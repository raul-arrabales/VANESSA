import { Link } from "react-router-dom";

export default function NotFoundPage(): JSX.Element {
  return (
    <section className="panel card-stack">
      <h2 className="section-title">Page not found</h2>
      <p className="status-text">The requested page is not part of the current frontend sitemap.</p>
      <div className="button-row">
        <Link to="/" className="btn btn-primary">Return home</Link>
      </div>
    </section>
  );
}
