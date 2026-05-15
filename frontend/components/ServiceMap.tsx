"use client";

import { useEffect, useRef } from "react";

interface Props {
  location: { lat: number; lng: number };
  services?: {
    hospitals?: any[];
    ambulances?: any[];
    police?: any[];
  };
  height?: string;
}

const COLORS = {
  hospital: "#DC2626",
  ambulance: "#F59E0B",
  police: "#3B82F6",
  user: "#16A34A",
};

/** Simplified equirectangular projection for local area display */
function projectPoint(
  lat: number,
  lng: number,
  centerLat: number,
  centerLng: number,
  width: number,
  height: number,
  scale: number,
): { x: number; y: number } {
  const x = (lng - centerLng) * scale * Math.cos((centerLat * Math.PI) / 180) + width / 2;
  const y = -(lat - centerLat) * scale + height / 2;
  return { x, y };
}

export default function ServiceMap({ location, services, height = "300px" }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = rect.height;

    // Find max distance for scaling
    const allServices = [
      ...(services?.ambulances || []).map((s: any) => ({
        ...s,
        color: COLORS.ambulance,
        label: "A",
      })),
      ...(services?.police || []).map((s: any) => ({
        ...s,
        color: COLORS.police,
        label: "P",
      })),
      ...(services?.hospitals || []).map((s: any) => ({
        ...s,
        color: COLORS.hospital,
        label: "H",
      })),
    ];

    const maxDist = Math.max(
      ...allServices.map((s: any) => s.distance_km || 5),
      5,
    );
    // Scale: pixels per km (10-30 km fits nicely)
    const scalePpk = Math.min(w, h) * 0.4 / Math.max(maxDist, 1);

    ctx.clearRect(0, 0, w, h);

    // Grid background
    ctx.fillStyle = "rgba(15, 23, 42, 0.6)";
    ctx.fillRect(0, 0, w, h);

    const gridSize = 30;
    ctx.strokeStyle = "rgba(255,255,255,0.03)";
    ctx.lineWidth = 1;
    for (let x = 0; x < w; x += gridSize) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();
    }
    for (let y = 0; y < h; y += gridSize) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }

    // Draw range rings
    for (let km = 5; km <= Math.ceil(maxDist / 5) * 5; km += 5) {
      const r = km * scalePpk;
      ctx.beginPath();
      ctx.arc(w / 2, h / 2, r, 0, Math.PI * 2);
      ctx.strokeStyle = "rgba(255,255,255,0.05)";
      ctx.lineWidth = 1;
      ctx.stroke();

      ctx.fillStyle = "rgba(255,255,255,0.1)";
      ctx.font = "8px sans-serif";
      ctx.textAlign = "left";
      ctx.fillText(`${km}km`, w / 2 + r + 3, h / 2 - 2);
    }

    // Draw services
    allServices.forEach((svc: any) => {
      const svcLat = svc.lat ?? svc.location?.lat ?? 0;
      const svcLng = svc.lng ?? svc.location?.lng ?? 0;
      const proj = projectPoint(
        svcLat,
        svcLng,
        location.lat,
        location.lng,
        w,
        h,
        scalePpk,
      );

      // Clamp to canvas
      const cx = Math.max(16, Math.min(w - 16, proj.x));
      const cy = Math.max(16, Math.min(h - 16, proj.y));

      // Glow
      ctx.beginPath();
      ctx.arc(cx, cy, 14, 0, Math.PI * 2);
      ctx.fillStyle = `${svc.color}33`;
      ctx.fill();

      // Dot
      ctx.beginPath();
      ctx.arc(cx, cy, 7, 0, Math.PI * 2);
      ctx.fillStyle = svc.color;
      ctx.fill();

      // Label
      ctx.fillStyle = "white";
      ctx.font = "bold 7px sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(svc.label, cx, cy);

      // Name below
      ctx.fillStyle = "rgba(255,255,255,0.5)";
      ctx.font = "7px sans-serif";
      ctx.fillText(
        svc.name?.substring(0, 14) || "",
        cx,
        cy + 14,
      );
    });

    // User marker (center)
    ctx.beginPath();
    ctx.arc(w / 2, h / 2, 12, 0, Math.PI * 2);
    ctx.fillStyle = COLORS.user;
    ctx.fill();
    ctx.strokeStyle = "#fff";
    ctx.lineWidth = 2;
    ctx.stroke();

    ctx.fillStyle = "white";
    ctx.font = "bold 7px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("YOU", w / 2, h / 2);

    // Pulse ring
    ctx.beginPath();
    ctx.arc(w / 2, h / 2, 20, 0, Math.PI * 2);
    ctx.strokeStyle = "rgba(22, 163, 74, 0.3)";
    ctx.lineWidth = 1.5;
    ctx.setLineDash([3, 3]);
    ctx.stroke();
    ctx.setLineDash([]);

    // Legend
    ctx.font = "9px sans-serif";
    const legendY = 10;
    const items = [
      { color: COLORS.hospital, label: "Hospital" },
      { color: COLORS.ambulance, label: "Ambulance" },
      { color: COLORS.police, label: "Police" },
    ];
    items.forEach((item, i) => {
      const lx = 5 + i * 80;
      ctx.fillStyle = item.color;
      ctx.fillRect(lx, legendY, 8, 8);
      ctx.fillStyle = "rgba(255,255,255,0.5)";
      ctx.textAlign = "left";
      ctx.fillText(item.label, lx + 12, legendY + 8);
    });
  }, [location, services]);

  return (
    <canvas
      ref={canvasRef}
      style={{ width: "100%", height, borderRadius: "1rem" }}
      className="bg-sos-dark/80"
    />
  );
}