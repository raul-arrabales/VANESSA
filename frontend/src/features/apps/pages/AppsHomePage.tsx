import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../../auth/AuthProvider";
import { listApps, type VanessaApp } from "../../../api/apps";

export default function AppsHomePage(): JSX.Element {
  const { token, isLoading: isAuthLoading } = useAuth();
  const [apps, setApps] = useState<VanessaApp[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (isAuthLoading) {
      return;
    }
    if (!token) {
      setApps([]);
      setError("");
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    void listApps(token)
      .then((items) => {
        if (!cancelled) {
          setApps(items);
          setError("");
        }
      })
      .catch((requestError) => {
        if (!cancelled) {
          setError(requestError instanceof Error ? requestError.message : "Unable to load apps.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [isAuthLoading, token]);

  return (
    <section className="card-stack">
      <article className="panel card-stack">
        <h2 className="section-title">Apps</h2>
        <p className="status-text">Published Vanessa WebApp chat agents appear here for authenticated users.</p>
      </article>
      {loading ? <p className="status-text">Loading apps...</p> : null}
      {error ? <p className="status-text error-text">{error}</p> : null}
      {!loading && !error && apps.length === 0 ? (
        <article className="panel card-stack">
          <p className="status-text">No apps are published yet.</p>
        </article>
      ) : null}
      {apps.map((app) => (
        <article key={app.id} className="panel card-stack">
          <div className="status-row">
            <div className="card-stack">
              <h3 className="section-title">{app.name}</h3>
              <p className="status-text">{app.description}</p>
            </div>
            <Link className="btn btn-primary" to={`/apps/${app.id}`}>Open app</Link>
          </div>
          <div className="inline-meta-list">
            <span>{app.agent_type}</span>
            <span>{app.channel_type}</span>
            <span>{app.interface_type}</span>
          </div>
        </article>
      ))}
    </section>
  );
}
