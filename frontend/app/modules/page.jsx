import Link from "next/link";

import { PHASES } from "@/lib/features";

export const metadata = {
  title: "Roadmap — Chirp",
};

export default function ModulesPage() {
  return (
    <div className="stack">
      <section className="hero">
        <span className="eyebrow">Build log</span>
        <h1>Everything, phase by phase.</h1>
        <p>
          Green means the feature is live and backed by real API endpoints.
          Amber means the screen is deliberately a warning: the phase has not
          been built yet, so nothing pretends to work.
        </p>
        <div className="row" style={{ marginTop: 22 }}>
          <Link className="btn btn-primary" href="/">
            Open the live app
          </Link>
          <Link className="btn btn-secondary" href="/register">
            Create an account
          </Link>
        </div>
      </section>

      <div className="module-grid">
        {PHASES.map((phase) => (
          <section key={phase.phase} className="card module-card">
            <div className="row between">
              <span className="eyebrow">Phase {phase.phase}</span>
              <span
                className={`badge ${
                  phase.status === "done" ? "badge-done" : "badge-todo"
                }`}
              >
                {phase.status === "done" ? "Live" : "Not yet"}
              </span>
            </div>
            <h3>{phase.title}</h3>
            <p className="muted">{phase.blurb}</p>
            <ul className="module-list">
              {phase.items.map((item) => (
                <li key={item.label}>
                  {item.done ? (
                    <span>{item.label}</span>
                  ) : (
                    <Link href={`/coming-soon/${item.slug}`}>{item.label}</Link>
                  )}
                  <span
                    className={`badge ${
                      item.done ? "badge-done" : "badge-todo"
                    }`}
                  >
                    {item.done ? "Live" : `Phase ${phase.phase}`}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}
