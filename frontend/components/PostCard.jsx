"use client";

import Link from "next/link";
import { useState } from "react";

import { useAuth } from "@/components/AuthProvider";
import { api } from "@/lib/api";
import { formatDate, initials } from "@/lib/format";

export default function PostCard({
  post,
  onDeleted,
  onUpdated,
  showOpen = true,
}) {
  const { me } = useAuth();
  const [editing, setEditing] = useState(false);
  const [content, setContent] = useState(post.content);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const mine = me && me.id === post.author.id;

  const save = async () => {
    setBusy(true);
    setError("");
    try {
      const updated = await api(`/posts/${post.id}`, {
        method: "PATCH",
        body: { content },
      });
      setEditing(false);
      onUpdated?.(updated);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    if (!window.confirm("Delete this post? It will be hidden from everyone.")) {
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api(`/posts/${post.id}`, { method: "DELETE" });
      onDeleted?.(post.id);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <article className="post card">
      <header className="post-head">
        <Link
          href={`/u/${post.author.username}`}
          className="avatar"
          aria-label={`@${post.author.username}`}
        >
          {initials(post.author.display_name)}
        </Link>
        <div className="post-who">
          <Link href={`/u/${post.author.username}`} className="post-name">
            {post.author.display_name}
          </Link>
          <span className="muted">
            @{post.author.username} · {formatDate(post.created_at)}
            {post.is_edited ? " · edited" : ""}
          </span>
        </div>
        {showOpen && (
          <Link href={`/posts/${post.id}`} className="post-open">
            Open
          </Link>
        )}
      </header>

      {editing ? (
        <div className="stack-sm post-edit">
          <textarea
            className="textarea"
            rows={3}
            maxLength={280}
            value={content}
            onChange={(event) => setContent(event.target.value)}
          />
          <div className="row">
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={save}
              disabled={busy || !content.trim()}
            >
              {busy ? "Saving…" : "Save"}
            </button>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => {
                setEditing(false);
                setContent(post.content);
                setError("");
              }}
            >
              Cancel
            </button>
            <span className="muted counter">{content.length}/280</span>
          </div>
        </div>
      ) : (
        <p className="post-content">{post.content}</p>
      )}

      {error && <p className="error">{error}</p>}

      <footer className="post-meta">
        <span title="Likes — Phase 3">♥ {post.like_count}</span>
        <span title="Comments — Phase 3">💬 {post.comment_count}</span>
        <span title="Reposts — Phase 3">↻ {post.share_count}</span>
        {mine && !editing && (
          <span className="post-actions">
            <button
              type="button"
              className="link-btn"
              onClick={() => setEditing(true)}
            >
              Edit
            </button>
            <button
              type="button"
              className="link-btn danger"
              onClick={remove}
              disabled={busy}
            >
              Delete
            </button>
          </span>
        )}
      </footer>
    </article>
  );
}
