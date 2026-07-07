// Auth bundle for the logged-in user: { access_token, user_id, username }.
//
// We use sessionStorage (NOT localStorage) on purpose: sessionStorage is wiped
// when the tab/browser closes, so the user must log in again on their next
// visit — standard behaviour for real apps. Their threads, messages, and
// profile are safe in the database and reappear after they log back in.
const KEY = "afw_auth";

export function saveAuth(data) {
  sessionStorage.setItem(KEY, JSON.stringify(data));
}

export function getAuth() {
  try {
    return JSON.parse(sessionStorage.getItem(KEY));
  } catch {
    return null;
  }
}

export function clearAuth() {
  sessionStorage.removeItem(KEY);
}
