import { useState, useEffect, useRef, useLayoutEffect } from "react";
import { useSearchParams } from "react-router";
import type { Track } from "./../types";
import { searchTracks, getTracks } from "./../api";
import { getScrollbarWidth } from "./../layout";
import TrackList from "./../components/TrackList";
import LoadingSpinner from "./../components/LoadingSpinner";
import Player, { type PlayerRef } from "./../components/Player";
import { usePlayerContext } from "./../PlayerContext";

type SearchResultsStatus = "DONE" | "ERROR" | "EMPTY";
type SearchResultsState = {
  data: Track[];
  status: SearchResultsStatus;
}

export default function SearchPage() {
  const [results, setResults] = useState<SearchResultsState>({ data: [], status: "DONE" });
  const [isLoading, setLoading] = useState(false);
  const { dispatch } = usePlayerContext();
  const playerRef = useRef<PlayerRef>(null);
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

  if (isLoading) {
    return <div className="content"><LoadingSpinner /></div>;
  }

  if (results.status === "DONE") {
    return (
      <div className="content">
        <h2>Search results</h2>
        <TrackList tracks={results.data} onPlay={track => { playerRef.current?.loadAndPlay(track) }}></TrackList>
      </div>
    );
  }

  if (results.status === "ERROR") {
    return <div className="content">There was an error while loading the tracks</div>;
  }

  return <div className="content">No results</div>;
}