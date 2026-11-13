"use client";

import Link from "next/link";

import { useAuth } from "@/components/AuthProvider";
import UserSearch from "@/components/UserSearch";

export default function DiscoverPage() {
  const { me, loading } = useAuth();

  return (
    <div className="stack">
      <section className="hero">
        <span className="eyebrow">Discover</span>
        <h1>Find people to follow.</h1>
        <p>
          Search by display name or @username, then follow in one click.
          Following someone updates their follower count and personalises their
          profile immediately.
        </p>
      </section>

      <section className="card card-pad">
        <h2>People</h2>
        <p className="muted" style={{ marginBottom: 16 }}>
          At least two characters. Your own account is left out of the results.
        </p>
        <UserSearch autoFocus />
      </section>

      {!loading && !me && (
        <div className="banner banner-warn">
          <strong>Log in to follow</strong>
          <span>
            Searching works without an account, but following needs one.{" "}
            <Link href="/login">Log in</Link> or{" "}
            <Link href="/register">create an account</Link>.
          </span>
        </div>
      )}

      <div className="banner banner-warn">
        <strong>⚠ Full search is not implemented yet</strong>
        <span>
          People search is live now because Phase 2 includes follow. Searching
          posts, hashtags and mentions arrives with Phase 5.
        </span>
      </div>
    </div>
  );
}
