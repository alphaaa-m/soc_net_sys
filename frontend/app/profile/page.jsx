"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/AuthProvider";
import PostCard from "@/components/PostCard";
import { api, clearToken } from "@/lib/api";
import { formatJoined } from "@/lib/format";

export default function ProfilePage() {
  const router = useRouter();
  const { me, loading, refresh, setMe } = useAuth();
  const [form, setForm] = useState({ display_name: "", bio: "" });
  const [posts, setPosts] = useState([]);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [password, setPassword] = useState("");
  const [deactivating, setDeactivating] = useState(false);

  useEffect(() => {
    if (!loading && !me) router.replace("/login");
  }, [loading, me, router]);

  useEffect(() => {
    if (me) setForm({ display_name: me.display_name, bio: me.bio || "" });
  }, [me]);

  const loadPosts = useCallback(async () => {
    if (!me) return;
    try {
      const page = await api(`/users/${me.username}/posts?limit=20`);
      setPosts(page.items);
    } catch (err) {
      setError(err.message);
    }
  }, [me]);

  useEffect(() => {
    loadPosts();
  }, [loadPosts]);

  if (loading || !me) {
    return <p className="muted">Loading profile…</p>;
  }

  const save = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await api("/users/me", { method: "PATCH", body: form });
      await refresh();
      setNotice("Profile updated.");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const deactivate = async () => {
    if (
      !window.confirm(
        "Deactivate your account? You will be logged out and cannot log in again.",
      )
    ) {
      return;
    }
    setDeactivating(true);
    setError("");
    try {
      await api("/auth/deactivate", { method: "POST", body: { password } });
      clearToken();
      setMe(null);
      router.replace("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setDeactivating(false);
    }
  };

  return (
    <div className="stack">
      <section className="card card-pad">
        <div className="row between">
          <div>
            <h2>{me.display_name}</h2>
            <p className="muted">
              @{me.username} · {me.email}
            </p>
          </div>
          <span className="badge badge-done">Phase 1</span>
        </div>
        <p className="muted" style={{ marginTop: 8 }}>
          Joined {formatJoined(me.created_at)}
        </p>
      </section>

      <section className="card card-pad">
        <h2>Edit profile</h2>
        <form className="form" onSubmit={save} style={{ marginTop: 14 }}>
          <div className="field">
            <label className="label" htmlFor="display_name">
              Display name
            </label>
            <input
              id="display_name"
              className="input"
              maxLength={50}
              value={form.display_name}
              onChange={(event) =>
                setForm({ ...form, display_name: event.target.value })
              }
              required
            />
          </div>
          <div className="field">
            <label className="label" htmlFor="bio">
              Bio <span className="muted">({form.bio.length}/160)</span>
            </label>
            <textarea
              id="bio"
              className="textarea"
              rows={3}
              maxLength={160}
              placeholder="A short line about you"
              value={form.bio}
              onChange={(event) =>
                setForm({ ...form, bio: event.target.value })
              }
            />
          </div>
          <div className="row">
            <button className="btn btn-primary" disabled={busy}>
              {busy ? "Saving…" : "Save changes"}
            </button>
            {notice && <span className="notice">{notice}</span>}
          </div>
          {error && <p className="error">{error}</p>}
        </form>
      </section>

      <section className="stack">
        <div className="row between">
          <h2>Your posts</h2>
          <span className="badge badge-done">Phase 2</span>
        </div>
        {posts.length === 0 ? (
          <div className="empty card">No posts yet.</div>
        ) : (
          posts.map((post) => (
            <PostCard
              key={post.id}
              post={post}
              onDeleted={(id) =>
                setPosts((list) => list.filter((item) => item.id !== id))
              }
              onUpdated={(updated) =>
                setPosts((list) =>
                  list.map((item) => (item.id === updated.id ? updated : item)),
                )
              }
            />
          ))
        )}
      </section>

      <section className="card card-pad">
        <h2>Danger zone</h2>
        <p className="muted" style={{ marginTop: 6 }}>
          Deactivation hides your content and blocks login. Confirm with your
          current password.
        </p>
        <div className="row" style={{ marginTop: 12 }}>
          <input
            className="input"
            style={{ maxWidth: 280 }}
            type="password"
            placeholder="Current password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          <button
            type="button"
            className="btn btn-danger"
            onClick={deactivate}
            disabled={deactivating || !password}
          >
            {deactivating ? "Deactivating…" : "Deactivate account"}
          </button>
        </div>
      </section>
    </div>
  );
}
