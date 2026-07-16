// import { useState, useEffect, useRef, useLayoutEffect } from "react";
// import type { Track } from "./types";
// import { searchTracks, getTracks } from "./api";
// import { getScrollbarWidth } from "./layout";
// import TrackList from "./components/TrackList";
// import LoadingSpinner from "./components/LoadingSpinner";


import { useState, useEffect, useRef, useLayoutEffect } from "react";
import { Outlet } from "react-router";
import Header from "./components/Header";
import Player, { type PlayerRef } from "./components/Player";
import { usePlayerContext } from "./PlayerContext";
import "./AppLayout.css";


// type ResultsStatus = "TOP" | "SEARCH" | "ERROR"  | "EMPTY";
// type ResultsState = {
//   data: Track[];
//   status: ResultsStatus;
// }

// function App() {
//   const [results, setResults] = useState<ResultsState>({ data: [], status: "TOP" });
//   const [isLoading, setLoading] = useState(false);
//   const {state: playerState, dispatch} = usePlayerContext();
//   const playerRef = useRef<PlayerRef>(null);

//   function onSearch(query: string) {
//     if (isLoading) {
//       return;
//     }
//     if (!query) {
//       loadTopTracks();
//       return;
//     }

//     // Close the player after user search
//     dispatch({type: "close"});
//     setLoading(true);

//     searchTracks(query)
//       .then(resp => {
//         setResults({
//           data: resp.results,
//           status: resp.results.length !== 0 ? "SEARCH" : "EMPTY"
//         });
//       })
//       .catch(err => {
//         console.error("Error while searching for tracks: ", err);
//         setResults({ data: [], status: "ERROR" });
//       }).finally(() => {
//           setLoading(false);
//       });
//   }

//   function loadTopTracks() {
//     setLoading(true);
//     getTracks("-submissions")
//       .then(resp => {
//         setResults({
//           data: resp.results,
//           status: resp.results.length !== 0 ? "TOP" : "EMPTY"
//         });
//         setLoading(false);
//       })
//       .catch(err => {
//         console.error("Error while searching loading top tracks:", err);
//         setResults({ data: [], status: "ERROR" });
//         setLoading(false);
//       });
//   }

//   useLayoutEffect(() => {
//     // Set global CSS properties which need to be pre-calculated before first paint
//     document.documentElement.style.setProperty("--scrollbar-width", `${getScrollbarWidth()}px`);
//   }, []);

//   useEffect(() => {
//     // Display top track only once on mount
//     loadTopTracks();
//   }, []);

//   // Disable scrolling on body when the player drawer is maximized
//   useEffect(() => {
//     const bodyClassName = "scroll-locked";

//     if (playerState.isMaximized) {
//       document.body.classList.add(bodyClassName);
//     } else {
//       document.body.classList.remove(bodyClassName);
//     }

//     return () => {
//       document.body.classList.remove(bodyClassName);
//     };
//   }, [playerState.isMaximized]);

//   const renderContent = () => {
//     if (isLoading) {
//       return <div className="content"><LoadingSpinner /></div>;
//     }

//     if (results.status === "TOP") {
//       return (
//         <div className="content">
//           <h2>Top tracks</h2>
//           <TrackList tracks={results.data} onPlay={track => { playerRef.current?.loadAndPlay(track) }}></TrackList>
//         </div>
//       );
//     }

//     if (results.status === "SEARCH") {
//       return (
//         <div className="content">
//           <h2>Search results</h2>
//           <TrackList tracks={results.data} onPlay={track => { playerRef.current?.loadAndPlay(track) }}></TrackList>
//         </div>
//       );
//     }

//     if (results.status === "ERROR") {
//       return <div className="content">There was an error while loading the tracks</div>;
//     }

//     return <div className="content">No results</div>;
//   }


//   return (
//     <>
//       <Header onSearch={onSearch} />
//       <main className="main" inert={playerState.isMaximized}>
//         {renderContent()}
//       </main>
//       <Player ref={playerRef} />
//     </>
//   )
// }

// export default App

export default function AppLayout() {
  const { state: playerState } = usePlayerContext();
  const playerRef = useRef<PlayerRef>(null);

  return (
    <>
      <Header />
      <main className="main" inert={playerState.isMaximized}>
        <Outlet />
      </main>
      <Player ref={playerRef} />
    </>
  )
}