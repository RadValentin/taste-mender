import { Link } from "react-router";
import PageMetadata from "../components/PageMetadata";

export default function NotFoundPage() {
  return (
    <>
      <PageMetadata
        title="Page Not Found | TasteMender"
        description="The requested page could not be found."
        robots="noindex"
      />

      <div className="not-found-page container">
        <h1>Page not found</h1>
        <p>
          The page may have been moved, deleted, or the address may be incorrect.
        </p>

        <Link className="btn btn-neon" to="/">
          Return home
        </Link>
      </div>
    </>
  );
}