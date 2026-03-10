import { useState } from 'react';
import { API_BASE_URL } from '../api';
import './Header.css'

export default function Header({onSearch}: { onSearch: (query: string) => void }) {
  const [searchQuery, setSearchQuery] = useState("");

  const inputPlaceholder = `Search for track or artist...`;

  function onInputKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      onSearch(searchQuery)
    }
  }

  return (
    <div className="header">
      <a className="logo" href="/">TasteMender</a>
      <div>
        <input
          value={searchQuery}
          placeholder={inputPlaceholder}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={onInputKeyDown}
        />
      </div>
      <div style={{textAlign: "right"}}>
        <a href={API_BASE_URL}>API</a>
        {/* <a href="#">About</a> */}
      </div>
    </div>
  );
}