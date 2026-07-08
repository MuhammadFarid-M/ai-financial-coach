import { useState } from "react";
import { api } from "../api";

// Password policy — mirrored on the backend (security.password_problems).
// Only the rules the user has NOT yet satisfied are shown, live.
const PW_RULES = [
  { test: (p) => p.length >= 8, msg: "at least 8 characters" },
  { test: (p) => /[A-Z]/.test(p), msg: "one uppercase letter" },
  { test: (p) => /[a-z]/.test(p), msg: "one lowercase letter" },
  { test: (p) => /[0-9]/.test(p), msg: "one number" },
  { test: (p) => /[^A-Za-z0-9]/.test(p), msg: "one special character" },
];

const EyeIcon = (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z" />
    <circle cx="12" cy="12" r="3" />
  </svg>
);

const EyeOffIcon = (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
    <line x1="1" y1="1" x2="23" y2="23" />
  </svg>
);

export default function AuthPage({ onAuthed }) {
  const [mode, setMode] = useState("signin"); // "signin" | "signup"
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPwErrors, setShowPwErrors] = useState(false);

  const isSignup = mode === "signup";

  // Only the FAILED rules, recomputed live as the user types.
  const pwProblems = PW_RULES.filter((r) => !r.test(password)).map((r) => r.msg);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

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
        <div className="password-wrap">
          <input
            id="password"
            className="field password-field"
            type={showPw ? "text" : "password"}
            autoComplete={isSignup ? "new-password" : "current-password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={isSignup ? "8+ chars, upper, lower, number, symbol" : "Your password"}
            required
          />
          <button
            type="button"
            className="pw-toggle"
            onClick={() => setShowPw((v) => !v)}
            aria-label={showPw ? "Hide password" : "Show password"}
            tabIndex={-1}
          >
            {showPw ? EyeOffIcon : EyeIcon}
          </button>
        </div>

        {/* Only the unmet rules (signup, after first submit). */}
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
