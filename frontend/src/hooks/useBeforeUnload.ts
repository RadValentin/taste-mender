import { useEffect } from "react";

/** Warns users of unsaved state before they leave the page. */
export default function useBeforeUnload(enabled: boolean) {
  useEffect(() => {
    if (!enabled) {
      return;
    }

    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "true"; // Nonempty string for legacy support
    };


    window.addEventListener("beforeunload", handleBeforeUnload);

    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, [enabled]);
}