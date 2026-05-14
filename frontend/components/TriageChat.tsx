"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { roadsosApi } from "@/lib/api";

interface Props {
  incidentId: string;
  language: string;
  onComplete: (result: any) => void;
  onError?: (err: string) => void;
}

interface Message {
  text: string;
  sender: "bot" | "user";
  instruction?: string;
  severity?: string;
}

const QUICK_REPLIES = {
  default: ["Yes", "No", "Unconscious", "Not sure"],
  emergency: ["Bleeding", "Not breathing", "Broken bone", "Chest pain"],
};

export default function TriageChat({ incidentId, language, onComplete, onError }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [complete, setComplete] = useState(false);
  const [instruction, setInstruction] = useState<string | null>(null);
  const [severity, setSeverity] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Fetch first question — uses incident ID so server knows this is existing
  useEffect(() => {
    const init = async () => {
      try {
        const resp = await roadsosApi.initiateIncident({
          lat: 0, lng: 0,
          channel: "pwa",
          location_accuracy_m: 0,
          language: language || "en",
        });
        // The incident was already created on splash page — we reuse the
        // first question from the response (or fall back to default)
        const q = resp.first_question || "Are you the victim, or are you helping someone else?";
        setMessages([{ text: q, sender: "bot" }]);
      } catch {
        setMessages([
          { text: "Connection error. Please check your network.", sender: "bot" },
        ]);
      }
    };
    init();
  }, [incidentId, language]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, instruction, loading]);

  useEffect(() => {
    if (!loading && !complete) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [loading, complete]);

  const sendAnswer = useCallback(
    async (answer: string) => {
      if (loading || complete) return;
      setLoading(true);
      setInput("");
      setInstruction(null);

      setMessages((prev) => [...prev, { text: answer, sender: "user" }]);

      try {
        const resp = await roadsosApi.sendTriage(incidentId, answer);

        if (resp.instruction) {
          setInstruction(resp.instruction);
        }

        if (resp.triage_complete) {
          setComplete(true);
          setSeverity(resp.severity);

          const botMsg: Message = {
            text: resp.next_question || `Triage complete. Severity: ${resp.severity}. `,
            sender: "bot",
            severity: resp.severity,
          };
          setMessages((prev) => [...prev, botMsg]);
          setTimeout(() => onComplete(resp), 1500);
        } else if (resp.next_question) {
          setMessages((prev) => [
            ...prev,
            {
              text: resp.next_question,
              sender: "bot",
              instruction: resp.instruction,
            },
          ]);
          if (resp.instruction) setInstruction(resp.instruction);
        }
      } catch (err: any) {
        const msg = "Sorry, there was an error. Help has been notified and is on the way.";
        setMessages((prev) => [...prev, { text: msg, sender: "bot" }]);
        onError?.(err.message || "Triage error");
      } finally {
        setLoading(false);
      }
    },
    [incidentId, loading, complete, onComplete, onError, language]
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim()) sendAnswer(input.trim());
  };

  const isSevere = severity === "RED";

  return (
    <main className="min-h-screen bg-sos-dark flex flex-col">
      {/* Status bar */}
      <div
        className={`px-4 py-2 flex items-center justify-between border-b ${
          isSevere ? "bg-sos-red/15 border-sos-red/30" : "bg-white/5 border-white/10"
        }`}
      >
        <div className="flex items-center gap-2">
          <div
            className={`w-2.5 h-2.5 rounded-full ${
              loading
                ? "bg-sos-orange animate-pulse-fast"
                : "bg-sos-red animate-pulse-fast"
            }`}
          />
          <span className="text-xs font-medium">
            {complete ? "Triage Complete" : loading ? "Processing…" : "Triage Active"}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[10px] text-white/40">{incidentId.slice(0, 8).toUpperCase()}</span>
          <button
            onClick={() => window.history.back()}
            className="text-xs px-2 py-1 rounded bg-white/10 hover:bg-white/20 transition-colors"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 max-w-lg mx-auto w-full">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.sender === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`rounded-2xl px-4 py-2.5 text-sm max-w-[85%] leading-relaxed ${
                msg.sender === "user"
                  ? "bg-sos-red text-white rounded-tr-sm"
                  : "glass-card text-white/90 rounded-tl-sm"
              } ${msg.severity === "RED" && msg.sender === "bot" ? "border border-sos-red/30" : ""}`}
            >
              <span className="whitespace-pre-line">{msg.text}</span>
              {msg.instruction && msg.sender === "bot" && (
                <div className="mt-2 p-2 bg-white/5 rounded text-xs border border-white/10">
                  💡 {msg.instruction}
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Instruction banner */}
        {instruction && !loading && (
          <div className="glass-card border border-sos-orange/30 rounded-xl p-3 animate-pulse">
            <span className="font-semibold text-sos-orange">⚠️ Action Required:</span> {instruction}
          </div>
        )}

        {/* Loading indicator */}
        {loading && (
          <div className="flex justify-start">
            <div className="glass-card rounded-2xl px-4 py-3">
              <div className="flex gap-1.5 items-center">
                <div className="w-2 h-2 rounded-full bg-white/30 animate-bounce" />
                <div className="w-2 h-2 rounded-full bg-white/30 animate-bounce" style={{ animationDelay: "0.15s", animationDuration: "0.6s" }} />
                <div className="w-2 h-2 rounded-full bg-white/30 animate-bounce" style={{ animationDelay: "0.3s", animationDuration: "0.7s" }} />
                <span className="text-xs text-white/30 ml-2">thinking…</span>
              </div>
            </div>
          </div>
        )}

        <div ref={endRef} />

        {/* Triage result */}
        {complete && (
          <div className="text-center mt-6 p-4 rounded-2xl bg-white/5 border border-sos-green/30">
            <div className="text-3xl mb-2">{severity === "RED" ? "🚨" : "⚠️"}</div>
            <div className={`font-black text-lg severity-${severity || "RED"}`}>
              Severity: {severity || "UNKNOWN"}
            </div>
            <p className="text-xs text-white/40 mt-1">
              {severity === "RED"
                ? "Critical — Ambulance dispatched immediately"
                : "Help has been notified. Stay on the line."}
            </p>
          </div>
        )}
      </div>

      {/* Quick replies + input */}
      {!complete && (
        <div className="border-t border-white/10 p-4 pb-[calc(1rem+env(safe-area-inset-bottom,0px))] max-w-lg mx-auto w-full">
          <div className="flex gap-2 mb-2 overflow-x-auto pb-1">
            {(!loading
              ? (severity === "RED"
                  ? QUICK_REPLIES.emergency
                  : QUICK_REPLIES.default
                )
              : []
            ).map((reply) => (
              <button
                key={reply}
                onClick={() => sendAnswer(reply)}
                disabled={loading}
                className="px-3 py-1.5 rounded-full text-xs glass-card text-white/60
                  whitespace-nowrap hover:bg-white/10 hover:text-white transition-colors
                  disabled:opacity-30 active:scale-95"
              >
                {reply}
              </button>
            ))}
            {!loading && (
              <button
                onClick={() => {
                  const Rec = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
                  if (Rec) {
                    const r = new Rec();
                    r.lang = language === "hi" ? "hi-IN" : "en-US";
                    r.interimResults = false;
                    r.onresult = (e: any) => sendAnswer(e.results[0][0].transcript);
                    r.start();
                  }
                }}
                disabled={loading}
                className="px-3 py-1.5 rounded-full bg-sos-red/20 text-xs text-sos-red
                  hover:bg-sos-red/30 transition-colors disabled:opacity-30 active:scale-95"
              >
                🎤
              </button>
            )}
          </div>

          <form onSubmit={handleSubmit} className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={complete ? "Session complete" : "Describe what you see…"}
              disabled={loading || complete}
              className="flex-1 bg-white/10 rounded-full px-4 py-3 text-sm text-white
                placeholder:text-white/30 outline-none focus:ring-2 focus:ring-sos-red/50
                disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <button
              type="submit"
              disabled={loading || complete || !input.trim()}
              className="btn-sos rounded-full px-5 py-3 text-sm disabled:opacity-40 active:scale-95"
            >
              {loading ? "…" : "→"}
            </button>
          </form>
        </div>
      )}
    </main>
  );
}