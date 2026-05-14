"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { roadsosApi } from "@/lib/api";
import { getCurrentPosition } from "@/lib/geolocation";

export default function Home() {
  const router = useRouter();
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [incidentId, setIncidentId] = useState<string | null>(null);

  const handleSOS = useCallback(async () => {
    setProcessing(true);
    setError(null);

    try {
      const pos = await getCurrentPosition();
      const { latitude: lat, longitude: lng } = pos.coords;

      const resp = await roadsosApi.initiateIncident({
        lat,
        lng,
        location_accuracy_m: pos.coords.accuracy,
        channel: "pwa",
        language: navigator.language.startsWith("hi") ? "hi" : "en",
      });

      if (!resp.incident_id) {
        throw new Error("Server did not return an incident ID");
      }

      setIncidentId(resp.incident_id);
      // Navigate to triage chat
      router.push(`/incident/${resp.incident_id}`);
    } catch (err: any) {
      setError(err.message || "Could not get location. Please enable GPS.");
      setTimeout(() => setError(null), 5000);
      setProcessing(false);
    }
  }, [router]);

  // Auto-start SOS if URL has ?sos=1 (e.g., from home screen shortcut)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("sos") === "1" && !processing) {
      handleSOS();
    }
  }, []);

  // Don't render until we know we're not auto-starting
  if (processing) {
    return (
      <main className="sos-splash flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full border-4 border-white/20 border-t-sos-red animate-spin" />
          <p className="text-lg font-semibold">Preparing emergency…</p>
          <p className="text-sm text-white/50 mt-1">Getting your location</p>
        </div>
      </main>
    );
  }

  if (incidentId) {
    // Already navigating — show nothing, router will handle
    return null;
  }

  return (
    <main className="sos-splash flex flex-col items-center justify-between p-6 relative" role="main">
      <div className="flex-1 flex flex-col items-center justify-center w-full max-w-md mx-auto gap-8">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-3 rounded-full bg-white/10 flex items-center justify-center">
            <svg viewBox="0 0 24 24" className="w-8 h-8 text-sos-red" fill="currentColor">
              <path d="M12 2L2 7v5c0 5.5 4.78 10 10 10s10-4.5 10-10V7l-10-5z"/>
            </svg>
          </div>
          <h1 className="text-2xl font-bold tracking-tight">RoadSoS</h1>
          <p className="text-sm text-white/60 mt-1">AI Emergency Response Companion</p>
        </div>

        {error && (
          <div className="glass-card rounded-xl px-4 py-3 text-sm text-sos-orange w-full text-center" role="alert">
            {error}
          </div>
        )}

        <div className="relative">
          <div className="absolute inset-0 pulse-ring rounded-full" aria-hidden="true" />
          <button
            onClick={handleSOS}
            className="btn-sos w-40 h-40 rounded-full text-3xl tracking-widest shadow-2xl
              shadow-sos-red/50 relative z-10 flex flex-col items-center justify-center gap-1
              focus:outline-none focus:ring-4 focus:ring-sos-red/50"
            aria-label="Emergency SOS — tap for help"
          >
            <span className="text-4xl leading-none" aria-hidden="true">SOS</span>
            <span className="text-xs font-normal opacity-80">Tap for Help</span>
          </button>
        </div>

        <p className="text-xs text-white/40 text-center max-w-xs leading-relaxed">
          Your GPS will be used to find the nearest hospital and ambulance. Tap SOS to start.
        </p>
      </div>

      <footer className="text-xs text-white/30 pb-4 text-center">
        v1.0 · RoadSoS · CoERS IIT Madras · RBG Labs
      </footer>
    </main>
  );
}