"use client";

import { useState } from "react";

const SLIDES = [
  {
    id: 1,
    title: "RoadSoS",
    subtitle: "The AI Companion that turns every bystander into a first responder",
    content: (
      <div className="flex flex-col items-center gap-6">
        <div className="w-24 h-24 rounded-full bg-sos-red flex items-center justify-center">
          <span className="text-3xl font-black text-white">SOS</span>
        </div>
        <p className="text-white/60 text-center max-w-md">
          Saving lives in the Golden Hour through AI-driven triage, location-aware dispatch, and voice-first accessibility
        </p>
        <div className="flex gap-4 text-xs text-white/40">
          <span>CoERS, IIT Madras</span>
          <span>Road Safety Hackathon 2026</span>
        </div>
      </div>
    ),
  },
  {
    id: 2,
    title: "The Problem",
    subtitle: "Most aren't killed by the crash. They're killed by the wait.",
    content: (
      <div className="space-y-4 w-full max-w-lg">
        <div className="text-5xl font-black text-center text-sos-red">1.19M</div>
        <p className="text-center text-white/60 text-sm">Annual road fatalities globally — half within 60 minutes</p>
        <div className="glass-card rounded-xl p-4">
          <table className="w-full text-xs">
            <thead><tr className="text-white/40"><th className="text-left pb-2">Metric</th><th className="pb-2">Global</th><th className="pb-2">BIMSTEC</th></tr></thead>
            <tbody className="text-white/70">
              <tr><td className="py-1">Ambulance response (urban)</td><td>8-12 min</td><td className="text-sos-red">20-35 min</td></tr>
              <tr><td className="py-1">Ambulance response (rural)</td><td>15-25 min</td><td className="text-sos-red">45-90+ min</td></tr>
              <tr><td className="py-1">Bystander first-aid rate</td><td>15-25%</td><td className="text-sos-red">&lt;5%</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    ),
  },
  {
    id: 3,
    title: "Our Solution",
    subtitle: "Multi-modal AI emergency companion",
    content: (
      <div className="space-y-4 w-full max-w-lg">
        <div className="grid grid-cols-3 gap-3">
          {[
            { icon: "⚡", label: "Speed", desc: "One tap, zero friction" },
            { icon: "🗣️", label: "Vernacular", desc: "8+ BIMSTEC languages" },
            { icon: "🔋", label: "Resilient", desc: "Offline + SMS fallback" },
          ].map(p => (
            <div key={p.label} className="glass-card rounded-xl p-3 text-center">
              <div className="text-2xl mb-1">{p.icon}</div>
              <div className="font-semibold text-sm">{p.label}</div>
              <div className="text-xs text-white/50">{p.desc}</div>
            </div>
          ))}
        </div>
        <div className="glass-card rounded-xl p-4 flex items-center justify-around text-xs">
          <span>📱 PWA</span><span>💬 WhatsApp</span><span>📞 IVR</span><span>✉️ SMS</span><span>📷 AR</span>
        </div>
      </div>
    ),
  },
  {
    id: 4,
    title: "How It Works",
    subtitle: "End-to-end incident flow",
    content: (
      <div className="space-y-3 w-full max-w-lg">
        {[
          { time: "0:00", text: "Bystander taps SOS or says 'Help' on WhatsApp", icon: "🆘" },
          { time: "0:05", text: "AI confirms GPS, asks triage questions in user's language", icon: "🤖" },
          { time: "0:20", text: "Severity assessed → ALS ambulance dispatched", icon: "🚑" },
          { time: "0:35", text: "Voice + AR guides bystander through first aid", icon: "📋" },
          { time: "1:10", text: "Scene photos uploaded, police + ICE notified", icon: "📸" },
          { time: "11:20", text: "Ambulance arrives, ER prepped with triage notes", icon: "🏥" },
        ].map(s => (
          <div key={s.time} className="flex items-center gap-3 glass-card rounded-lg p-2.5 text-sm">
            <span className="text-lg">{s.icon}</span>
            <span className="font-mono text-xs text-sos-orange w-12">{s.time}</span>
            <span className="text-white/80 flex-1">{s.text}</span>
          </div>
        ))}
      </div>
    ),
  },
  {
    id: 5,
    title: "Tech & AI Depth",
    subtitle: "Safety-first architecture with RAG-grounded LLM",
    content: (
      <div className="space-y-4 w-full max-w-lg">
        <div className="glass-card rounded-xl p-4">
          <div className="text-xs font-mono text-white/40 space-y-1">
            <div className="text-white/70 font-semibold mb-2">Architecture Layers</div>
            <div className="bg-sos-red/20 p-1.5 rounded">📱 Presentation: PWA · WhatsApp · IVR · SMS · AR</div>
            <div className="bg-purple-900/30 p-1.5 rounded">🧠 AI: LLM Triage · ASR/TTS · Translation · RAG</div>
            <div className="bg-blue-900/30 p-1.5 rounded">⚙️ Services: Dispatch · Geocoder · Notifications</div>
            <div className="bg-green-900/30 p-1.5 rounded">🗄️ Data: PostgreSQL+PostGIS · Redis · pgvector</div>
          </div>
        </div>
        <div className="glass-card rounded-xl p-3 text-xs text-white/60">
          <span className="font-semibold text-white/80">Why RAG, not free generation:</span> Medical hallucination is unacceptable. All instructions retrieved from vetted WHO + Red Cross protocols.
        </div>
      </div>
    ),
  },
  {
    id: 6,
    title: "Impact & Roadmap",
    subtitle: "From hackathon to cross-BIMSTEC deployment",
    content: (
      <div className="space-y-4 w-full max-w-lg">
        <div className="text-center">
          <div className="text-3xl font-black text-sos-green">22-34%</div>
          <p className="text-sm text-white/60">Projected mortality reduction in highway accidents</p>
        </div>
        <div className="space-y-2">
          {[
            { phase: "Stage 1", date: "Jun 2026", desc: "PWA MVP, WhatsApp bot, TN seed DB" },
            { phase: "Pilot A", date: "Q3 2026", desc: "2 highway corridors (NH-44, NH-66)" },
            { phase: "Pilot B", date: "Q4 2026", desc: "6 Indian states + Sri Lanka, Bhutan" },
            { phase: "Scale", date: "2027", desc: "Cross-BIMSTEC rollout, national 112 integration" },
          ].map(p => (
            <div key={p.phase} className="flex items-center gap-3 glass-card rounded-lg p-2.5 text-sm">
              <div className="w-16 text-xs font-bold text-sos-orange">{p.phase}</div>
              <div className="w-20 text-xs text-white/40 font-mono">{p.date}</div>
              <div className="text-white/70 text-xs flex-1">{p.desc}</div>
            </div>
          ))}
        </div>
      </div>
    ),
  },
  {
    id: 7,
    title: "Thank You",
    subtitle: "Every minute matters. Let's give every road user a fighting chance.",
    content: (
      <div className="flex flex-col items-center gap-4 text-center">
        <div className="w-16 h-16 rounded-full bg-sos-red/20 flex items-center justify-center">
          <svg className="w-8 h-8 text-sos-red animate-pulse" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2L2 7v5c0 5.5 4.78 10 10 10s10-4.5 10-10V7l-10-5z"/>
          </svg>
        </div>
        <div className="glass-card rounded-xl p-4 text-xs text-white/60">
          <p>Team RoadSoS · CoERS IIT Madras · RBG Labs</p>
          <p className="mt-1">Road Safety Hackathon 2026</p>
        </div>
        <div className="flex gap-4 text-xs">
          <span className="text-white/40">🔗 GitHub</span>
          <span className="text-white/40">📱 Live Demo</span>
          <span className="text-white/40">💬 WhatsApp</span>
        </div>
      </div>
    ),
  },
];

export default function Presentation() {
  const [current, setCurrent] = useState(0);
  const slide = SLIDES[current];

  return (
    <main className="min-h-screen bg-sos-dark flex flex-col">
      <div className="flex-1 flex flex-col items-center justify-center p-6 max-w-2xl mx-auto w-full">
        <div className="text-center mb-6">
          <h1 className="text-2xl font-bold">{slide.title}</h1>
          <p className="text-sm text-white/50 mt-1">{slide.subtitle}</p>
        </div>
        <div className="flex-1 flex items-center justify-center w-full">
          {slide.content}
        </div>
      </div>

      <div className="p-4 flex items-center justify-between max-w-md mx-auto w-full">
        <button
          onClick={() => setCurrent(Math.max(0, current - 1))}
          disabled={current === 0}
          className="px-4 py-2 rounded-full glass-card text-sm disabled:opacity-30"
        >
          ← Back
        </button>
        <span className="text-xs text-white/40">{current + 1} / {SLIDES.length}</span>
        <button
          onClick={() => setCurrent(Math.min(SLIDES.length - 1, current + 1))}
          disabled={current === SLIDES.length - 1}
          className="px-4 py-2 rounded-full btn-sos text-sm disabled:opacity-30"
        >
          Next →
        </button>
      </div>
    </main>
  );
}
