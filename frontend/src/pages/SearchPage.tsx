import { useEffect } from "react";
import { useSearchParams } from "react-router";
import { useOutletContext } from "react-router";
import type { AppLayoutContext } from "./../types";
import { searchTracks } from "./../api";
import LoadingSpinner from "../components/LoadingSpinner.tsx";
import PageMetadata from "./../components/PageMetadata.tsx";
import TrackList from "./../components/TrackList";
import TrackListSkeleton from "./../components/TrackListSkeleton.tsx";
import StatusMessage from "./../components/StatusMessage";
import "./../components/StatusMessage.css";
import { usePlaybackContext } from "./../PlaybackContext";
import { useInfiniteQuery } from "@tanstack/react-query";
import "./SearchPage.css";

// How many results to load at a time.
const SEARCH_LIMIT = 25;

export default function SearchPage() {
  const { onPlay } = useOutletContext<AppLayoutContext>();
  const { dispatch } = usePlaybackContext();
  const [searchParams] = useSearchParams();
  const queryStr = searchParams.get("q") || "";
  const {
    data, isLoading, isError, isFetching, isFetchingNextPage, isFetchNextPageError, hasNextPage,
    fetchNextPage,
  } = useInfiniteQuery({
    queryKey: ["search", "tracks", queryStr],
    queryFn: ({ pageParam, signal }) =>
      searchTracks(queryStr, SEARCH_LIMIT, pageParam, signal),
    initialPageParam: 0,
    getNextPageParam: (lastPage, _allPages, lastPageParam) => {
      return lastPage.has_more
        ? lastPageParam + SEARCH_LIMIT
        : undefined;
    },
    enabled: queryStr.length > 0,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: false,
  });
  const tracks = data?.pages.flatMap(page => page.results) ?? [];

  // Close the player after user search
  useEffect(() => {
    dispatch({ type: "CLOSE_PLAYER" });
  }, [queryStr, dispatch]);

  function handleLoadMore() {
    if (hasNextPage && !isFetching) {
      void fetchNextPage();
    }
  }

  function renderLoadMoreButton() {
    if (!hasNextPage) {
      return null;
    }

    let content;
    if (isFetchingNextPage) {
      content = (
        <>
          <LoadingSpinner variant="icon" />
          Loading...
        </>
      );
    } else if (isFetchNextPageError) {
      content = "Try again";
    } else {
      content = "Load More";
    }

    return (
      <button type="button"
        className="btn btn-neon"
        onClick={handleLoadMore}
        disabled={isFetching}
      >
        {content}
      </button>
    )
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

    // Only replace the whole page if there are no previously loaded results.
    if (isError && !data) {
      return (
        <StatusMessage
          title="Search unavailable"
          description="There was an error while loading tracks. Please try again."
          variant="error"
        />
      );
    }

    if (tracks.length === 0) {
      return (
        <StatusMessage
          title="No matches found"
          description="Try a different track title or artist name."
          variant="info"
        />
      );
    }

    return (
      <>
        <h2>Search results</h2>
        <TrackList tracks={tracks} onPlay={onPlay} />

        {isFetchNextPageError && (
          <StatusMessage
            title="Could not load more tracks"
            description="Your previous results are still available. Please try again."
            variant="error"
          />
        )}
      </>
    );
  }


  // Main Render
  return (
    <>
      <PageMetadata
        title="Search | TasteMender"
        description="Search TasteMender by track title or artist and discover acoustically similar music."
      />
      <div className="search-page container">
        {renderContent()}
        <div className="search-page__footer">
          {renderLoadMoreButton()}
        </div>
      </div>
    </>
  );
}