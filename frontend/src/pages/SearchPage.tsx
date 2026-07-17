import { useState, useEffect } from "react";
import { useSearchParams } from "react-router";
import { useOutletContext } from "react-router";
import type { Track } from "./../types";
import { searchTracks } from "./../api";
import TrackList from "./../components/TrackList";
import LoadingSpinner from "./../components/LoadingSpinner";
import { usePlayerContext } from "./../PlayerContext";
import "./SearchPage.css";

type AppLayoutContext = {
  onPlay: (track: Track) => void;
};

type SearchResultsStatus = "DONE" | "ERROR" | "EMPTY";
type SearchResultsState = {
  data: Track[];
  status: SearchResultsStatus;
}

export default function SearchPage() {
  const [results, setResults] = useState<SearchResultsState>({ data: [], status: "DONE" });
  const [isLoading, setLoading] = useState(false);
  const { onPlay } = useOutletContext<AppLayoutContext>();
  const { dispatch } = usePlayerContext();
  const [searchParams] = useSearchParams();

  useEffect(() => {
    if (isLoading) {
      return;
    }

    // Close the player after user search
    dispatch({ type: "close" });
    setLoading(true);

    const query = searchParams.get("q");
    if (!query) {
      return;
    }

    searchTracks(query)
      .then(resp => {
        setResults({
          data: resp.results,
          status: resp.results.length !== 0 ? "DONE" : "EMPTY"
        });
      })
      .catch(err => {
        console.error("Error while searching for tracks: ", err);
        setResults({ data: [], status: "ERROR" });
      }).finally(() => {
        setLoading(false);
      });
  }, [searchParams]);

  function renderContent() {
    if (isLoading) {
      return <LoadingSpinner />;
    }

    switch (results.status) {
      case "DONE":
        return (
          <>
            <h2>Search results</h2>
            <TrackList tracks={results.data} onPlay={onPlay}></TrackList>
          </>
        );
      case "ERROR":
        return (
          <div className="search-state search-state-error" role="status" aria-live="polite">
            <h2>Search unavailable</h2>
            <p>There was an error while loading tracks. Please try again.</p>
          </div>
        );
      case "EMPTY":
      default:
        return (
          <div className="search-state search-state-empty" role="status" aria-live="polite">
            <h2>No matches found</h2>
            <p>Try a different track title or artist name.</p>
          </div>
        );
    }
  }

  return (
    <div className="search-page container">
      {renderContent()}
    </div>
  );
}