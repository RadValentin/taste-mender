import { useRef } from "react";
import { useNavigate, useSearchParams, Link } from "react-router";
import { API_BASE_URL } from "../api";
import "./Header.css"

/** App header: TasteMender logo, search bar (fires `onSearch` on Enter or button click),
 *  and a link to the REST API docs. */
export default function Header() {
  const [searchParams] = useSearchParams();
  const queryString = searchParams.get("q") ?? "";
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const inputPlaceholder = `Search for track or artist...`;

  function onSearch() {
    const query: string = inputRef.current?.value || '';

    if (query.trim()) {
      navigate(`/search?q=${encodeURIComponent(query.trim())}`);
    } else {
      navigate("/");
    }
  }

  function onInputKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      onSearch();
    }
  }

  return (
    <header className="header">
      <div className="header__inner">
        <Link className="header__logo" to="/" aria-label="TasteMender">
          <span className="header__logo-line">Taste</span>
          <span className="header__logo-line header__logo-accent">Mender</span>
        </Link>
        <div className="header__search-box">
          <input
            key={queryString}
            ref={inputRef}
            name="search"
            type="search"
            defaultValue={queryString}
            placeholder={inputPlaceholder}
            onKeyDown={onInputKeyDown}
          />
          <button
            type="button"
            className="btn btn-metal"
            aria-label="Search"
            onClick={onSearch}
          >
            <i className="fa-solid fa-magnifying-glass"></i>
          </button>
        </div>
        <div className="header__links">
          <a className="btn btn-amber" href={API_BASE_URL}>API</a>
        </div>
      </div>
    </header>
  );
}