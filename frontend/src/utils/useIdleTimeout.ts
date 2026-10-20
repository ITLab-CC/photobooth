import { useEffect } from "react";

const ACTIVITY_EVENTS = ["pointerdown", "keydown", "touchstart"] as const;

/**
 * Ruft onIdle auf, wenn für ms Millisekunden keine Eingabe erfolgt ist.
 * Jede Eingabe setzt den Timer zurück. Bei enabled=false läuft kein Timer.
 */
export function useIdleTimeout(enabled: boolean, ms: number, onIdle: () => void): void {
  useEffect(() => {
    if (!enabled) return;

    let timer = setTimeout(onIdle, ms);
    const reset = () => {
      clearTimeout(timer);
      timer = setTimeout(onIdle, ms);
    };

    ACTIVITY_EVENTS.forEach((event) => window.addEventListener(event, reset));
    return () => {
      clearTimeout(timer);
      ACTIVITY_EVENTS.forEach((event) => window.removeEventListener(event, reset));
    };
  }, [enabled, ms, onIdle]);
}
