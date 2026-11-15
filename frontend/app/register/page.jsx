"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/AuthProvider";

export default function RegisterPage() {
  const router = useRouter();
  const { me, loading: authLoading, register, login } = useAuth();
  const [form, setForm] = useState({
    display_name: "",
    username: "",
    email: "",
    password: "",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!authLoading && me) router.replace("/profile");
  }, [authLoading, me, router]);

  const update = (field) => (event) =>
    setForm((current) => ({ ...current, [field]: event.target.value }));

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await register({
        display_name: form.display_name.trim(),
        username: form.username.trim(),
        email: form.email.trim(),
        password: form.password,
      });
      await login(form.username.trim(), form.password);
      router.push("/profile");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-card card card-pad">
      <span className="eyebrow">Join Chirp</span>
      <h1 className="auth-title">Create your account</h1>
      <p className="muted" style={{ marginBottom: 18 }}>
        Usernames are 3–30 characters: letters, numbers and underscores only.
      </p>

      <form className="form" onSubmit={submit}>
        <div className="field">
          <label className="label" htmlFor="display_name">
            Display name
          </label>
          <input
            id="display_name"
            className="input"
            maxLength={50}
            value={form.display_name}
            onChange={update("display_name")}
            required
          />
        </div>
        <div className="field">
          <label className="label" htmlFor="username">
            Username
          </label>
          <input
            id="username"
            className="input"
            maxLength={30}
            pattern="[A-Za-z0-9_]+"
            title="Letters, numbers and underscores only"
            value={form.username}
            onChange={update("username")}
            required
          />
        </div>
        <div className="field">
          <label className="label" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            className="input"
            type="email"
            value={form.email}
            onChange={update("email")}
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
            minLength={8}
            autoComplete="new-password"
            value={form.password}
            onChange={update("password")}
            required
          />
          <span className="muted">At least 8 characters.</span>
        </div>
        {error && <p className="error">{error}</p>}
        <button className="btn btn-primary" disabled={busy}>
          {busy ? "Creating account…" : "Create account"}
        </button>
      </form>

      <p className="muted" style={{ marginTop: 18 }}>
        Already have an account? <Link href="/login">Log in</Link>.
      </p>
    </div>
  );
}
