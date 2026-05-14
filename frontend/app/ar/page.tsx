"use client";

import { useEffect, useRef, useState } from "react";
import { roadsosApi } from "@/lib/api";

export default function ARPage() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [activeInstruction, setActiveInstruction] = useState<string | null>(null);
  const [showAR, setShowAR] = useState(false);
  const [tracking, setTracking] = useState(false);

  const instructions = [
    {
      title: "Bleeding Control",
      instruction: "Apply firm pressure with a clean cloth directly on the wound. Keep pressing — do not lift to check.",
      overlay: "pressure-area",
    },
    {
      title: "CPR Compressions",
      instruction: "Place heel of hand on centre of chest. Push hard and fast at 100–120 compressions/min. Depth: at least 5cm.",
      overlay: "chest-compression",
    },
    {
      title: "Recovery Position",
      instruction: "Roll the person onto their side. Tilt head back to keep airway open. Bend top leg for stability.",
      overlay: "recovery-position",
    },
    {
      title: "Spinal Immobilisation",
      instruction: "Do NOT move the person. Hold head and neck still with both hands. Wait for professional help.",
      overlay: "spinal-align",
    },
  ];

  useEffect(() => {
    if (showAR) {
      startCamera();
    }
    return () => {
      stopCamera();
    };
  }, [showAR]);

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
        setTracking(true);
        startOverlayLoop();
      }
    } catch {
      console.log("Camera unavailable — AR overlay rendered without video feed.");
      setTracking(false);
    }
  };

  const stopCamera = () => {
    if (videoRef.current?.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      stream.getTracks().forEach((track) => track.stop());
    }
  };

  const startOverlayLoop = () => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const loop = () => {
      if (!showAR) return;

      canvas.width = video.videoWidth || 400;
      canvas.height = video.videoHeight || 300;

      // Draw video frame
      try {
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      } catch {
        // Video not ready yet
        ctx.fillStyle = "#111";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
      }

      // Semi-transparent overlay
      ctx.fillStyle = "rgba(0, 0, 0, 0.4)";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Draw instructional overlay based on active instruction
      const instr = instructions.find((i) => i.title === activeInstruction);
      if (!instr) {
        // Default: draw crosshair for reference
        ctx.strokeStyle = "#DC2626";
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        ctx.beginPath();
        ctx.moveTo(canvas.width / 2 - 30, canvas.height / 2);
        ctx.lineTo(canvas.width / 2 + 30, canvas.height / 2);
        ctx.moveTo(canvas.width / 2, canvas.height / 2 - 30);
        ctx.lineTo(canvas.width / 2, canvas.height / 2 + 30);
        ctx.stroke();
        ctx.setLineDash([]);

        // "Point camera at victim" label
        ctx.fillStyle = "rgba(255,255,255,0.8)";
        ctx.font = "18px -apple-system, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("📷 Point camera at victim", canvas.width / 2, canvas.height - 40);
      }

      if (instr) {
        const drawInstruction = (ctx: CanvasRenderingContext2D, w: number, h: number, type: string) => {
          ctx.save();
          ctx.translate(w / 2, h / 2);

          // Draw overlay graphic
          ctx.strokeStyle = "#16A34A";
          ctx.lineWidth = 4;
          ctx.shadowColor = "rgba(22,163,74,0.5)";
          ctx.shadowBlur = 20;

          if (type === "pressure-area") {
            // Circle around wound area
            ctx.beginPath();
            ctx.arc(0, 0, 80, 0, Math.PI * 2);
            ctx.stroke();
            // Arrow pointing to centre
            ctx.beginPath();
            ctx.moveTo(-40, 40);
            ctx.lineTo(0, -60);
            ctx.lineTo(40, 40);
            ctx.fillStyle = "rgba(22,163,74,0.3)";
            ctx.fill();
            ctx.font = "bold 22px sans-serif";
            ctx.textAlign = "center";
            ctx.fillStyle = "#16A34A";
            ctx.fillText("PRESS HERE", 0, -80);
          } else if (type === "chest-compression") {
            // Chest compression guide
            ctx.beginPath();
            ctx.ellipse(0, 0, 40, 50, 0, 0, Math.PI * 2);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(-50, -80);
            ctx.lineTo(0, -60);
            ctx.lineTo(50, -80);
            ctx.stroke();
            ctx.font = "bold 18px sans-serif";
            ctx.textAlign = "center";
            ctx.fillStyle = "#16A34A";
            ctx.fillText("COMPRESS HERE", 0, -100);
          } else if (type === "recovery-position") {
            // Figure outline in recovery position
            ctx.beginPath();
            ctx.arc(0, 0, 30, 0, Math.PI * 2);
            ctx.stroke();
            // Arm line
            ctx.beginPath();
            ctx.moveTo(30, 0);
            ctx.lineTo(60, -30);
            ctx.stroke();
            ctx.font = "bold 18px sans-serif";
            ctx.textAlign = "center";
            ctx.fillStyle = "#16A34A";
            ctx.fillText("ROLL TO SIDE", 0, -120);
          } else if (type === "spinal-align") {
            // Spine alignment indicator
            ctx.beginPath();
            ctx.moveTo(-40, -60);
            ctx.lineTo(-40, 60);
            ctx.lineTo(40, 60);
            ctx.lineTo(40, -60);
            ctx.closePath();
            ctx.stroke();
            ctx.font = "bold 18px sans-serif";
            ctx.textAlign = "center";
            ctx.fillStyle = "#EA580C";
            ctx.fillText("DO NOT MOVE", 0, -80);
          }

          ctx.restore();
        };

        drawInstruction(ctx, canvas.width, canvas.height, instr.overlay);
      }

      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  };

  return (
    <main className="min-h-screen bg-black">
      {!showAR ? (
        <div className="flex flex-col items-center justify-center min-h-screen p-6">
          <div className="w-16 h-16 rounded-full bg-sos-red/20 flex items-center justify-center mb-4">
            <svg className="w-8 h-8 text-sos-red" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
            </svg>
          </div>
          <h1 className="text-2xl font-bold mb-2">AR First Aid Assistant</h1>
          <p className="text-white/50 text-sm mb-6 text-center">
            Point your camera at the injured person. RoadSoS will guide you step-by-step with overlay instructions.
          </p>
          <button
            onClick={() => setShowAR(true)}
            className="btn-sos px-8 py-4 rounded-full text-lg shadow-2xl shadow-sos-red/50"
          >
            📷 Start Camera
          </button>
          <p className="text-white/30 text-xs mt-4">Camera runs on-device — no footage is recorded or uploaded</p>
        </div>
      ) : (
        <>
          <div className="relative">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="w-full max-w-lg mx-auto bg-black"
              style={{ transform: "scaleX(-1)" }}
            />
            <canvas
              ref={canvasRef}
              className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-lg"
              style={{ transform: "scaleX(-1)" }}
            />
          </div>

          <div className="p-4 max-w-lg mx-auto w-full">
            <div className="glass-card rounded-2xl p-4">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-semibold text-sos-red">First Aid Guide</span>
                <button
                  onClick={() => setShowAR(false)}
                  className="text-xs px-3 py-1 rounded-full bg-white/10 text-white/70"
                >
                  Close
                </button>
              </div>
              <div className="space-y-2">
                {instructions.map((instr) => (
                  <button
                    key={instr.title}
                    onClick={() => setActiveInstruction(
                      activeInstruction === instr.title ? null : instr.title
                    )}
                    className={`w-full flex items-center justify-between p-3 rounded-xl transition-colors ${
                      activeInstruction === instr.title
                        ? "bg-sos-red/20 border border-sos-red"
                        : "bg-white/5 border border-transparent"
                    }`}
                  >
                    <div className="text-left">
                      <div className={`text-sm font-semibold ${
                        activeInstruction === instr.title ? "text-white" : "text-white/70"
                      }`}>{instr.title}</div>
                      {activeInstruction === instr.title && (
                        <div className="text-xs text-white/50 mt-1">{instr.instruction}</div>
                      )}
                    </div>
                    <span className="text-lg">
                      {activeInstruction === instr.title ? "📌" : "▶️"}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </main>
  );
}