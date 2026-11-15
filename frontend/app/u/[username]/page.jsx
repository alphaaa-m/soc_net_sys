"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/AuthProvider";
import FollowButton from "@/components/FollowButton";
import PostCard from "@/components/PostCard";
import { api } from "@/lib/api";
import { formatJoined, initials } from "@/lib/format";

const TABS = [
  { key: "posts", label: "Posts" },
  { key: "followers", label: "Followers" },
  { key: "following", label: "Following" },
];

export default function PublicProfilePage() {
  const { username } = useParams();
  const { me, loading: authLoading } = useAuth();
  const [profile, setProfile] = useState(null);
  const [tab, setTab] = useState("posts");
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [fetching, setFetching] = useState(true);

  const loadProfile = useCallback(async () => {
    try {
      const data = await api(`/users/${username}`);
      setProfile(data);
      setError("");
      return data;
    } catch (err) {
      setError(err.message);
      setProfile(null);
      return null;
    } finally {
      setFetching(false);
    }
  }, [username]);

  const loadTab = useCallback(
    async (key) => {
      setItems([]);
      setNotice("");
      try {
        const path =
          key === "posts"
            ? `/users/${username}/posts?limit=20`
            : `/users/${username}/${key}?limit=20`;
        const page = await api(path);
        setItems(page.items);
      } catch (err) {
        setNotice(err.message);
      }
    },
    [username],
  );

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  useEffect(() => {
    if (profile) loadTab(tab);
  }, [profile, tab, loadTab]);

  if (fetching) {
    return <p className="muted">Loading profile…</p>;
  }

  if (error || !profile) {
    return (
      <div className="stack">
        <div className="banner banner-warn">
          <strong>Profile not available</strong>
          <span>
            {error || "This account does not exist or has been deactivated."}
          </span>
        </div>
        <div className="row">
          <Link className="btn btn-secondary" href="/modules">
            Back to the roadmap
          </Link>
          <Link className="btn btn-ghost" href="/">
            Go home
          </Link>
        </div>
      </div>
    );
  }

  const refreshAfterFollow = async () => {
    await loadProfile();
    await loadTab(tab);
  };

  return (
    <div className="stack">
      <section className="card card-pad">
        <div className="profile-head">
          <span className="avatar lg">{initials(profile.display_name)}</span>
          <div className="profile-info">
            <div className="row between">
              <div>
                <h1 className="profile-name">{profile.display_name}</h1>
                <span className="handle">@{profile.username}</span>
              </div>
              <FollowButton profile={profile} onChange={refreshAfterFollow} />
            </div>
            <p className="bio">{profile.bio || "No bio yet."}</p>
            <div className="counts">
              <div className="count">
                <strong>{profile.followers_count}</strong>
                <span>Followers</span>
              </div>
              <div className="count">
                <strong>{profile.following_count}</strong>
                <span>Following</span>
              </div>
              <div className="count">
                <strong>{profile.posts_count}</strong>
                <span>Posts</span>
              </div>
            </div>
            <p className="muted">Joined {formatJoined(profile.created_at)}</p>
          </div>
        </div>
      </section>

      {me && me.id === profile.id && (
        <div className="banner banner-info">
          <strong>This is your profile</strong>
          <span>
            You cannot follow yourself.{" "}
            <Link href="/discover">Find people to follow</Link> in Discover.
          </span>
        </div>
      )}

      <div className="tabs">
        {TABS.map((item) => (
          <button
            key={item.key}
            type="button"
            className={`tab ${tab === item.key ? "active" : ""}`}
            onClick={() => setTab(item.key)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {notice && <p className="error">{notice}</p>}

      {tab === "posts" ? (
        items.length === 0 ? (
          <div className="empty card">No posts yet.</div>
        ) : (
          <div className="stack">
            {items.map((post) => (
              <PostCard
                key={post.id}
                post={post}
                onDeleted={() => {
                  loadTab("posts");
                  loadProfile();
                }}
                onUpdated={() => loadTab("posts")}
              />
            ))}
          </div>
        )
      ) : (
        <div className="card">
          {items.length === 0 ? (
            <div className="empty">Nobody here yet.</div>
          ) : (
            items.map((person) => (
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
                {me && person.id === me.id ? (
                  <span className="badge">You</span>
                ) : (
                  <FollowButton
                    profile={person}
                    size="sm"
                    onChange={() => {
                      loadTab(tab);
                      loadProfile();
                    }}
                  />
                )}
              </div>
            ))
          )}
        </div>
      )}

      {!me && !authLoading && (
        <div className="banner banner-warn">
          <strong>Log in to follow</strong>
          <span>
            <Link href="/login">Log in</Link> or{" "}
            <Link href="/register">create an account</Link> to follow people and
            personalise this page.
          </span>
        </div>
      )}
    </div>
  );
}
