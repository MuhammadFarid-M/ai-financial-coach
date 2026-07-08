// Single front door to the backend. Every network call goes through request(),
// so the base URL, the auth header, and error handling all live in one place.
import { getAuth, clearAuth } from "./auth";

const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, { method = "GET", body, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };

  if (auth) {
    const a = getAuth();
    if (a?.access_token) headers["Authorization"] = `Bearer ${a.access_token}`;
  }

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  // A 401 on an AUTHENTICATED request means the token expired/invalid -> wipe
  // it and bounce to the auth screen. On a PUBLIC request (login/signup) a 401
  // just means bad credentials, so let it fall through to the normal handler
  // below and show the backend's real message ("Incorrect email or password").
  if (res.status === 401 && auth) {
    clearAuth();
    window.location.reload();
    throw new Error("Your session expired. Please sign in again.");
  }

  if (res.status === 204) return null; // No Content (e.g. delete)

  if (!res.ok) {
    let detail = "Something went wrong. Please try again.";
    try {
      const data = await res.json();
      if (data?.detail) detail = data.detail;
    } catch {
      /* response had no JSON body */
    }
    const err = new Error(detail);
    err.status = res.status; // callers can branch on this (e.g. 404 = no profile)
    throw err;
  }

  return res.json();
}

export const api = {
  // --- auth ---
  signup: (email, username, password) =>
    request("/auth/signup", {
      method: "POST",
      auth: false,
      body: { email, username, password },
    }),
  login: (email, password) =>
    request("/auth/login", { method: "POST", auth: false, body: { email, password } }),

  // --- profile ---
  saveProfile: (profile) => request("/api/save-profile", { method: "POST", body: profile }),
  getProfile: (userId) => request(`/profile/${userId}`),

  // --- sessions (threads) ---
  listSessions: (userId) => request(`/api/sessions/${userId}`),
  deleteSession: (sessionId) => request(`/api/sessions/${sessionId}`, { method: "DELETE" }),
  getMessages: (sessionId) => request(`/api/sessions/${sessionId}/messages`),

  // --- chat ---
  // session_id may be null/undefined -> backend starts a new thread and
  // returns its id in the response.
  chat: (payload) => request("/api/chat", { method: "POST", body: payload }),
};
