"use client";

import { useState } from "react";

import { useAuth } from "@/components/AuthProvider";
import { api } from "@/lib/api";

export default function FollowButton({ profile, onChange }) {
  const { me } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (!me || me.id === profile.id) return null;

  const following = profile.is_following;

  const toggle = async () => {
    setBusy(true);
    setError("");
    try {
      await api(`/users/${profile.id}/follow`, {
        method: following ? "DELETE" : "PUT",
      });
      onChange?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="stack-sm">
      <button
        type="button"
        className={`btn ${following ? "btn-secondary" : "btn-primary"}`}
        onClick={toggle}
        disabled={busy}
      >
        {busy ? "…" : following ? "Following" : "Follow"}
      </button>
      {error && <p className="error">{error}</p>}
    </div>
  );
}
