"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export default function LoadingPage() {
  const router = useRouter();
  const [show, setShow] = useState(true);

  useEffect(() => {
    // Auto-recover: if user lands here without an incident, redirect to main page
    const timer = setTimeout(() => {
      router.replace("/");
    }, 100);
    return () => clearTimeout(timer);
  }, [router]);

  if (!show) return null;

  return (
    <main className="sos-splash flex items-center justify-center">
      <div className="text-center">
        <div className="w-16 h-16 mx-auto mb-4 rounded-full border-4 border-white/20 border-t-sos-red animate-spin" />
        <p className="text-lg font-semibold">Initialising…</p>
        <p className="text-sm text-white/50 mt-2">Connecting to RoadSoS network</p>
      </div>
    </main>
  );
}