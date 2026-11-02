"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/AuthProvider";
import PostCard from "@/components/PostCard";
import PostComposer from "@/components/PostComposer";
import { api } from "@/lib/api";

export default function HomePage() {
  const { me } = useAuth();
  const [posts, setPosts] = useState([]);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!me) return;
    setFetching(true);
    try {
      const page = await api(`/users/${me.username}/posts?limit=10`);
      setPosts(page.items);
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setFetching(false);
    }
  }, [me]);

  useEffect(() => {
    load();
  }, [load]);

  // Render the landing immediately (also on the server). A signed-in visitor
  // may see it for a heartbeat while the token is validated, then the feed
  // replaces it.
  if (!me) {
    return (
      <div className="stack">
        <section className="hero">
          <span className="eyebrow">A small, text-first social network</span>
          <h1>Say more with less.</h1>
          <p>
            Chirp is a teaching project that grows one phase at a time. Create
            an account, publish short posts, follow people, and explore the
            roadmap to see exactly what is live and what is still coming.
          </p>
          <div className="row" style={{ marginTop: 22 }}>
            <Link className="btn btn-primary" href="/register">
              Create your account
            </Link>
            <Link className="btn btn-secondary" href="/login">
              I already have one
            </Link>
          </div>
        </section>

        <section className="module-grid">
          <div className="card module-card">
            <span className="badge badge-done">Phase 1 · live</span>
            <h3>Accounts &amp; profiles</h3>
            <p className="muted">
              Register, log in with a JWT, edit your display name and bio, and
              browse public profiles.
            </p>
          </div>
          <div className="card module-card">
            <span className="badge badge-done">Phase 2 · live</span>
            <h3>Follow graph &amp; posts</h3>
            <p className="muted">
              Follow and unfollow people, see follower counts update, and
              create, edit or soft-delete your posts.
            </p>
          </div>
          <div className="card module-card">
            <span className="badge badge-todo">Phases 3–6 · planned</span>
            <h3>Honest roadmap</h3>
            <p className="muted">
              Likes, comments, the feed, search, blocking and admin are shown
              as clear warnings instead of fake screens.
            </p>
          </div>
        </section>

        <div className="banner banner-warn">
          <strong>⚠ Phases 3–6 are not implemented yet</strong>
          <span>
            Every unfinished area opens a &quot;not yet implemented&quot;
            warning. <Link href="/modules">Open the roadmap</Link> to see what
            is live.
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="stack">
      <section className="card card-pad">
        <div className="row between">
          <div>
            <h2>Welcome back, {me.display_name.split(" ")[0]}</h2>
            <p className="muted">Signed in as @{me.username}</p>
          </div>
          <Link href="/profile" className="btn btn-secondary btn-sm">
            Edit profile
          </Link>
        </div>
        <PostComposer
          onPosted={(post) => setPosts((list) => [post, ...list])}
        />
      </section>

      <div className="banner banner-warn">
        <strong>⚠ Following feed is not implemented yet</strong>
        <span>
          GET /feed arrives in Phase 4. This page shows your personal posts so
          you can use everything from Phase 2 today.
        </span>
      </div>

      <section className="stack">
        <div className="row between">
          <h2>Your posts</h2>
          <span className="muted">{posts.length} shown</span>
        </div>
        {error && <p className="error">{error}</p>}
        {fetching && <p className="muted">Loading posts…</p>}
        {!fetching && !error && posts.length === 0 && (
          <div className="empty card">
            No posts yet. Write your first one above.
          </div>
        )}
        {posts.map((post) => (
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
        ))}
      </section>
    </div>
  );
}
