import { useState } from "react";
import { useNavigate } from "react-router";
import { API_BASE_URL } from "../api";
import "./Header.css"

export default function Header() {
  const [searchQuery, setSearchQuery] = useState("");
  const navigate = useNavigate();
  const inputPlaceholder = `Search for track or artist...`;

  function onSearch(query: string) {
    if (query.trim()) {
      navigate(`/search?q=${encodeURIComponent(query.trim())}`);
    } else {
      navigate("/");
    }
  }

  function onInputKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      onSearch(searchQuery);
    }
  }

  return (
    <header className="header">
      <div className="header-inner">
        <a className="logo" href="/" aria-label="TasteMender">
          <span className="logo-line">Taste</span>
          <span className="logo-line logo-mender">Mender</span>
        </a>
        <div className="search-box">
          <input
            name="search"
            type="search"
            value={searchQuery}
            placeholder={inputPlaceholder}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={onInputKeyDown}
          />
          <button
            type="button"
            className="btn btn-metal btn-search"
            aria-label="Search"
            onClick={() => {onSearch(searchQuery)}}
          >
            <i className="fa-solid fa-magnifying-glass"></i>
          </button>
        </div>
        <div className="links">
          <a className="btn btn-amber" href={API_BASE_URL}>API</a>
          {/* <a href="#">About</a> */}
        </div>
      </div>
    </header>
  );
}