import { useState } from "react";
import { getAuth, saveAuth, clearAuth } from "./auth";
import AuthPage from "./components/AuthPage";
import FinancialCoach from "./components/FinancialCoach";
import ThemeToggle from "./components/ThemeToggle";

// The whole app is gated on auth: no saved token -> AuthPage; otherwise the
// workspace. `auth` lives in React state so logging in/out re-renders instantly.
export default function App() {
  const [auth, setAuth] = useState(getAuth());

  function handleAuthed(data) {
    saveAuth(data);
    setAuth(data);
  }

  function handleLogout() {
    clearAuth();
    setAuth(null);
  }

  return (
    <>
      <ThemeToggle />
      {!auth ? (
        <AuthPage onAuthed={handleAuthed} />
      ) : (
        <FinancialCoach auth={auth} onLogout={handleLogout} />
      )}
    </>
  );
}
