// Build desktop/build/runtime: everything the Windows program runs besides Electron itself.
//   pgsql/   PostgreSQL 16 (EDB Windows binaries) with the PostGIS 3.5 bundle (OSGeo) copied in
//   python/  Python 3.12 (python.org build from NuGet) with the engine's packages from pyproject.toml
//   app/     core, db, engine, jobs, data/{rules,sources,reference} and desktop_bootstrap.py
//   web/     the Next.js standalone server, built with LOCAL_MODE=1
// Run on Windows from desktop/: node scripts/prepare-runtime.mjs   (CI: .github/workflows/desktop.yml)
// Downloads are checked against the SHA-256 values below and cached in desktop/build/cache.

import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const desktop = path.resolve(here, "..");
const repo = path.resolve(desktop, "..");
const build = path.join(desktop, "build");
const cache = path.join(build, "cache");
const tmp = path.join(build, "tmp");
const out = path.join(build, "runtime");
const WIN = process.platform === "win32";

// Pinned downloads (checked 2026-11-01). Change the version and the hash together.
const DOWNLOADS = {
  postgres: {
    url: "https://get.enterprisedb.com/postgresql/postgresql-16.13-1-windows-x64-binaries.zip",
    sha256: "9b4c7a1bc31147b5b2ba59178d0eef86c16181d54a20177192b387dff20f00a9",
  },
  postgis: {
    url: "https://download.osgeo.org/postgis/windows/pg16/archive/postgis-bundle-pg16-3.5.3x64.zip",
    sha256: "db5c96627d24160cca9bd4378407a4041149d02df9b88faeda2ce1736b3a736d",
  },
  python: {
    url: "https://api.nuget.org/v3-flatcontainer/python/3.12.10/python.3.12.10.nupkg",
    sha256: "0eb85c2dfccccf1b17352de4c397f69194035b7d37149eacc16f1147d93de3b8",
  },
};

const step = (msg) => console.log(`\n== ${msg}`);
const sh = (cmd, args, opts = {}) => execFileSync(cmd, args, { stdio: "inherit", ...opts });

async function download(name) {
  const { url, sha256 } = DOWNLOADS[name];
  const file = path.join(cache, path.basename(new URL(url).pathname));
  const hash = (f) => createHash("sha256").update(fs.readFileSync(f)).digest("hex");
  if (fs.existsSync(file) && hash(file) === sha256) return file;
  step(`download ${name}: ${url}`);
  const res = await fetch(url, { redirect: "follow" });
  if (!res.ok) throw new Error(`${url} answered ${res.status}`);
  fs.writeFileSync(file, Buffer.from(await res.arrayBuffer()));
  const got = hash(file);
  if (got !== sha256) throw new Error(`${name}: SHA-256 ${got} does not match the pinned ${sha256}`);
  return file;
}

function unzip(zip, dest) {
  fs.mkdirSync(dest, { recursive: true });
  // Windows 10 and later ship bsdtar, which reads zip files.
  if (WIN) sh("tar", ["-xf", zip, "-C", dest]);
  else sh("unzip", ["-q", "-o", zip, "-d", dest]);
}

/** Copy a folder into another; existing files are kept unless overwrite is set. */
function merge(from, to, overwrite = false) {
  fs.mkdirSync(to, { recursive: true });
  for (const e of fs.readdirSync(from, { withFileTypes: true })) {
    const a = path.join(from, e.name);
    const b = path.join(to, e.name);
    if (e.isDirectory()) merge(a, b, overwrite);
    else if (overwrite || !fs.existsSync(b)) fs.copyFileSync(a, b);
  }
}

function copyTree(from, to) {
  fs.cpSync(from, to, {
    recursive: true,
    filter: (src) => !/[\\/](__pycache__|node_modules|\.pytest_cache)([\\/]|$)/.test(src) && !src.endsWith(".pyc"),
  });
}

async function postgres() {
  const pgZip = await download("postgres");
  const gisZip = await download("postgis");
  step("unpack PostgreSQL");
  const pgTmp = path.join(tmp, "pg");
  unzip(pgZip, pgTmp);
  const pgsql = path.join(out, "pgsql");
  fs.renameSync(path.join(pgTmp, "pgsql"), pgsql);
  // Not needed to run the server: the admin GUI, the installer helper, docs, headers and debug symbols.
  for (const d of ["pgAdmin 4", "pgAdmin", "StackBuilder", "doc", "include", "symbols"]) {
    fs.rmSync(path.join(pgsql, d), { recursive: true, force: true });
  }
  step("unpack PostGIS into PostgreSQL");
  const gisTmp = path.join(tmp, "postgis");
  unzip(gisZip, gisTmp);
  const bundle = path.join(gisTmp, fs.readdirSync(gisTmp).find((n) => n.startsWith("postgis-bundle")));
  // The bundle mirrors the PostgreSQL folder. DLLs PostgreSQL already ships (OpenSSL, libxml2, ...) are kept as
  // the server was built against them.
  for (const d of ["bin", "lib", "share", "gdal-data"]) {
    if (fs.existsSync(path.join(bundle, d))) merge(path.join(bundle, d), path.join(pgsql, d));
  }
}

async function python() {
  const nupkg = await download("python");
  step("unpack Python");
  const pyTmp = path.join(tmp, "python");
  unzip(nupkg, pyTmp);
  const py = path.join(out, "python");
  fs.renameSync(path.join(pyTmp, "tools"), py);
  for (const d of ["Lib/test", "Lib/idlelib", "include", "libs"]) fs.rmSync(path.join(py, d), { recursive: true, force: true });
  const exe = path.join(py, "python.exe");
  step("install the engine's Python packages");
  sh(exe, ["-m", "ensurepip", "--upgrade"]);
  const deps = execFileSync(exe, [
    "-c",
    "import tomllib,sys; print('\\n'.join(tomllib.load(open(sys.argv[1],'rb'))['project']['dependencies']))",
    path.join(repo, "pyproject.toml"),
  ])
    .toString()
    .split(/\r?\n/)
    .filter(Boolean);
  sh(exe, ["-m", "pip", "install", "--no-warn-script-location", "--disable-pip-version-check", ...deps]);
}

function appCode() {
  step("copy the engine, jobs and data");
  const app = path.join(out, "app");
  for (const d of ["core", "db", "engine", "jobs"]) copyTree(path.join(repo, d), path.join(app, d));
  for (const d of ["rules", "sources", "reference"]) copyTree(path.join(repo, "data", d), path.join(app, "data", d));
  fs.copyFileSync(path.join(desktop, "src", "bootstrap.py"), path.join(app, "desktop_bootstrap.py"));
}

function web() {
  step("build the web app (standalone, LOCAL_MODE=1)");
  const webDir = path.join(repo, "web");
  const npm = WIN ? "npm.cmd" : "npm";
  const env = { ...process.env, NEXT_OUTPUT: "standalone", LOCAL_MODE: "1", NEXT_TELEMETRY_DISABLED: "1" };
  sh(npm, ["ci", "--no-audit", "--no-fund"], { cwd: webDir, env, shell: WIN });
  sh(npm, ["run", "build"], { cwd: webDir, env, shell: WIN });
  const dest = path.join(out, "web");
  fs.cpSync(path.join(webDir, ".next", "standalone"), dest, { recursive: true });
  fs.cpSync(path.join(webDir, ".next", "static"), path.join(dest, "web", ".next", "static"), { recursive: true });
  if (fs.existsSync(path.join(webDir, "public"))) fs.cpSync(path.join(webDir, "public"), path.join(dest, "web", "public"), { recursive: true });
  if (!fs.existsSync(path.join(dest, "web", "server.js"))) throw new Error("web/server.js missing from the standalone build");
}

const only = process.argv.slice(2);
const want = (part) => only.length === 0 || only.includes(part);

fs.mkdirSync(cache, { recursive: true });
fs.rmSync(tmp, { recursive: true, force: true });
if (only.length === 0) fs.rmSync(out, { recursive: true, force: true });
fs.mkdirSync(out, { recursive: true });
if (!WIN && (want("postgres") || want("python"))) {
  throw new Error("The Postgres and Python downloads are Windows builds. On Mac or Linux run only: app web");
}
if (want("postgres")) await postgres();
if (want("python")) await python();
if (want("app")) appCode();
if (want("web")) web();
fs.rmSync(tmp, { recursive: true, force: true });
step(`runtime ready in ${out}`);
