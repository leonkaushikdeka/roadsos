"use client";

import { useState, useEffect } from "react";
import { roadsosApi } from "@/lib/api";

export default function AdminDashboard() {
  const [stats, setStats] = useState<any>(null);
  const [heatmap, setHeatmap] = useState<any[]>([]);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, [days]);

  async function loadData() {
    setLoading(true);
    try {
      const [s, h] = await Promise.all([
        roadsosApi.getStats(days),
        roadsosApi.getHeatmap(days),
      ]);
      setStats(s);
      setHeatmap(h.incidents);
    } catch {
      setStats(null);
      setHeatmap([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-sos-dark p-4 pb-[calc(1rem+env(safe-area-inset-bottom,0px))] flex flex-col">
      <div className="flex items-center justify-between mb-6 max-w-md mx-auto w-full">
        <div>
          <h1 className="text-xl font-bold">Admin Dashboard</h1>
          <p className="text-xs text-white/40">Incident analytics & heatmap</p>
        </div>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="bg-white/10 border border-white/10 rounded-full px-3 py-1.5 text-xs text-white/70 outline-none focus:ring-2 focus:ring-sos-red/50"
        >
          {[7, 30, 90].map((d) => (
            <option key={d} value={d}>{d} days</option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="flex items-center justify-center flex-1">
          <div className="text-center">
            <div className="w-8 h-8 mx-auto rounded-full border-2 border-white/20 border-t-sos-red animate-spin" />
            <p className="text-sm text-white/40 mt-3">Loading analytics…</p>
          </div>
        </div>
      ) : stats ? (
        <div className="flex flex-col gap-4 max-w-md mx-auto w-full">
          {/* Summary cards */}
          <div className="grid grid-cols-2 gap-3">
            <div className="glass-card rounded-xl p-4 text-center">
              <div className="text-2xl font-black">{stats.total_incidents}</div>
              <div className="text-[10px] text-white/40 uppercase mt-1">Total Incidents</div>
            </div>
            <div className="glass-card rounded-xl p-4 text-center">
              <div className="text-2xl font-black text-sos-green">{stats.avg_eta_min}m</div>
              <div className="text-[10px] text-white/40 uppercase mt-1">Avg ETA</div>
            </div>
            <div className="glass-card rounded-xl p-4 text-center">
              <div className="text-2xl font-black text-sos-red">{stats.red_count}</div>
              <div className="text-[10px] text-white/40 uppercase mt-1">Critical</div>
            </div>
            <div className="glass-card rounded-xl p-4 text-center">
              <div className="text-2xl font-black text-sos-orange">{stats.yellow_count}</div>
              <div className="text-[10px] text-white/40 uppercase mt-1">Moderate</div>
            </div>
          </div>

          {/* Bar chart — severity distribution */}
          <div className="glass-card rounded-xl p-4">
            <h3 className="text-xs font-semibold text-white/50 uppercase mb-3">
              Severity Distribution
            </h3>
            <div className="space-y-2">
              {["RED", "YELLOW", "GREEN"].map((sev) => (
                <div key={sev} className="flex items-center gap-3">
                  <span className="text-[10px] w-12 text-white/60">{sev}</span>
                  <div className="flex-1 h-4 bg-white/5 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-700"
                      style={{
                        width: `${Math.max(1, (
                          (stats[`${sev.toLowerCase()}_count"] || 0) /
                          (stats.total_incidents || 1)
                        ) * 100)}%`,
                        background: sev === "RED"
                          ? "#DC2626"
                          : sev === "YELLOW"
                          ? "#F59E0B"
                          : "#16A34A",
                      }}
                    />
                  </div>
                  <span className="text-[10px] w-8 text-right text-white/60">
                    {stats[`${sev.toLowerCase()}_count`] || 0}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Heatmap */}
          <div className="glass-card rounded-xl p-4">
            <h3 className="text-xs font-semibold text-white/50 uppercase mb-3">
              Incident Heatmap ({heatmap.length} points)
            </h3>
            {heatmap.length > 0 ? (
              <div className="relative w-full h-48 rounded-lg overflow-hidden">
                <canvas
                  ref={(el) => {
                    if (!el || !heatmap.length) return;
                    const ctx = el.getContext("2d");
                    if (!ctx) return;
                    const dpr = window.devicePixelRatio || 1;
                    el.width = el.clientWidth * dpr;
                    el.height = el.clientHeight * dpr;
                    ctx.scale(dpr, dpr);

                    // Normalize coordinates
                    const lngs = heatmap.map((p: any) => p.lng);
                    const lats = heatmap.map((p: any) => p.lat);
                    const minLng = Math.min(...lngs);
                    const maxLng = Math.max(...lngs);
                    const minLat = Math.min(...lats);
                    const maxLat = Math.max(...lats);
                    const w = el.clientWidth;
                    const h = el.clientHeight;

                    // Draw heat dots
                    heatmap.forEach((p: any) => {
                      const x = minLng === maxLng ? w / 2 : ((p.lng - minLng) / (maxLng - minLng)) * w;
                      const y = minLat === maxLat ? h / 2 : h - ((p.lat - minLat) / (maxLat - minLat)) * h;
                      const intensity = p.severity === "RED" ? 1 : p.severity === "YELLOW" ? 0.5 : 0.2;

                      const grad = ctx.createRadialGradient(x, y, 0, x, y, 20);
                      grad.addColorStop(0, `rgba(220, 38, 38, ${0.6 * intensity})`);
                      grad.addColorStop(1, `rgba(220, 38, 38, 0)`);
                      ctx.fillStyle = grad;
                      ctx.beginPath();
                      ctx.arc(x, y, 20, 0, Math.PI * 2);
                      ctx.fill();
                    });
                  }}
                  className="w-full h-full"
                />
              </div>
            ) : (
              <p className="text-xs text-white/40 text-center py-8">
                No incidents in this period
              </p>
            )}
          </div>

          {/* Recent incidents */}
          <div className="glass-card rounded-xl p-4">
            <h3 className="text-xs font-semibold text-white/50 uppercase mb-3">
              Recent Incidents
            </h3>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {heatmap.slice(0, 5).map((p: any, i: number) => (
                <div key={i} className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <div
                      className={`w-2 h-2 rounded-full ${
                        p.severity === "RED"
                          ? "bg-sos-red"
                          : p.severity === "YELLOW"
                          ? "bg-sos-orange"
                          : "bg-sos-green"
                      }`}
                    />
                    <span className="text-white/70">
                      {new Date(p.date).toLocaleDateString()}
                    </span>
                  </div>
                  <span className="text-white/40">{p.severity}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className="text-center py-12">
          <p className="text-white/40 text-sm">
            Could not load analytics. Check your backend connection.
          </p>
          <button
            onClick={loadData}
            className="mt-4 px-4 py-2 rounded-full bg-white/10 text-xs hover:bg-white/20 transition-colors"
          >
            Retry
          </button>
        </div>
      )}
    </main>
  );
}