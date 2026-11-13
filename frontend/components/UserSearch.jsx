"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { useAuth } from "@/components/AuthProvider";
import FollowButton from "@/components/FollowButton";
import { api } from "@/lib/api";
import { initials } from "@/lib/format";

/**
 * Debounced people search with inline follow/unfollow buttons.
 *
 * Backed by `GET /users?q=` (Phase 2 discovery aid). Results are personalised
 * with `is_following` when the caller is logged in, so the buttons reflect the
 * real follow graph instead of guessing.
 */
export default function UserSearch({
  autoFocus = false,
  placeholder = "Search by name or @username",
}) {
  const { me } = useAuth();
  const [query, setQuery] = useState("");
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");
  const latestRequest = useRef(0);

  const term = query.trim();

  useEffect(() => {
    const request = ++latestRequest.current;

    if (term.length < 2) {
      setItems([]);
      setTotal(0);
      setError("");
      setStatus("idle");
      return undefined;
    }

    setStatus("loading");
    const timer = setTimeout(async () => {
      try {
        const page = await api(
          `/users?q=${encodeURIComponent(term)}&limit=20`,
        );
        if (request !== latestRequest.current) return;
        setItems(page.items);
        setTotal(page.total);
        setError("");
        setStatus("done");
      } catch (err) {
        if (request !== latestRequest.current) return;
        setItems([]);
        setTotal(0);
        setError(err.message);
        setStatus("error");
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [term]);

  const applyFollowState = (id, following) => {
    setItems((list) =>
      list.map((person) =>
        person.id === id ? { ...person, is_following: following } : person,
      ),
    );
  };

  return (
    <div className="user-search">
      <div className="search-wrap">
        <svg
          className="search-icon"
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          aria-hidden="true"
        >
          <circle cx="11" cy="11" r="7" />
          <path d="m20 20-3.5-3.5" />
        </svg>
        <input
          type="search"
          className="input search-input"
          placeholder={placeholder}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          autoFocus={autoFocus}
          aria-label="Search people"
        />
      </div>

      <p className="muted search-meta" aria-live="polite">
        {term.length < 2
          ? "Type at least 2 characters."
          : status === "loading"
            ? "Searching…"
            : status === "done"
              ? `${total} ${total === 1 ? "person" : "people"} found`
              : ""}
      </p>

      {error && <p className="error">{error}</p>}

      {status === "done" && items.length === 0 && (
        <div className="empty card">
          No one matches “{term}”. Try another name or username.
        </div>
      )}

      {items.length > 0 && (
        <div className="card user-results">
          {items.map((person) => (
            <div key={person.id} className="user-row">
              <Link href={`/u/${person.username}`} className="avatar sm">
                {initials(person.display_name)}
              </Link>
              <div className="user-row-info">
                <Link href={`/u/${person.username}`}>
                  <strong>{person.display_name}</strong>
                </Link>
                <small className="muted">
                  @{person.username}
                  {person.bio ? ` · ${person.bio}` : ""}
                </small>
              </div>
              {me ? (
                <FollowButton
                  profile={person}
                  size="sm"
                  onChange={(following) =>
                    applyFollowState(person.id, following)
                  }
                />
              ) : (
                <Link className="btn btn-secondary btn-sm" href="/login">
                  Log in to follow
                </Link>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
