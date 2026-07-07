import { useState } from "react";
import { api } from "../api";

// Password policy — mirrored on the backend (security.password_problems).
// Each rule shows as a small red hint under the field when unmet.
const PW_RULES = [
  { test: (p) => p.length >= 8, msg: "at least 8 characters" },
  { test: (p) => /[A-Z]/.test(p), msg: "one uppercase letter" },
  { test: (p) => /[a-z]/.test(p), msg: "one lowercase letter" },
  { test: (p) => /[0-9]/.test(p), msg: "one number" },
  { test: (p) => /[^A-Za-z0-9]/.test(p), msg: "one special character" },
];

// One card that toggles between Sign In and Create Account. Username only
// matters for signup (the backend logs in with email + password).
export default function AuthPage({ onAuthed }) {
  const [mode, setMode] = useState("signin"); // "signin" | "signup"
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPwErrors, setShowPwErrors] = useState(false);

  const isSignup = mode === "signup";

  // Live list of unmet rules for the current password.
  const pwProblems = PW_RULES.filter((r) => !r.test(password)).map((r) => r.msg);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    // On signup, block submit if the password doesn't meet the rules, and
    // reveal the red hints. They then clear line-by-line as the user types.
    if (isSignup && pwProblems.length > 0) {
      setShowPwErrors(true);
      return;
    }

    setLoading(true);
    try {
      const data = isSignup
        ? await api.signup(email, username, password)
        : await api.login(email, password);
      onAuthed(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function switchMode() {
    setMode(isSignup ? "signin" : "signup");
    setError("");
    setShowPwErrors(false);
  }

  return (
    <div className="auth-wrap">
      <form className="auth-card" onSubmit={handleSubmit}>
        <h1 className="auth-title">{isSignup ? "Create Account" : "Sign In"}</h1>
        <p className="auth-sub">AI Financial Workspace</p>

        <label className="field-label" htmlFor="email">Email Address</label>
        <input
          id="email"
          className="field"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          required
        />

        {isSignup && (
          <>
            <label className="field-label" htmlFor="username">Username</label>
            <input
              id="username"
              className="field"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Your name"
              required
            />
          </>
        )}

        <label className="field-label" htmlFor="password">Password</label>
        <input
          id="password"
          className="field"
          type="password"
          autoComplete={isSignup ? "new-password" : "current-password"}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder={isSignup ? "8+ chars, upper, lower, number, symbol" : "Your password"}
          required
        />

        {/* Live red hints for each unmet rule (signup only, after first submit). */}
        {isSignup && showPwErrors && pwProblems.length > 0 && (
          <ul className="pw-hints">
            {pwProblems.map((m) => (
              <li key={m}>Password must have {m}</li>
            ))}
          </ul>
        )}

        {error && <div className="form-error">{error}</div>}

        <button className="btn-primary" type="submit" disabled={loading}>
          {loading ? "Please wait..." : isSignup ? "Sign Up" : "Sign In"}
        </button>

        <div className="auth-toggle">
          {isSignup ? "Already have an account?" : "New here?"}{" "}
          <button type="button" className="link" onClick={switchMode}>
            {isSignup ? "Sign In" : "Create Account"}
          </button>
        </div>
      </form>
    </div>
  );
}
