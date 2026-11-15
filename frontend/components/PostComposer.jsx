"use client";

import { useState } from "react";

import { api } from "@/lib/api";

export default function PostComposer({ onPosted }) {
  const [content, setContent] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (event) => {
    event.preventDefault();
    if (!content.trim()) return;
    setBusy(true);
    setError("");
    try {
      const post = await api("/posts", {
        method: "POST",
        body: { content },
      });
      setContent("");
      onPosted?.(post);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="composer" onSubmit={submit}>
      <textarea
        className="textarea"
        rows={3}
        maxLength={280}
        placeholder="What's on your mind?"
        value={content}
        onChange={(event) => setContent(event.target.value)}
      />
      <div className="row between">
        <span className={`muted counter ${content.length > 260 ? "warn" : ""}`}>
          {content.length}/280
        </span>
        <button
          type="submit"
          className="btn btn-primary"
          disabled={busy || !content.trim()}
        >
          {busy ? "Posting…" : "Post"}
        </button>
      </div>
      {error && <p className="error">{error}</p>}
    </form>
  );
}
