"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/AuthProvider";

export default function LoginPage() {
  const router = useRouter();
  const { me, loading: authLoading, login } = useAuth();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!authLoading && me) router.replace("/profile");
  }, [authLoading, me, router]);

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(identifier.trim(), password);
      router.push("/profile");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-card card card-pad">
      <span className="eyebrow">Welcome back</span>
      <h1 className="auth-title">Log in to Chirp</h1>
      <p className="muted" style={{ marginBottom: 18 }}>
        Use your email address or your username.
      </p>

      <form className="form" onSubmit={submit}>
        <div className="field">
          <label className="label" htmlFor="identifier">
            Email or username
          </label>
          <input
            id="identifier"
            className="input"
            autoComplete="username"
            value={identifier}
            onChange={(event) => setIdentifier(event.target.value)}
            required
          />
        </div>
        <div className="field">
          <label className="label" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            className="input"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </div>
        {error && <p className="error">{error}</p>}
        <button className="btn btn-primary" disabled={busy}>
          {busy ? "Logging in…" : "Log in"}
        </button>
      </form>

      <p className="muted" style={{ marginTop: 18 }}>
        New here? <Link href="/register">Create an account</Link>.
      </p>
    </div>
  );
}
