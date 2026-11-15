"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { FEATURES } from "@/lib/features";

export default function ComingSoonPage() {
  const { slug } = useParams();
  const feature = FEATURES[slug];

  if (!feature) {
    return (
      <div className="stack">
        <div className="banner banner-warn">
          <strong>Unknown roadmap item</strong>
          <span>That feature does not exist in the roadmap registry.</span>
        </div>
        <Link className="btn btn-secondary" href="/modules">
          Back to the roadmap
        </Link>
      </div>
    );
  }

  return (
    <div className="stack">
      <section className="coming">
        <span className="badge badge-todo">
          Phase {feature.phase} · Not yet implemented
        </span>
        <h1>⚠ {feature.title} is on the roadmap.</h1>
        <p>{feature.blurb}</p>
        <p style={{ marginTop: 14 }}>
          The backend endpoints for this screen have not been built yet, so the
          UI intentionally stops here instead of showing fake data.
        </p>
        <span className="endpoint">Planned API: {feature.endpoints}</span>
        <div className="row" style={{ marginTop: 22 }}>
          <Link className="btn btn-primary" href="/modules">
            View the full roadmap
          </Link>
          <Link className="btn btn-secondary" href="/">
            Back to what works today
          </Link>
        </div>
      </section>
    </div>
  );
}
