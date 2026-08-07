"use client";

import { useState } from "react";
import { askAssistant, type AskResponse } from "@/lib/api";

const EXAMPLE_QUESTIONS = [
  "How is the system performing this month?",
  "What trades are currently open?",
  "Are longs or shorts performing better?",
  "Should I retrain the ML model yet?",
  "What factors actually predict a win?",
];

interface Exchange {
  question: string;
  response: AskResponse | null;
  error: string | null;
}

export default function AssistantPage() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<Exchange[]>([]);
  const [showData, setShowData] = useState<number | null>(null);

  const ask = async (q: string) => {
    const trimmed = q.trim();
    if (!trimmed || loading) return;
    setLoading(true);
    setQuestion("");
    try {
      const response = await askAssistant(trimmed);
      setHistory((h) => [...h, { question: trimmed, response, error: null }]);
    } catch (e) {
      setHistory((h) => [...h, { question: trimmed, response: null, error: (e as Error).message }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="max-w-3xl mx-auto px-6 py-10">
      <header className="mb-6">
        <h1 className="text-2xl font-bold mb-1">AI Research Assistant</h1>
        <p className="text-sm text-gray-400">
          Answers are grounded in this system&apos;s own trade database — resolved
          trades, calibration reports, open positions — not live guessing. If the
          data doesn&apos;t support an answer, it says so instead of making one up.
        </p>
      </header>

      {history.length === 0 && (
        <div className="mb-6 flex flex-wrap gap-2">
          {EXAMPLE_QUESTIONS.map((q) => (
            <button
              key={q}
              onClick={() => ask(q)}
              className="text-xs px-3 py-1.5 rounded-full border border-border text-gray-400 hover:text-gray-100 hover:border-gray-500"
            >
              {q}
            </button>
          ))}
        </div>
      )}

      <div className="space-y-4 mb-6">
        {history.map((ex, i) => (
          <div key={i} className="border border-border rounded-lg bg-panel p-4">
            <div className="text-sm font-medium text-gray-200 mb-2">{ex.question}</div>
            {ex.error && (
              <div className="text-sm text-bear">
                {ex.error}. Is the backend running on :8000?
              </div>
            )}
            {ex.response && (
              <>
                <div className="text-sm text-gray-300 whitespace-pre-wrap leading-relaxed">
                  {ex.response.answer}
                </div>
                <div className="mt-3 flex items-center gap-3 text-xs text-gray-600">
                  {ex.response.categories_matched.length > 0 && (
                    <span>Matched: {ex.response.categories_matched.join(", ")}</span>
                  )}
                  <button
                    onClick={() => setShowData(showData === i ? null : i)}
                    className="underline hover:text-gray-300"
                  >
                    {showData === i ? "Hide raw data" : "Show raw data used"}
                  </button>
                </div>
                {showData === i && (
                  <pre className="mt-2 text-xs bg-bg border border-border rounded p-3 overflow-x-auto max-h-80 overflow-y-auto text-gray-400">
                    {JSON.stringify(ex.response.data, null, 2)}
                  </pre>
                )}
              </>
            )}
          </div>
        ))}
        {loading && <div className="text-sm text-gray-500">Reading the database…</div>}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(question);
        }}
        className="flex gap-2"
      >
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask about your trades, performance, or patterns…"
          className="flex-1 bg-panel border border-border rounded px-3 py-2 text-sm text-gray-200 placeholder:text-gray-600 focus:outline-none focus:border-gray-500"
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="px-4 py-2 rounded bg-bull text-black text-sm font-medium disabled:opacity-40"
        >
          Ask
        </button>
      </form>

      <footer className="mt-8 text-xs text-gray-600 border-t border-border pt-4">
        Not financial advice. Answers reflect this system&apos;s own historical
        performance data, which may be a very small sample early on — the
        assistant will say so when that&apos;s the case.
      </footer>
    </main>
  );
}
