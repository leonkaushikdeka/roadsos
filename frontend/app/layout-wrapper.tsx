"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isHome = pathname === "/";
  const [isOnline, setIsOnline] = useState(true);
  const [protocols, setProtocols] = useState<any[]>([]);
  const [showOffline, setShowOffline] = useState(false);

  // Online/offline detection
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      setShowOffline(false);
    };
    const handleOffline = () => {
      setIsOnline(false);
      // Try to load cached protocols
      loadCachedProtocols();
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    if (!navigator.onLine) {
      setIsOnline(false);
      loadCachedProtocols();
    }

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  // Listen for SW protocol update messages
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.addEventListener("message", (event) => {
        if (event.data?.type === "PROTOCOL_UPDATED") {
          loadCachedProtocols();
        }
      });
    }
  }, []);

  const loadCachedProtocols = useCallback(async () => {
    try {
      if ("caches" in window) {
        // Try to get from SW cache via a fetch with cache-only mode
        const cache = await caches.open("roadsos-protocols-v2");
        const resp = await cache.match("/v1/protocols/offline-bundle?lang=en");
        if (resp) {
          const data = await resp.json();
          setProtocols(data.protocols || []);
          setShowOffline(true);
        }
      }
    } catch {
      setProtocols([]);
      setShowOffline(true);
    }
  }, []);

  return (
    <div className="min-h-screen bg-sos-dark">
      {/* Offline banner */}
      {!isOnline && (
        <div className="offline-banner">
          ⚠️ You are offline. Displaying cached first-aid protocols.
        </div>
      )}

      {/* Offline full-screen fallback for critical pages */}
      {showOffline && !isOnline && (
        <div className="offline-fallback">
          <div className="offline-icon">🆘</div>
          <h1 className="text-2xl font-bold text-white mb-2">Offline Mode</h1>
          <p className="text-white/60 mb-4">
            No internet connection. Emergency contacts may not be reachable.
          </p>
          {protocols.length > 0 && (
            <>
              <h2 className="text-sm font-semibold text-sos-red mb-2">
                Cached First-Aid Protocols
              </h2>
              <div className="offline-protocol-list">
                {protocols.map((p: any) => (
                  <div key={p.id} className="offline-protocol-item">
                    <strong>{p.type.replace(/_/g, " ").toUpperCase()}</strong>
                    <br />
                    <span className="text-white/70 text-xs">
                      ({p.source})
                    </span>
                    <p className="mt-1 text-sm">{p.text}</p>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {/* Header */}
      {!isHome && (
        <header className="sticky top-0 z-50 bg-sos-dark/95 backdrop-blur-md border-b border-white/10">
          <div className="flex items-center justify-between px-4 py-3 max-w-lg mx-auto">
            <Link href="/" className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-sos-red/20 flex items-center justify-center">
                <svg viewBox="0 0 24 24" className="w-4 h-4 text-sos-red" fill="currentColor">
                  <path d="M12 2L2 7v5c0 5.5 4.78 10 10 10s10-4.5 10-10V7l-10-5z"/>
                </svg>
              </div>
              <span className="text-sm font-bold">RoadSoS</span>
            </Link>
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${isOnline ? "bg-green-400" : "bg-red-500"}`} />
              <span className="text-[10px] text-white/40 uppercase tracking-wider">
                {isOnline ? "Online" : "Offline"}
              </span>
            </div>
          </div>
        </header>
      )}

      <main>{children}</main>

      {/* Bottom safety banner */}
      {isHome && (
        <footer className="text-center py-3 border-t border-white/5">
          <p className="text-[10px] text-white/30">
            🆘 In a real emergency? Call <span className="text-sos-red font-bold">108</span> immediately.
          </p>
        </footer>
      )}
    </div>
  );
}