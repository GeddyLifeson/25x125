// 25x125 desktop program (Electron). Starts the bundled Postgres with PostGIS, the Python engine and the
// Next.js web app on this computer only (127.0.0.1), opens the app in a window, and keeps the data fresh
// from the public portals. No sign-in: the engine runs with LOCAL_MODE=1 (engine/auth.py).
//
// Layout of the runtime folder (built by scripts/prepare-runtime.mjs, shipped as resources/runtime):
//   pgsql/    PostgreSQL 16 binaries with the PostGIS bundle copied in
//   python/   Python 3.12 with the engine's packages installed
//   app/      core, db, engine, jobs, data and desktop_bootstrap.py (the Python side of the repo)
//   web/      the Next.js standalone server (web/server.js) with its static files
// Everything the program writes goes to the user data folder (%APPDATA%\25x125): pgdata, logs, config.json.

const { app, BrowserWindow, Menu, dialog, ipcMain, shell } = require("electron");
const { spawn, spawnSync } = require("node:child_process");
const crypto = require("node:crypto");
const fs = require("node:fs");
const http = require("node:http");
const net = require("node:net");
const path = require("node:path");

const WIN = process.platform === "win32";
const EXE = WIN ? ".exe" : "";
const SELF_TEST = process.argv.includes("--self-test");
// --data-dir=PATH keeps the database, logs and settings somewhere other than %APPDATA%\25x125 (CI uses it).
const dataDirArg = process.argv.find((a) => a.startsWith("--data-dir="));
if (dataDirArg) app.setPath("userData", path.resolve(dataDirArg.slice("--data-dir=".length)));
const DAY_MS = 24 * 3600 * 1000;
// Fresh data: the incremental update runs when the last one is older than this; the full reload (tax-year
// sources too, 1-2 hours) when the last one is older than FULL_EVERY_DAYS. Checked at start and every hour.
const UPDATE_AFTER_HOURS = 20;
const FULL_EVERY_DAYS = 30;

const runtime = app.isPackaged
  ? path.join(process.resourcesPath, "runtime")
  : path.join(__dirname, "..", "build", "runtime");
const R = {
  pgBin: path.join(runtime, "pgsql", "bin"),
  python: WIN ? path.join(runtime, "python", "python.exe") : path.join(runtime, "python", "bin", "python3"),
  app: path.join(runtime, "app"),
  webServer: path.join(runtime, "web", "web", "server.js"),
};

let userData, logsDir, pgData, configFile, config;
let ports = { pg: 0, engine: 0, web: 0 };
const children = new Map(); // name -> ChildProcess
let mainWindow = null;
let statusWindow = null;
let job = null; // { kind: "full" | "update", child, started }
let quitting = false;
const statusLines = [];

// ---------- small helpers ----------

function log(line) {
  const text = `[${new Date().toISOString()}] ${line}`;
  statusLines.push(text);
  if (statusLines.length > 2000) statusLines.splice(0, statusLines.length - 2000);
  try {
    fs.appendFileSync(path.join(logsDir, "desktop.log"), text + "\n");
  } catch {
    // logs folder not ready yet
  }
  if (statusWindow && !statusWindow.isDestroyed()) statusWindow.webContents.send("log", text);
  if (SELF_TEST) process.stdout.write(text + "\n");
}

function setStatus(text) {
  log(text);
  if (statusWindow && !statusWindow.isDestroyed()) statusWindow.webContents.send("status", text);
}

function loadConfig() {
  try {
    return JSON.parse(fs.readFileSync(configFile, "utf8"));
  } catch {
    return {};
  }
}

function saveConfig() {
  fs.writeFileSync(configFile, JSON.stringify(config, null, 2));
}

function freePort(preferred = 0) {
  return new Promise((resolve) => {
    const srv = net.createServer();
    srv.unref();
    srv.on("error", () => (preferred ? freePort(0).then(resolve) : resolve(0)));
    srv.listen(preferred, "127.0.0.1", () => {
      const { port } = srv.address();
      srv.close(() => resolve(port));
    });
  });
}

function get(url, timeoutMs = 5000) {
  return new Promise((resolve) => {
    const req = http.get(url, { timeout: timeoutMs }, (res) => {
      let body = "";
      res.setEncoding("utf8");
      res.on("data", (c) => (body += c));
      res.on("end", () => resolve({ status: res.statusCode, headers: res.headers, body }));
    });
    req.on("timeout", () => req.destroy(new Error("timeout")));
    req.on("error", (e) => resolve({ status: 0, body: String(e) }));
  });
}

async function waitFor(url, label, timeoutS) {
  const end = Date.now() + timeoutS * 1000;
  while (Date.now() < end) {
    const r = await get(url, 3000);
    if (r.status > 0 && r.status < 500) return r;
    await new Promise((res) => setTimeout(res, 500));
  }
  throw new Error(`${label} did not answer at ${url} within ${timeoutS} seconds. See the logs folder.`);
}

function baseEnv() {
  const pgsql = path.join(runtime, "pgsql");
  const env = {
    ...process.env,
    PATH: [R.pgBin, path.dirname(R.python), process.env.PATH].join(path.delimiter),
    PROJ_LIB: path.join(pgsql, "share", "contrib", "postgis-3.5", "proj"),
    GDAL_DATA: path.join(pgsql, "gdal-data"),
    PYTHONUTF8: "1",
    PYTHONUNBUFFERED: "1",
    PYTHONDONTWRITEBYTECODE: "1",
    PYTHONPATH: R.app,
    DATABASE_URL: `postgresql://postgres:${config.pgPassword}@127.0.0.1:${ports.pg}/x25x125`,
    ENGINE_SHARED_SECRET: config.secret,
    LOCAL_MODE: "1",
    APP_ENV: "development",
    NEXT_TELEMETRY_DISABLED: "1",
  };
  delete env.ELECTRON_RUN_AS_NODE;
  return env;
}

function logStream(name) {
  const file = path.join(logsDir, `${name}.log`);
  try {
    if (fs.statSync(file).size > 20 * 1024 * 1024) fs.renameSync(file, file + ".old");
  } catch {
    // no log yet
  }
  return fs.createWriteStream(file, { flags: "a" });
}

/** Run a program to the end. Resolves with its exit code; output goes to logs/<name>.log and the status window. */
function run(name, cmd, args, opts = {}) {
  return new Promise((resolve) => {
    const out = logStream(name);
    out.write(`\n=== ${new Date().toISOString()} ${cmd} ${args.join(" ")}\n`);
    const child = spawn(cmd, args, { env: baseEnv(), windowsHide: true, ...opts });
    if (opts.track) opts.track(child);
    const onData = (d) => {
      out.write(d);
      if (opts.echo) for (const line of String(d).split(/\r?\n/)) if (line.trim()) log(`${name}: ${line}`);
    };
    child.stdout.on("data", onData);
    child.stderr.on("data", onData);
    child.on("error", (e) => {
      out.write(`failed to start: ${e}\n`);
      resolve(-1);
    });
    child.on("close", (code) => {
      out.end();
      resolve(code ?? -1);
    });
  });
}

/** Start a long-running service; its output goes to logs/<name>.log. */
function startService(name, cmd, args, extraEnv = {}) {
  const out = logStream(name);
  out.write(`\n=== ${new Date().toISOString()} ${cmd} ${args.join(" ")}\n`);
  const child = spawn(cmd, args, { env: { ...baseEnv(), ...extraEnv }, cwd: userData, windowsHide: true });
  child.stdout.pipe(out);
  child.stderr.pipe(out);
  child.on("exit", (code) => {
    children.delete(name);
    if (!quitting) {
      log(`${name} stopped (exit ${code}). See logs\\${name}.log.`);
      if (!SELF_TEST && mainWindow && !mainWindow.isDestroyed()) {
        dialog.showMessageBox(mainWindow, {
          type: "error",
          message: `The ${name} stopped.`,
          detail: `Close 25x125 and open it again. If it keeps happening, send Claude the file logs\\${name}.log from ${userData}.`,
        });
      }
    }
  });
  children.set(name, child);
  return child;
}

function killTree(child) {
  if (!child || child.exitCode !== null) return;
  if (WIN) spawnSync("taskkill", ["/pid", String(child.pid), "/T", "/F"], { windowsHide: true });
  else child.kill("SIGTERM");
}

// ---------- the database ----------

const pg = (tool) => path.join(R.pgBin, tool + EXE);

async function startDatabase() {
  const fresh = !fs.existsSync(path.join(pgData, "PG_VERSION"));
  if (fresh) {
    setStatus("Creating the database (first start only)...");
    const pw = path.join(userData, "pw.tmp");
    fs.writeFileSync(pw, config.pgPassword);
    const code = await run("postgres-init", pg("initdb"), [
      "-D", pgData, "-U", "postgres", "--pwfile", pw, "--auth", "scram-sha-256", "-E", "UTF8", "--no-locale",
    ]);
    fs.rmSync(pw, { force: true });
    if (code !== 0) throw new Error("Could not create the database folder. See logs\\postgres-init.log.");
    // Local only; settings sized for the 1-2 hour load on a normal PC.
    fs.appendFileSync(
      path.join(pgData, "postgresql.conf"),
      [
        "",
        "# 25x125 desktop",
        "listen_addresses = '127.0.0.1'",
        "unix_socket_directories = ''",
        "shared_buffers = 256MB",
        "work_mem = 32MB",
        "maintenance_work_mem = 512MB",
        "max_wal_size = 4GB",
        "checkpoint_timeout = 15min",
        "logging_collector = off",
        "",
      ].join("\n"),
    );
  }
  // A crash or power cut can leave the server running or a stale lock file; pg_ctl handles both.
  const status = spawnSync(pg("pg_ctl"), ["status", "-D", pgData], { env: baseEnv(), windowsHide: true });
  if (status.status === 0) {
    log("A database server from an earlier run is still up; stopping it first.");
    spawnSync(pg("pg_ctl"), ["stop", "-D", pgData, "-m", "fast", "-w"], { env: baseEnv(), windowsHide: true });
  }
  setStatus("Starting the database...");
  const code = await run("postgres", pg("pg_ctl"), [
    "start", "-D", pgData, "-w", "-t", "120", "-l", path.join(logsDir, "postgres-server.log"),
    "-o", `-p ${ports.pg}`,
  ]);
  if (code !== 0) throw new Error("The database did not start. See logs\\postgres-server.log.");
  setStatus("Preparing the tables...");
  const boot = await run("bootstrap", R.python, ["-m", "desktop_bootstrap"], { cwd: R.app, echo: true });
  if (boot !== 0) throw new Error("Could not prepare the tables. See logs\\bootstrap.log.");
}

function stopDatabase() {
  if (!pgData || !fs.existsSync(path.join(pgData, "PG_VERSION"))) return;
  spawnSync(pg("pg_ctl"), ["stop", "-D", pgData, "-m", "fast", "-w", "-t", "60"], {
    env: baseEnv(),
    windowsHide: true,
  });
}

// ---------- engine and web app ----------

async function startEngine() {
  setStatus("Starting the engine...");
  startService("engine", R.python, [
    "-m", "uvicorn", "engine.app:app", "--host", "127.0.0.1", "--port", String(ports.engine), "--app-dir", R.app,
  ]);
  await waitFor(`http://127.0.0.1:${ports.engine}/health`, "The engine", 120);
}

async function startWeb() {
  setStatus("Starting the app...");
  startService("web", process.execPath, [R.webServer], {
    ELECTRON_RUN_AS_NODE: "1",
    NODE_ENV: "production",
    PORT: String(ports.web),
    HOSTNAME: "127.0.0.1",
    ENGINE_URL: `http://127.0.0.1:${ports.engine}`,
    TILES_URL: `http://127.0.0.1:${ports.engine}/tiles`,
  });
  await waitFor(`http://127.0.0.1:${ports.web}/`, "The app", 120);
}

// ---------- data loads ----------

function dataState() {
  const last = config.lastUpdateAt ? new Date(config.lastUpdateAt) : null;
  const lastFull = config.lastFullAt ? new Date(config.lastFullAt) : null;
  return { last, lastFull };
}

function startJob(kind, reason) {
  if (job) {
    log(`A data load is already running (${job.kind}); not starting another.`);
    return false;
  }
  const args = ["-m", "jobs.nightly", "--year", String(new Date().getFullYear())];
  if (kind === "update") args.push("--skip-yearly");
  const started = new Date();
  setStatus(
    kind === "full"
      ? `Full data load started (${reason}). It takes 1 to 2 hours and about 3 GB of disk.`
      : `Data update started (${reason}). It usually takes 5 to 20 minutes.`,
  );
  job = { kind, started, child: null };
  job.timer = setInterval(() => {
    const mins = Math.round((Date.now() - started.getTime()) / 60000);
    if (mins > 0 && mins % 5 === 0) log(`Still loading (${mins} minutes so far). The step named last above is running.`);
  }, 60 * 1000);
  updateMenu();
  run("data-load", R.python, args, { cwd: R.app, echo: true, track: (c) => (job.child = c) }).then((code) => {
    const mins = Math.round((Date.now() - started.getTime()) / 60000);
    config.lastUpdateAt = started.toISOString();
    if (kind === "full") config.lastFullAt = started.toISOString();
    config.lastResult = { kind, code, finished: new Date().toISOString(), minutes: mins };
    saveConfig();
    clearInterval(job.timer);
    job = null;
    updateMenu();
    setStatus(
      code === 0
        ? `Data ${kind === "full" ? "load" : "update"} finished in ${mins} minutes.`
        : `Data ${kind === "full" ? "load" : "update"} finished in ${mins} minutes; some sources failed (see the lines above or logs\\data-load.log). They are tried again next time.`,
    );
    if (mainWindow && !mainWindow.isDestroyed() && !quitting) mainWindow.webContents.reload();
  });
  return true;
}

function checkData() {
  if (SELF_TEST || job) return;
  const { last, lastFull } = dataState();
  if (!lastFull) return startJob("full", "first start");
  if (Date.now() - lastFull.getTime() > FULL_EVERY_DAYS * DAY_MS) return startJob("full", "monthly reload");
  if (!last || Date.now() - last.getTime() > UPDATE_AFTER_HOURS * 3600 * 1000) return startJob("update", "daily update");
}

// ---------- windows and menu ----------

function openStatusWindow() {
  if (statusWindow && !statusWindow.isDestroyed()) return statusWindow.show();
  statusWindow = new BrowserWindow({
    width: 760,
    height: 560,
    title: "25x125: status and data loads",
    webPreferences: { preload: path.join(__dirname, "status-preload.js"), contextIsolation: true, sandbox: true },
  });
  statusWindow.setMenuBarVisibility(false);
  statusWindow.loadFile(path.join(__dirname, "status.html"));
  statusWindow.on("closed", () => (statusWindow = null));
}

function openMainWindow() {
  if (mainWindow && !mainWindow.isDestroyed()) return mainWindow.show();
  const origin = `http://127.0.0.1:${ports.web}`;
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    title: "25x125",
    webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true },
  });
  // Links to other sites (sources, apply links) open in the normal browser.
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith(origin)) return { action: "allow" };
    if (/^https?:\/\//.test(url)) shell.openExternal(url);
    return { action: "deny" };
  });
  mainWindow.webContents.on("will-navigate", (e, url) => {
    if (!url.startsWith(origin)) {
      e.preventDefault();
      if (/^https?:\/\//.test(url)) shell.openExternal(url);
    }
  });
  mainWindow.loadURL(origin + "/map");
  mainWindow.on("closed", () => {
    mainWindow = null;
    if (!quitting) app.quit();
  });
}

function updateMenu() {
  const running = Boolean(job);
  const template = [
    {
      label: "File",
      submenu: [
        { label: "Open data folder", click: () => shell.openPath(userData) },
        { label: "Open logs folder", click: () => shell.openPath(logsDir) },
        { type: "separator" },
        { role: "quit", label: "Quit 25x125" },
      ],
    },
    { role: "editMenu" },
    {
      label: "View",
      submenu: [{ role: "reload" }, { role: "resetZoom" }, { role: "zoomIn" }, { role: "zoomOut" }, { type: "separator" }, { role: "togglefullscreen" }],
    },
    {
      label: "Data",
      submenu: [
        { label: "Status and data log", click: openStatusWindow },
        { type: "separator" },
        { label: "Update data now (new records)", enabled: !running, click: () => startJob("update", "asked from the menu") },
        { label: "Full reload (1 to 2 hours)", enabled: !running, click: () => startJob("full", "asked from the menu") },
        { label: running ? `Stop the ${job.kind === "full" ? "full load" : "update"}` : "Stop the data load", enabled: running, click: stopJob },
      ],
    },
    {
      label: "Help",
      submenu: [
        { label: "Install and use instructions", click: () => shell.openExternal("https://github.com/GeddyLifeson/25x125/blob/main/desktop/README.md") },
        { label: "Engine health (JSON)", click: () => shell.openExternal(`http://127.0.0.1:${ports.engine}/health`) },
        { role: "toggleDevTools" },
      ],
    },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

function stopJob() {
  if (!job) return;
  log("Stopping the data load. Sources already loaded are kept; the rest load next time.");
  killTree(job.child);
}

ipcMain.handle("status:init", () => ({
  lines: statusLines,
  dataDir: userData,
  ...(config ? { lastUpdateAt: config.lastUpdateAt, lastFullAt: config.lastFullAt, lastResult: config.lastResult } : {}),
  running: job ? job.kind : null,
}));
ipcMain.handle("status:open-app", () => (ports.web ? openMainWindow() : null));

// ---------- start and stop ----------

async function selfTest() {
  // Started with --self-test (CI): everything above except windows and data loads, then a few checks.
  const results = [];
  const check = async (name, fn) => {
    try {
      const detail = await fn();
      results.push({ name, ok: true, detail });
    } catch (e) {
      results.push({ name, ok: false, detail: String(e && e.message ? e.message : e) });
    }
  };
  const web = `http://127.0.0.1:${ports.web}`;
  const engine = `http://127.0.0.1:${ports.engine}`;
  await check("engine health: database and PostGIS", async () => {
    const r = await get(`${engine}/health`);
    const j = JSON.parse(r.body);
    if (j.database !== "ok" || !j.postgis) throw new Error(r.body);
    return j.postgis;
  });
  await check("local session: no sign-in, Pro", async () => {
    const r = await get(`${web}/deals`);
    if (r.status !== 200) throw new Error(`/deals answered ${r.status} ${r.headers?.location ?? ""}`);
    if (!r.body.includes("Desktop, this computer only")) throw new Error("the page does not show local mode");
    return "deals page opens without sign-in";
  });
  await check("rules load (Python on Windows reads the rule files)", async () => {
    const code = await run("self-test-seed", R.python, ["-m", "jobs.seed_rules"], { cwd: R.app, echo: true });
    if (code !== 0) throw new Error(`jobs.seed_rules exit ${code}`);
    return "seed_rules ok";
  });
  await check("map tiles from the engine", async () => {
    const r = await get(`${web}/tiles/lots/14/4202/6087`);
    if (![200, 204].includes(r.status)) throw new Error(`tile answered ${r.status}: ${r.body.slice(0, 200)}`);
    return `status ${r.status}`;
  });
  await check("address search answers", async () => {
    const r = await get(`${web}/?q=1600%20N%20Milwaukee`);
    if (r.status !== 200) throw new Error(`search page answered ${r.status}`);
    return "search page 200";
  });
  if (process.argv.includes("--self-test-load")) {
    await check("one real loader: community area and ward boundaries from the Chicago Data Portal", async () => {
      const code = await run("self-test-load", R.python, ["-m", "jobs.load_boundaries"], { cwd: R.app, echo: true });
      if (code !== 0) throw new Error(`jobs.load_boundaries exit ${code}`);
      const r = await get(`${engine}/community-areas`);
      if (r.status !== 200) throw new Error(`/community-areas answered ${r.status}`);
      const n = JSON.parse(r.body).length;
      if (n < 77) throw new Error(`${n} community areas, expected 77`);
      return `${n} community areas`;
    });
  }
  const ok = results.every((r) => r.ok);
  const outArg = process.argv.find((a) => a.startsWith("--self-test-out="));
  const report = JSON.stringify({ ok, ports, results }, null, 2);
  if (outArg) fs.writeFileSync(outArg.slice("--self-test-out=".length), report);
  process.stdout.write(report + "\n");
  return ok;
}

async function start() {
  userData = app.getPath("userData");
  logsDir = path.join(userData, "logs");
  pgData = path.join(userData, "pgdata");
  configFile = path.join(userData, "config.json");
  fs.mkdirSync(logsDir, { recursive: true });
  config = loadConfig();
  if (!config.pgPassword) config.pgPassword = crypto.randomBytes(18).toString("hex");
  if (!config.secret) config.secret = crypto.randomBytes(32).toString("hex");
  // The database keeps its port between runs when it is free (54325 by default, clear of Docker's 5432).
  ports.pg = await freePort(config.pgPort || 54325);
  config.pgPort = ports.pg;
  ports.engine = await freePort(0);
  ports.web = await freePort(0);
  saveConfig();
  log(`25x125 desktop ${app.getVersion()} starting. Data folder: ${userData}`);

  if (!SELF_TEST) {
    updateMenu();
    openStatusWindow();
  }
  try {
    for (const p of [R.pgBin, R.python, R.app, R.webServer]) {
      if (!fs.existsSync(p)) throw new Error(`Missing part of the program: ${p}. Reinstall 25x125.`);
    }
    await startDatabase();
    await startEngine();
    await startWeb();
  } catch (e) {
    log(`Start-up failed: ${e.message}`);
    if (SELF_TEST) {
      fs.writeFileSync(
        (process.argv.find((a) => a.startsWith("--self-test-out=")) || "--self-test-out=self-test.json").slice(16),
        JSON.stringify({ ok: false, error: e.message }, null, 2),
      );
      return shutdown(1);
    }
    dialog.showErrorBox("25x125 could not start", `${e.message}\n\nLogs: ${logsDir}`);
    return shutdown(1);
  }
  setStatus(`Ready. App at http://127.0.0.1:${ports.web} (this computer only).`);

  if (SELF_TEST) return shutdown((await selfTest()) ? 0 : 1);

  openMainWindow();
  const { lastFull } = dataState();
  checkData();
  if (!lastFull) {
    openStatusWindow();
    setStatus(
      "First start: loading the public data now. This takes 1 to 2 hours and about 3 GB. " +
        "You can look around the app meanwhile; the map and lists fill in when the load finishes. " +
        "Keep 25x125 open until this window says the load finished.",
    );
  }
  setInterval(checkData, 3600 * 1000);
}

let shuttingDown = false;
async function shutdown(code = 0) {
  if (shuttingDown) return;
  shuttingDown = true;
  quitting = true;
  if (job) killTree(job.child);
  for (const [, child] of children) killTree(child);
  stopDatabase();
  app.exit(code);
}

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    } else if (statusWindow) statusWindow.focus();
  });
  app.on("before-quit", (e) => {
    if (shuttingDown) return;
    if (job && job.kind === "full" && !SELF_TEST) {
      const pick = dialog.showMessageBoxSync({
        type: "question",
        buttons: ["Keep running", "Quit anyway"],
        defaultId: 0,
        message: "A full data load is still running.",
        detail: "If you quit, sources already loaded are kept and the rest load the next time you open 25x125.",
      });
      if (pick === 0) {
        e.preventDefault();
        quitting = false;
        return;
      }
    }
    e.preventDefault();
    shutdown(0);
  });
  app.on("window-all-closed", () => {
    if (!mainWindow) app.quit();
  });
  app.whenReady().then(start);
}
