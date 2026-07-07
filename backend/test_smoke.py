"""
End-to-end smoke test. Run with:  python test_smoke.py

It walks the full happy path the frontend will use:
signup -> save profile -> read profile -> create session -> chat ->
load messages -> list sessions -> delete session.

Uses FastAPI's TestClient, so no separate server needs to be running.
(The AI runs in local/offline mode unless OPENROUTER_API_KEY is set.)
"""
import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def main():
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"

    # 1. Signup
    r = client.post("/auth/signup", json={
        "email": email, "username": "Priya", "password": "secret123",
    })
    assert r.status_code == 201, r.text
    auth = r.json()
    token = auth["access_token"]
    user_id = auth["user_id"]
    headers = {"Authorization": f"Bearer {token}"}
    print("signup ok        ->", user_id, auth["username"])

    # 2. Login (verify credentials work too)
    r = client.post("/auth/login", json={"email": email, "password": "secret123"})
    assert r.status_code == 200, r.text
    print("login ok")

    # 3. Save profile
    r = client.post("/api/save-profile", headers=headers, json={
        "user_id": user_id,
        "monthly_income": 500000,
        "monthly_expenses": 50000,
        "current_savings": 300000,
        "risk_tolerance": "Aggressive growth",
    })
    assert r.status_code == 200, r.text
    print("save-profile ok  ->", r.json())

    # 4. Read profile
    r = client.get(f"/profile/{user_id}", headers=headers)
    assert r.status_code == 200, r.text
    print("get profile ok   ->", r.json())

    # 5. Create session
    r = client.post("/api/sessions", headers=headers, json={"user_id": user_id})
    assert r.status_code == 201, r.text
    session = r.json()
    session_id = session["id"]
    print("create session ok->", session["title"])

    # 6. Chat (no metrics in payload — server reads them from the saved profile)
    r = client.post("/api/chat", headers=headers, json={
        "user_id": user_id,
        "session_id": session_id,
        "prompt": "How should I budget and allocate my monthly surplus?",
    })
    assert r.status_code == 200, r.text
    msg = r.json()
    print("chat ok          -> chart_bool:", msg["chart_bool"], "| chart_data:", msg["chart_data"])
    print("                    response:", msg["conversational_response"][:90], "...")

    # 7. Load messages
    r = client.get(f"/api/sessions/{session_id}/messages", headers=headers)
    assert r.status_code == 200 and len(r.json()) == 1, r.text
    print("get messages ok  -> count:", len(r.json()))

    # 8. List sessions
    r = client.get(f"/api/sessions/{user_id}", headers=headers)
    assert r.status_code == 200 and len(r.json()) == 1, r.text
    print("list sessions ok -> count:", len(r.json()))

    # 9. Auth must be enforced
    r = client.get(f"/profile/{user_id}")  # no token
    assert r.status_code in (401, 403), r.text
    print("auth enforced ok -> no token rejected with", r.status_code)

    # 10. Delete session (cascade removes its messages)
    r = client.delete(f"/api/sessions/{session_id}", headers=headers)
    assert r.status_code == 204, r.text
    r = client.get(f"/api/sessions/{user_id}", headers=headers)
    assert r.status_code == 200 and len(r.json()) == 0, r.text
    print("delete session ok-> sessions now:", len(r.json()))

    print("\nALL CHECKS PASSED ✅")


if __name__ == "__main__":
    main()
