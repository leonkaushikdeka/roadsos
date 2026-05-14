"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { roadsosApi } from "@/lib/api";

export default function CompletePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const incidentId = searchParams.get("id");
  const severity = searchParams.get("severity");

  const [details, setDetails] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!incidentId) {
      router.push("/");
      return;
    }

    const load = async () => {
      try {
        const status = await roadsosApi.getIncidentStatus(incidentId);
        setDetails(status);
      } catch {
        // Still show completion screen
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [incidentId, router]);

  const sev = severity || details?.severity || "N/A";
  const sevIcon = sev === "RED" ? "🚨" : sev === "YELLOW" ? "⚠️" : sev === "GREEN" ? "✅" : "📋";
  const sevColor = sev === "RED" ? "text-sos-red" : sev === "YELLOW" ? "text-sos-orange" : "text-sos-green";

  return (
    <main className="min-h-screen bg-sos-dark flex flex-col">
      {/* Top banner */}
      <div className="bg-sos-green/10 border-b border-sos-green/30 px-4 py-8 text-center">
        <div className="text-5xl mb-2">{sevIcon}</div>
        <div className={`text-3xl font-black ${sevColor}`}>
          {sev} — Session Complete
        </div>
        <p className="text-white/50 text-sm mt-2">
          Triage and dispatch are complete.
          {sev === "RED" && " Emergency services are actively responding."}
        </p>
      </div>

      {/* Details */}
      <div className="flex-1 p-4 max-w-lg mx-auto w-full space-y-4">
        {/* Timeline */}
        <div className="glass-card rounded-2xl p-4">
          <h3 className="text-xs font-semibold text-white/50 uppercase mb-3">
            Incident Timeline
          </h3>
          <div className="space-y-3 relative pl-5">
            <div className="absolute left-[7px] top-2 bottom-2 w-[2px] bg-white/10" />
            {details?.triage_transcript?.map((entry: any, i: number) => (
              <div key={i} className="relative flex items-start gap-3">
                <div className="absolute left-[-22px] top-1.5 w-3 h-3 rounded-full border-2 border-sos-red bg-sos-dark" />
                <div>
                  <div className="text-xs text-white/40">
                    {new Date(entry.timestamp).toLocaleTimeString()}
                  </div>
                  <div className="text-sm text-white/70 mt-0.5">
                    {entry.answer || "—"}
                  </div>
                  {entry.severity && (
                    <span
                      className={`inline-block text-[10px] font-bold px-2 py-0.5 rounded-full mt-1
                        ${entry.severity === "RED"
                          ? "bg-sos-red/20 text-sos-red"
                          : entry.severity === "YELLOW"
                          ? "bg-sos-orange/20 text-sos-orange"
                          : "bg-sos-green/20 text-sos-green"
                        }`}
                    >
                      {entry.severity}
                    </span>
                  )}
                </div>
              </div>
            ))}
            <div className="relative">
              <div className="absolute left-[-22px] top-1.5 w-3 h-3 rounded-full border-2 border-sos-green bg-sos-dark" />
              <div className="text-xs text-white/40">Complete</div>
              <div className="text-sm text-white/70">Triage assessment finished</div>
            </div>
          </div>
        </div>

        {/* Service info */}
        {details?.dispatched_services?.length > 0 && (
          <div className="glass-card rounded-2xl p-4">
            <h3 className="text-xs font-semibold text-white/50 uppercase mb-3">
              Dispatched Services
            </h3>
            {details.dispatched_services.map((svc: any, i: number) => (
              <div key={i} className="flex items-center gap-3 py-2">
                <div className="w-8 h-8 rounded-full bg-sos-red/10 flex items-center justify-center text-xs">
                  {svc.type === "ambulance" ? "🚑" : svc.type === "police" ? "🚔" : "🏥"}
                </div>
                <div className="flex-1">
                  <div className="text-sm font-medium">
                    {svc.service_name}
                  </div>
                  <div className="text-xs text-white/40">
                    {svc.type} · {new Date(svc.dispatched_at).toLocaleTimeString()}
                  </div>
                </div>
                <div className="text-xs text-white/60 text-right">
                  {details.ambulance_eta_min && i === 0 ? `~${details.ambulance_eta_min} min ETA` : "Dispatched"}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Incident ID */}
        <div className="glass-card rounded-2xl p-4 text-center">
          <p className="text-[10px] text-white/40 uppercase tracking-wider">
            Incident Reference
          </p>
          <p className="text-xs font-mono font-bold text-white/80 mt-1 select-all">
            {incidentId}
          </p>
          <p className="text-[10px] text-white/30 mt-2">
            Save this for reference when speaking with emergency services
          </p>
        </div>

        {/* Next steps */}
        <div className="glass-card rounded-2xl p-4">
          <h3 className="text-[11px] font-semibold text-white/70 mb-2">
            What happens next
          </h3>
          <ol className="text-xs text-white/50 space-y-3 list-decimal ml-4">
            <li>Emergency responders are en route.</li>
            <li>
              Follow any instructions you were given (bleeding control, CPR, etc.).
            </li>
            <li>
              When responders arrive, share this incident reference:{" "}
              <span className="font-mono text-white/80">{incidentId?.slice(0, 8)}</span>
            </li>
            <li>
              Emergency contacts have been notified (if registered).
            </li>
          </ol>
        </div>
      </div>

      {/* Bottom actions */}
      <div className="p-4 pb-[calc(1rem+env(safe-area-inset-bottom,0px))]">
        <button
          onClick={() => router.push("/")}
          className="w-full btn-sos py-4 rounded-2xl text-sm font-semibold
            shadow-lg shadow-sos-red/30 active:scale-[0.98]"
        >
          ← Back to Home
        </button>
      </div>
    </main>
  );
}