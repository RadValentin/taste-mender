import { useState, useEffect } from "react";
import { useOutletContext } from "react-router";
import type { Track } from "./../types";
import { getTracks } from "./../api";
import TrackList from "./../components/TrackList";
import LoadingSpinner from "./../components/LoadingSpinner";
import "./HomePage.css";

type AppLayoutContext = {
  onPlay: (track: Track) => void;
};

type HomeResultsStatus = "DONE" | "ERROR"  | "EMPTY";
type HomeResultsState = {
  data: Track[];
  status: HomeResultsStatus;
}

export default function HomePage() {
  const [results, setResults] = useState<HomeResultsState>({ data: [], status: "DONE" });
  const [isLoading, setLoading] = useState(false);
  const { onPlay } = useOutletContext<AppLayoutContext>();

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

  function renderContent() {
    if (isLoading) {
      return <LoadingSpinner />;
    }
    // All of this will become part of the carousel
    switch (results.status) {
      case "DONE":
        return (
          <>
            <h2>Top tracks</h2>
            <TrackList tracks={results.data} onPlay={onPlay}></TrackList>
          </>
        );
      case "ERROR":
        return <div>There was an error while loading the tracks</div>;
      case "EMPTY":
      default:
        return <div>No results</div>;
    }
  }

  return (
    <div className="home-page container">
      {renderContent()}
    </div>
  );
}