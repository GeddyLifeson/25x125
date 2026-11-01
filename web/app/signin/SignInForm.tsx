"use client";
import { useState } from "react";

export function SignInForm({ next, email: initial }: { next: string; email: string }) {
  const [email, setEmail] = useState(initial);
  const [state, setState] = useState<"idle" | "sending" | "sent">("idle");
  const [err, setErr] = useState<string | null>(null);
  if (state === "sent") {
    return (
      <p role="status" data-testid="link-sent">
        Check {email} for the sign-in link. It works once and expires in 30 minutes.
      </p>
    );
  }
  return (
    <form
      className="search"
      onSubmit={async (e) => {
        e.preventDefault();
        setErr(null);
        setState("sending");
        const res = await fetch("/api/auth/email", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ email, next }),
        });
        const body = (await res.json().catch(() => ({}))) as { detail?: string };
        if (res.ok) setState("sent");
        else {
          setState("idle");
          setErr(body.detail ?? res.statusText);
        }
      }}
    >
      <input
        name="email"
        type="email"
        required
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="you@company.com"
        aria-label="Email"
        autoComplete="email"
        autoFocus
      />
      <button className="btn primary" type="submit" disabled={state === "sending"}>
        {state === "sending" ? "Sending" : "Email me a link"}
      </button>
      {err && <p className="err">{err}</p>}
    </form>
  );
}
