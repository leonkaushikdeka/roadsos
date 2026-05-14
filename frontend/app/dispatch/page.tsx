"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { roadsosApi } from "@/lib/api";
import ServiceMap from "@/components/ServiceMap";

export default function DispatchPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const incidentId = searchParams.get("id");

  const [severity, setSeverity] = useState<string | null>(null);
  const [dispatchData, setDispatchData] = useState<any>(null);
  const [location, setLocation] = useState<{ lat: number; lng: number } | null>(null);
  const [eta, setEta] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!incidentId) {
      router.push("/");
      return;
    }

    const loadDispatches = async () => {
      try {
        const status = await roadsosApi.getIncidentStatus(incidentId);
        setSeverity(status.severity);
        setLocation(null); // We'll get from services

        if (status.dispatch_options) {
          setDispatchData(status.dispatch_options);
        }

        if (status.ambulance_eta_min) {
          setEta(status.ambulance_eta_min);
        }

        // If dispatch not complete, trigger dispatch
        if (!status.dispatched_services?.length) {
          await roadsosApi.confirmDispatch(
            incidentId,
            status.dispatch_options?.ambulances?.[0]?.id || ""
          );
          // Re-fetch
          const updated = await roadsosApi.getIncidentStatus(incidentId);
          setDispatchData(updated.dispatch_options || null);
          setEta(updated.ambulance_eta_min || null);
        }
      } catch (err: any) {
        setError("Could not load dispatch status");
      } finally {
        setLoading(false);
      }
    };

    loadDispatches();
  }, [incidentId, router]);

  if (loading) {
    return (
      <main className="sos-splash flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full border-4 border-white/20 border-t-sos-red animate-spin" />
          <p className="text-lg font-semibold">Dispatching help…</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-sos-dark p-4 flex flex-col">
      <div className="text-center py-6">
        <div className={`text-4xl font-black mb-2 severity-${severity || "RED"}`}>
          {severity || "EMERGENCY"}
        </div>
        <p className="text-white/50 text-sm">Severity Assessment</p>
      </div>

      <div className="glass-card rounded-2xl p-6 mb-4 text-center">
        <div className="w-16 h-16 mx-auto mb-3 rounded-full bg-sos-red/20 flex items-center justify-center">
          <svg
            className="w-8 h-8 text-sos-red animate-pulse"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 10V3L4 14h7v7l9-11h-7z"
            />
          </svg>
        </div>
        <h2 className="text-xl font-bold mb-1">
          {dispatchData?.ambulances?.[0]?.name
            ? "Ambulance Dispatched"
            : "Help En Route"}
        </h2>
        {eta && (
          <p className="text-3xl font-black text-sos-red">~{eta} min ETA</p>
        )}
        <p className="text-white/50 text-sm mt-2">Help is on the way. Stay where you are.</p>
      </div>

      {location && dispatchData && (
        <div className="flex-1 min-h-[200px] rounded-2xl overflow-hidden">
          <ServiceMap location={location} services={dispatchData} />
        </div>
      )}

      {!location && (
        <div className="flex-1 flex items-center justify-center">
          <p className="text-sm text-white/40">Map loading in 3…</p>
        </div>
      )}

      <div className="mt-4 space-y-2">
        <h3 className="text-xs font-semibold text-white/50 uppercase">Dispatched Services</h3>
        <div className="glass-card rounded-2xl p-4 space-y-3">
          {dispatchData?.ambulances?.slice(0, 3).map((a: any) => (
            <div key={a.id} className="flex justify-between items-center">
              <span className="text-sm">
                <span className="text-xs text-sos-orange mr-2">🚑</span>
                {a.name}
              </span>
              <span className="text-xs text-white/60">
                {a.distance_km} km · {a.eta_min} min
              </span>
            </div>
          ))}
          {dispatchData?.hospitals?.slice(0, 3).map((h: any) => (
            <div key={h.id} className="flex justify-between items-center">
              <span className="text-sm">
                <span className="text-xs text-sos-red mr-2">🏥</span>
                {h.name}
              </span>
              <span className="text-xs text-white/60">
                {h.distance_km} km · Grade {h.trauma_grade}
              </span>
            </div>
          ))}
          {dispatchData?.police?.slice(0, 2).map((p: any) => (
            <div key={p.id} className="flex justify-between items-center">
              <span className="text-sm">
                <span className="text-xs text-sos-blue mr-2">🚔</span>
                {p.name}
              </span>
              <span className="text-xs text-white/60">
                {p.distance_km} km · {p.eta_min} min
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-4 flex gap-3">
        <button
          onClick={() => router.push(`/complete?id=${incidentId}`)}
          className="flex-1 btn-sos py-3 rounded-full text-sm"
        >
          Confirm ✅
        </button>
        <button
          onClick={() => router.push("/")}
          className="flex-1 py-3 rounded-full glass-card text-sm"
        >
          Cancel
        </button>
      </div>
    </main>
  );
}