import { useState, useEffect } from "react";
import { useSearchParams } from "react-router";
import { useOutletContext } from "react-router";
import type { Track } from "./../types";
import { searchTracks } from "./../api";
import TrackList from "./../components/TrackList";
import TrackListSkeleton from "./../components/TrackListSkeleton.tsx";
import StatusMessage from "./../components/StatusMessage";
import "./../components/StatusMessage.css";
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
    const query = searchParams.get("q");

    // Close the player after user search
    dispatch({ type: "close" });

    if (!query) {
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    setLoading(true);
    searchTracks(query, 25, controller.signal)
      .then(resp => {
        setResults({
          data: resp.results,
          status: resp.results.length !== 0 ? "DONE" : "EMPTY"
        });
      })
      .catch(err => {
        if (err.code === "ERR_CANCELED") {
          return;
        }

        console.error("Error while searching for tracks: ", err);
        setResults({ data: [], status: "ERROR" });
      }).finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => {
      controller.abort();
    };
  }, [searchParams]);

  function renderContent() {
    if (isLoading) {
      return (
        <>
          <h2>Searching</h2>
          <TrackListSkeleton count={10} variant="list" />
        </>
      );
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
          <StatusMessage
            title="Search unavailable"
            description="There was an error while loading tracks. Please try again."
            variant="error"
          />
        );
      case "EMPTY":
      default:
        return (
          <StatusMessage
            title="No matches found"
            description="Try a different track title or artist name."
            variant="info"
          />
        );
    }
  }

  return (
    <div className="search-page container">
      {renderContent()}
    </div>
  );
}