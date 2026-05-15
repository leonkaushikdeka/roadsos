"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { roadsosApi } from "@/lib/api";
import { getCurrentPosition, getGeolocationPermissionState } from "@/lib/geolocation";

export default function Home() {
  const router = useRouter();
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [locationBlocked, setLocationBlocked] = useState(false);
  const [incidentId, setIncidentId] = useState<string | null>(null);

  const handleSOS = useCallback(async () => {
    setProcessing(true);
    setError(null);
    setLocationBlocked(false);

    // Check permission state before attempting — gives immediate feedback
    const permState = await getGeolocationPermissionState();
    if (permState === "denied") {
      setLocationBlocked(true);
      setProcessing(false);
      return;
    }

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
      router.push(`/incident?id=${resp.incident_id}`);
    } catch (err: any) {
      // PERMISSION_DENIED code = 1
      if (err?.code === 1) {
        setLocationBlocked(true);
      } else {
        setError(err.message || "Could not get location. Please enable GPS.");
        setTimeout(() => setError(null), 5000);
      }
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

        {locationBlocked && (
          <div className="glass-card rounded-xl px-4 py-4 text-sm w-full" role="alert" aria-live="assertive">
            <p className="font-semibold text-sos-red mb-2">Location access is blocked</p>
            <p className="text-white/70 mb-3 text-xs leading-relaxed">
              RoadSoS needs your GPS to dispatch help. Your browser is blocking location access.
            </p>
            <ol className="text-white/60 text-xs space-y-1 list-decimal list-inside mb-3">
              <li>Tap the lock / info icon in your browser's address bar</li>
              <li>Find <strong className="text-white/80">Location</strong> and set it to <strong className="text-white/80">Allow</strong></li>
              <li>Reload the page, then tap SOS again</li>
            </ol>
            <button
              onClick={() => { setLocationBlocked(false); window.location.reload(); }}
              className="w-full py-2 rounded-lg bg-sos-red/20 text-sos-red text-xs font-semibold"
            >
              Reload &amp; Try Again
            </button>
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