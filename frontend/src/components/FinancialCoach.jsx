import { useEffect, useState } from "react";
import { api } from "../api";
import Sidebar from "./Sidebar";
import ChatWindow from "./ChatWindow";

const EMPTY_PROFILE = {
  monthly_income: "",
  monthly_expenses: "",
  current_savings: "",
  risk_tolerance: "Moderate",
};

// Controls the two-step lifecycle:
//   step 1 = profile setup wizard
//   step 2 = chat workspace (sidebar + chat)
export default function FinancialCoach({ auth, onLogout }) {
  const [step, setStep] = useState(1);
  const [booting, setBooting] = useState(true);

  // profile (step 1)
  const [profile, setProfile] = useState(EMPTY_PROFILE);
  const [savingProfile, setSavingProfile] = useState(false);
  const [profileError, setProfileError] = useState("");

  // workspace (step 2)
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([]);

  // On first load, try to fetch an existing profile. If found, prefill it and
  // jump straight to the workspace; if there's none (404), start at setup.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const p = await api.getProfile(auth.user_id);
        if (cancelled) return;
        setProfile({
          monthly_income: p.monthly_income,
          monthly_expenses: p.monthly_expenses,
          current_savings: p.current_savings,
          risk_tolerance: p.risk_tolerance,
        });
        setStep(2);
      } catch (err) {
        if (err.status !== 404) console.error(err);
        if (!cancelled) setStep(1);
      } finally {
        if (!cancelled) setBooting(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [auth.user_id]);

  // Load the user's threads whenever we're in the workspace.
  useEffect(() => {
    if (step !== 2) return;
    api.listSessions(auth.user_id).then(setSessions).catch(console.error);
  }, [step, auth.user_id]);

  async function handleSaveProfile(e) {
    e.preventDefault();
    setProfileError("");

    // Reject negative numbers before saving.
    if (
      Number(profile.monthly_income) < 0 ||
      Number(profile.monthly_expenses) < 0 ||
      Number(profile.current_savings) < 0
    ) {
      setProfileError("Please fix the highlighted fields — values can't be negative.");
      return;
    }

    setSavingProfile(true);
    try {
      await api.saveProfile({
        user_id: auth.user_id,
        monthly_income: Number(profile.monthly_income) || 0,
        monthly_expenses: Number(profile.monthly_expenses) || 0,
        current_savings: Number(profile.current_savings) || 0,
        risk_tolerance: profile.risk_tolerance,
      });
      setStep(2);
    } catch (err) {
      setProfileError(err.message);
    } finally {
      setSavingProfile(false);
    }
  }

  // --- thread actions ---
  function startNewThread() {
    setActiveSessionId(null); // null => the next message starts a fresh thread
    setMessages([]);
  }

  async function openThread(sessionId) {
    setActiveSessionId(sessionId);
    try {
      const msgs = await api.getMessages(sessionId);
      setMessages(msgs);
    } catch (err) {
      console.error(err);
    }
  }

  async function deleteThread(sessionId) {
    if (!window.confirm("Delete this strategy thread and all of its messages?")) return;
    try {
      await api.deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (sessionId === activeSessionId) startNewThread();
    } catch (err) {
      console.error(err);
    }
  }

  // Sends one prompt. The user's message is shown IMMEDIATELY (optimistic),
  // then replaced with the full exchange once the backend responds. If
  // activeSessionId is null, the backend creates the thread and returns its id.
  async function sendMessage(prompt) {
    const tempId = "temp-" + Date.now();
    setMessages((prev) => [
      ...prev,
      { id: tempId, user_prompt: prompt, conversational_response: null, pending: true },
    ]);

    try {
      const res = await api.chat({
        user_id: auth.user_id,
        session_id: activeSessionId,
        prompt,
      });
      // Swap the optimistic placeholder for the real message.
      setMessages((prev) => prev.map((m) => (m.id === tempId ? res : m)));

      if (res.session_id !== activeSessionId) {
        setActiveSessionId(res.session_id);
        const fresh = await api.listSessions(auth.user_id);
        setSessions(fresh);
      }
    } catch (err) {
      // Roll back the optimistic message and let ChatWindow surface the error.
      setMessages((prev) => prev.filter((m) => m.id !== tempId));
      throw err;
    }
  }

  if (booting) {
    return <div className="booting">Loading your workspace…</div>;
  }

  // ---------- STEP 1: profile setup ----------
  if (step === 1) {
    const neg = (v) => v !== "" && Number(v) < 0;
    const negErrors = {
      monthly_income: neg(profile.monthly_income),
      monthly_expenses: neg(profile.monthly_expenses),
      current_savings: neg(profile.current_savings),
    };
    return (
      <div className="setup-wrap">
        <form className="setup-card" onSubmit={handleSaveProfile}>
          <h1 className="setup-title">👋 Let&rsquo;s Setup Your Financial Profile!</h1>
          <p className="setup-sub">
            These numbers power every strategy the AI builds for you.
          </p>

          <label className="field-label" htmlFor="income">Monthly Income (INR)</label>
          <input
            id="income"
            className="field"
            type="number"
            min="0"
            placeholder="e.g. 500000"
            value={profile.monthly_income}
            onChange={(e) => setProfile({ ...profile, monthly_income: e.target.value })}
            required
          />
          {negErrors.monthly_income && (
            <div className="field-hint-error">Invalid — value can’t be negative</div>
          )}

          <label className="field-label" htmlFor="expenses">
            Monthly Expenses / Essential Needs (INR)
          </label>
          <input
            id="expenses"
            className="field"
            type="number"
            min="0"
            placeholder="e.g. 50000"
            value={profile.monthly_expenses}
            onChange={(e) => setProfile({ ...profile, monthly_expenses: e.target.value })}
            required
          />
          {negErrors.monthly_expenses && (
            <div className="field-hint-error">Invalid — value can’t be negative</div>
          )}

          <label className="field-label" htmlFor="savings">Current Savings (INR)</label>
          <input
            id="savings"
            className="field"
            type="number"
            min="0"
            placeholder="e.g. 300000"
            value={profile.current_savings}
            onChange={(e) => setProfile({ ...profile, current_savings: e.target.value })}
            required
          />
          {negErrors.current_savings && (
            <div className="field-hint-error">Invalid — value can’t be negative</div>
          )}

          <label className="field-label" htmlFor="risk">Risk Tolerance</label>
          <select
            id="risk"
            className="field"
            value={profile.risk_tolerance}
            onChange={(e) => setProfile({ ...profile, risk_tolerance: e.target.value })}
          >
            <option value="Conservative">Conservative — protect capital, steady growth</option>
            <option value="Moderate">Moderate — balanced risk and return</option>
            <option value="Aggressive">Aggressive — higher risk for higher growth</option>
          </select>

          {profileError && <div className="form-error">{profileError}</div>}

          <button className="btn-primary" type="submit" disabled={savingProfile}>
            {savingProfile ? "Saving…" : "OK"}
          </button>
        </form>
      </div>
    );
  }

  // ---------- STEP 2: workspace ----------
  return (
    <div className="workspace">
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onNewThread={startNewThread}
        onOpenThread={openThread}
        onDeleteThread={deleteThread}
        onModifyParams={() => setStep(1)}
        onLogout={onLogout}
      />
      <ChatWindow username={auth.username} messages={messages} onSend={sendMessage} />
    </div>
  );
}
