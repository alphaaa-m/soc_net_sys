"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { useAuth } from "@/components/AuthProvider";
import { initials } from "@/lib/format";

export default function Nav() {
  const pathname = usePathname();
  const router = useRouter();
  const { me, loading, logout } = useAuth();

  const links = [
    { href: "/", label: "Home" },
    { href: "/modules", label: "Roadmap" },
  ];
  if (me) links.push({ href: "/profile", label: "My profile" });

  const signOut = async () => {
    await logout();
    router.push("/");
  };

  return (
    <aside className="sidebar">
      <Link href="/" className="brand">
        <span className="brand-mark">C</span>
        <span className="brand-text">
          Chirp
          <small>text-first social</small>
        </span>
      </Link>

      <nav className="nav" aria-label="Main">
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={`nav-link ${pathname === link.href ? "active" : ""}`}
          >
            {link.label}
          </Link>
        ))}
      </nav>

      <div className="sidebar-foot">
        {loading ? (
          <span className="muted">Loading…</span>
        ) : me ? (
          <div className="stack-sm">
            <Link href="/profile" className="mini-profile">
              <span className="avatar sm">{initials(me.display_name)}</span>
              <span>
                <strong>{me.display_name}</strong>
                <small className="muted">@{me.username}</small>
              </span>
            </Link>
            <button type="button" className="btn btn-ghost btn-sm" onClick={signOut}>
              Log out
            </button>
          </div>
        ) : (
          <div className="stack-sm">
            <Link href="/login" className="btn btn-secondary btn-sm">
              Log in
            </Link>
            <Link href="/register" className="btn btn-primary btn-sm">
              Create account
            </Link>
          </div>
        )}
        <div className="phase-pill">Phase 1–2 live</div>
      </div>
    </aside>
  );
}
