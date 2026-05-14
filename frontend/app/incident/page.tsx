"use client";

import { useState, useRef, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { roadsosApi } from "@/lib/api";

interface Message {
  text: string;
  sender: "bot" | "user";
  instruction?: string;
  severity?: string;
}

const QUICK_REPLIES_DEFAULT = ["Yes", "No", "Unconscious", "Not sure"];
const QUICK_REPLIES_EMERGENCY = ["Bleeding", "Not breathing", "Broken bone", "Chest pain"];

export default function TriagePage() {
  const router = useRouter();
  const incidentId = useSearchParams().get("id");

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [complete, setComplete] = useState(false);
  const [instruction, setInstruction] = useState<string | null>(null);
  const [severity, setSeverity] = useState<string | null>(null);
  const [triageState, setTriageState] = useState<string>("INIT");
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Fetch first question from existing incident
  useEffect(() => {
    if (!incidentId) {
      router.push("/");
      return;
    }

    async function initTriage() {
      try {
        setLoading(true);
        const resp = await roadsosApi.startTriage(incidentId);
        setTriageState(resp.triage_state || "INIT");
        setMessages([{ text: resp.first_question, sender: "bot" }]);
      } catch {
        setMessages([
          { text: "Connection error. Please check your network.", sender: "bot" },
        ]);
      } finally {
        setLoading(false);
      }
    }

    initTriage();
  }, [incidentId, router]);

  // Auto-scroll and focus
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, instruction, loading]);

  useEffect(() => {
    if (!loading && !complete) setTimeout(() => inputRef.current?.focus(), 100);
  }, [loading, complete]);

  const sendAnswer = useCallback(
    async (answer: string) => {
      if (loading || complete || !incidentId) return;
      setLoading(true);
      setInput("");
      setInstruction(null);

      setMessages((prev) => [...prev, { text: answer, sender: "user" }]);

      try {
        const resp = await roadsosApi.sendTriage(incidentId, answer);

        if (resp.instruction) setInstruction(resp.instruction);
        setTriageState(resp.severity || triageState);

        if (resp.triage_complete) {
          setComplete(true);
          setSeverity(resp.severity);

          const botMsg: Message = {
            text: resp.next_question || `Triage complete. Severity: ${resp.severity}.`,
            sender: "bot",
            severity: resp.severity,
            instruction: resp.instruction,
          };
          setMessages((prev) => [...prev, botMsg]);

          // Auto-navigate to dispatch
          setTimeout(() => {
            if (resp.dispatch_options) {
              router.push(`/dispatch?id=${incidentId}&severity=${resp.severity}`);
            } else {
              router.push(`/complete?id=${incidentId}&severity=${resp.severity}`);
            }
          }, 2500);
        } else if (resp.next_question) {
          setMessages((prev) => [
            ...prev,
            { text: resp.next_question, sender: "bot", instruction: resp.instruction || undefined },
          ]);
        }
      } catch {
        setMessages((prev) => [
          ...prev,
          { text: "Error processing response. Help has been notified.", sender: "bot" },
        ]);
      } finally {
        setLoading(false);
      }
    },
    [incidentId, loading, complete, router]
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim()) sendAnswer(input.trim());
  };

  const isSevere = severity === "RED";
  const quickReplies = isSevere
    ? QUICK_REPLIES_EMERGENCY
    : QUICK_REPLIES_DEFAULT;

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
            className={`w-2.5 h-2.5 rounded-full ${loading ? "bg-sos-orange" : "bg-sos-red"} animate-pulse-fast`}
          />
          <span className="text-xs font-medium">
            {complete ? "Triage Complete!" : loading ? "Loading…" : "Triage Active"}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[10px] text-white/40">
            {incidentId?.slice(0, 8).toUpperCase()}
          </span>
          <button
            onClick={() => router.push("/")}
            className="text-xs px-2 py-1 rounded-full bg-white/10 hover:bg-white/20 transition-colors"
          >
            ✕ Home
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
              }`}
            >
              <span className="whitespace-pre-line">{msg.text}</span>
              {/* Show instruction as a sub-bubble only on bot messages */}
              {msg.instruction && msg.sender === "bot" && (
                <div className="mt-2 p-2 bg-white/5 rounded-lg text-xs border border-white/10">
                  💡 {msg.instruction}
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Instruction banner */}
        {instruction && !loading && (
          <div className="glass-card border border-sos-orange/30 rounded-xl p-3 text-sm">
            <span className="font-semibold text-sos-orange">⚠️ Action Required:</span>{" "}
            {instruction}
          </div>
        )}

        {/* Loading indicator */}
        {loading && messages.length === 0 && (
          <div className="flex justify-center py-12">
            <div className="text-center">
              <div className="w-12 h-12 mx-auto mb-3 flex gap-2 items-center justify-center">
                <div className="w-2.5 h-2.5 rounded-full bg-white/40 animate-bounce" style={{ animationDelay: "0s" }} />
                <div className="w-2.5 h-2.5 rounded-full bg-white/40 animate-bounce" style={{ animationDelay: "0.15s" }} />
                <div className="w-2.5 h-2.5 rounded-full bg-white/40 animate-bounce" style={{ animationDelay: "0.3s" }} />
              </div>
              <p className="text-xs text-white/40">Connecting to RoadSoS AI…</p>
            </div>
          </div>
        )}

        {loading && messages.length > 0 && (
          <div className="flex justify-start">
            <div className="glass-card rounded-2xl px-4 py-3">
              <div className="flex gap-1.5 items-center">
                <div className="w-2 h-2 rounded-full bg-white/30 animate-bounce" />
                <div className="w-2 h-2 rounded-full bg-white/30 animate-bounce" style={{ animationDelay: "0.15s" }} />
                <div className="w-2 h-2 rounded-full bg-white/30 animate-bounce" style={{ animationDelay: "0.3s" }} />
                <span className="text-xs text-white/30 ml-2">thinking…</span>
              </div>
            </div>
          </div>
        )}

        <div ref={endRef} />

        {/* Severity badge shown after completion */}
        {complete && (
          <div className="text-center mt-6 p-4 rounded-2xl bg-white/5 border border-sos-green/30">
            <div className="text-3xl mb-2">{isSevere ? "🚨" : "⚠️"}</div>
            <div className={`font-black text-lg severity-${severity || "RED"}`}>
              Severity: {severity || "UNKNOWN"}
            </div>
            <p className="text-xs text-white/40 mt-1">
              {isSevere
                ? "Critical — Ambulance dispatched immediately"
                : "Help has been notified. Stay on the line."}
            </p>
          </div>
        )}
      </div>

      {/* Quick replies */}
      {!complete && (
        <div className="border-t border-white/10 p-4 pb-[calc(1rem+env(safe-area-inset-bottom,0px))] max-w-lg mx-auto w-full">
          <div className="flex gap-2 mb-2 overflow-x-auto pb-1">
            {!loading &&
              quickReplies.map((reply) => (
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
          </div>

          <form onSubmit={handleSubmit} className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Describe what you see…"
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