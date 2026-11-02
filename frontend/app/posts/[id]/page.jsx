"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/AuthProvider";
import PostCard from "@/components/PostCard";
import { api } from "@/lib/api";

export default function PostDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const { loading } = useAuth();
  const [post, setPost] = useState(null);
  const [error, setError] = useState("");
  const [fetching, setFetching] = useState(true);

  const load = useCallback(async () => {
    setFetching(true);
    try {
      const data = await api(`/posts/${id}`);
      setPost(data);
      setError("");
    } catch (err) {
      setError(err.message);
      setPost(null);
    } finally {
      setFetching(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  if (fetching || loading) {
    return <p className="muted">Loading post…</p>;
  }

  if (error || !post) {
    return (
      <div className="stack">
        <div className="banner banner-warn">
          <strong>Post not available</strong>
          <span>{error || "This post does not exist or was deleted."}</span>
        </div>
        <Link className="btn btn-secondary" href="/">
          Back home
        </Link>
      </div>
    );
  }

  return (
    <div className="stack">
      <div className="row between">
        <h2>Post</h2>
        <Link className="btn btn-ghost btn-sm" href={`/u/${post.author.username}`}>
          @{post.author.username}
        </Link>
      </div>

      <PostCard
        post={post}
        showOpen={false}
        onDeleted={() => router.push(`/u/${post.author.username}`)}
        onUpdated={(updated) => setPost(updated)}
      />

      <div className="banner banner-warn">
        <strong>⚠ Comments are not implemented yet</strong>
        <span>
          Threaded comments and one-level replies arrive in Phase 3. The post
          itself is fully live.
        </span>
      </div>
    </div>
  );
}
