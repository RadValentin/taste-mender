import { useState, useEffect, useRef, useLayoutEffect } from "react";
import type { Track } from "./../types";
import { searchTracks, getTracks } from "./../api";
import TrackList from "./../components/TrackList";
import LoadingSpinner from "./../components/LoadingSpinner";
import Player, { type PlayerRef } from "./../components/Player";
import { usePlayerContext } from "./../PlayerContext";

type HomeResultsStatus = "DONE" | "ERROR"  | "EMPTY";
type HomeResultsState = {
  data: Track[];
  status: HomeResultsStatus;
}

export default function HomePage() {
  const [results, setResults] = useState<HomeResultsState>({ data: [], status: "DONE" });
  const [isLoading, setLoading] = useState(false);
  const {dispatch} = usePlayerContext();
  const playerRef = useRef<PlayerRef>(null);

  function loadTopTracks() {
    setLoading(true);
    getTracks("-submissions")
      .then(resp => {
        setResults({
          data: resp.results,
          status: resp.results.length !== 0 ? "DONE" : "EMPTY"
        });
        setLoading(false);
      })
      .catch(err => {
        console.error("Error while searching loading top tracks:", err);
        setResults({ data: [], status: "ERROR" });
        setLoading(false);
      });
  }

  useEffect(() => {
    // Fetch top track data only once on mount.
    loadTopTracks();
  }, []);

  if (isLoading) {
    return <div className="content"><LoadingSpinner /></div>;
  }

  if (results.status === "DONE") {
    return (
      <div className="content">
        <h2>Top tracks</h2>
        <TrackList tracks={results.data} onPlay={track => { playerRef.current?.loadAndPlay(track) }}></TrackList>
      </div>
    );
  }

  if (results.status === "ERROR") {
    return <div className="content">There was an error while loading the tracks</div>;
  }

  return <div className="content">No results</div>;
}