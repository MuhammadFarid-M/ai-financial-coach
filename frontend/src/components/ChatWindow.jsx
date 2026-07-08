import { useEffect, useRef, useState } from "react";
import MessageBubble from "./MessageBubble";

// Rotating "thinking" messages, shown one at a time, advancing every ~10s.
// The last one acknowledges the free-tier cold start so a long wait feels normal.
const THINKING_MSGS = [
  "Thinking",
  "Working on it",
  "Just a moment",
  "Almost there",
  "Still working — the free server can take up to a minute",
];

export default function ChatWindow({ username, messages, onSend }) {
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [thinkIdx, setThinkIdx] = useState(0);
  const bodyRef = useRef(null);

  // Keep the latest message in view.
  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [messages, sending, thinkIdx]);

  // Cycle the thinking message every 10s while waiting; reset when idle.
  useEffect(() => {
    if (!sending) {
      setThinkIdx(0);
      return;
    }
    const t = setInterval(() => {
      setThinkIdx((i) => Math.min(i + 1, THINKING_MSGS.length - 1));
    }, 10000);
    return () => clearInterval(t);
  }, [sending]);

  async function handleSend(e) {
    e.preventDefault();
    const prompt = input.trim();
    if (!prompt || sending) return;

    setError("");
    setInput("");
    setSending(true);
    try {
      await onSend(prompt);
    } catch (err) {
      setError(err.message);
      setInput(prompt); // restore the text so the user doesn't lose it
    } finally {
      setSending(false);
    }
  }

  const isEmpty = messages.length === 0 && !sending;

  return (
    <main id="center" className="center">
      <header className="center-header">
        <h1 className="center-title">AI Financial Workspace</h1>
        <p className="center-welcome">Welcome, {username}!</p>
      </header>

      <div className="chat-body" ref={bodyRef}>
        {isEmpty && (
          <div className="chat-empty">
            Your financial intelligence engine is ready. Ask a question below to
            construct data frameworks.
          </div>
        )}

        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}

        {sending && (
          <div className="bubble ai pending">
            <span className="analyzing">
              {THINKING_MSGS[thinkIdx]}
              <span className="dot">.</span>
              <span className="dot">.</span>
              <span className="dot">.</span>
            </span>
          </div>
        )}
        {error && <div className="form-error chat-error">{error}</div>}
      </div>

      <form className="prompt-bar" onSubmit={handleSend}>
        <input
          className="prompt-input"
          placeholder="Ask a financial question..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={sending}
        />
        <button className="btn-primary send-btn" type="submit" disabled={sending}>
          {sending ? "Sending..." : "Send"}
        </button>
      </form>
    </main>
  );
}
