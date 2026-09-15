import { useState, useEffect, useRef } from "react";
import { useSearchParams } from "react-router";
import { useOutletContext } from "react-router";
import type { Track } from "./../types";
import { searchTracks } from "./../api";
import PageMetadata from "./../components/PageMetadata.tsx";
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

const SEARCH_LIMIT = 25;

export default function SearchPage() {
  const [results, setResults] = useState<SearchResultsState>({ data: [], status: "DONE" });
  const [isLoading, setLoading] = useState(false);
  const [isLoadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const loadMoreController = useRef<AbortController | null>(null);
  const { onPlay } = useOutletContext<AppLayoutContext>();
  const { dispatch } = usePlayerContext();
  const [searchParams] = useSearchParams();

  // Initial search (though input or navigation)
  useEffect(() => {
    const query = searchParams.get("q");

    // Close the player after user search
    dispatch({ type: "close" });
    loadMoreController.current?.abort();

    if (!query) {
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    setLoading(true);
    setLoadingMore(false);
    searchTracks(query, SEARCH_LIMIT, 0, controller.signal)
      .then(resp => {
        setResults({
          data: resp.results,
          status: resp.results.length !== 0 ? "DONE" : "EMPTY"
        });
        setHasMore(resp.results.length >= SEARCH_LIMIT);
      })
      .catch(err => {
        if (controller.signal.aborted) {
          return;
        }

        console.error("Error while searching for tracks: ", err);
        setResults({ data: [], status: "ERROR" });
        setHasMore(false);
      }).finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => {
      controller.abort();
      loadMoreController.current?.abort();
    };
  }, [searchParams]);

  // Loading more search results
  function handleLoadMore() {
    const query = searchParams.get("q");
    if (!query || isLoadingMore) {
      return;
    }

    const offset = results.data.length;
    const controller = new AbortController();
    loadMoreController.current = controller;
    setLoadingMore(true);

    searchTracks(query, SEARCH_LIMIT, offset, controller.signal)
      .then(resp => {
        setResults(previous => ({
          data: [...previous.data, ...resp.results],
          status: "DONE",
        }));
        setHasMore(resp.results.length >= SEARCH_LIMIT);
      })
      .catch(err => {
        if (!controller.signal.aborted) {
          console.error("Error while loading more search results: ", err);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoadingMore(false);
        }
      });

  }

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
            {hasMore && (
              <button
                type="button"
                className="btn btn-neon"
                onClick={handleLoadMore}
                disabled={isLoadingMore}
              >
                {isLoadingMore ? "Loading..." : "Load More"}
              </button>
            )}
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
    <>
      <PageMetadata
        title="Search | TasteMender"
        description="Search TasteMender by track title or artist and discover acoustically similar music."
      />
      <div className="search-page container">
        {renderContent()}
      </div>
    </>
  );
}