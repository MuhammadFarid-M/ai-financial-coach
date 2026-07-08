import os
from dotenv import load_dotenv
import httpx
load_dotenv()
key = os.getenv("OPENROUTER_API_KEY")
base = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
r = httpx.post(f"{base}/chat/completions",
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    json={"model": "openrouter/free", "messages": [{"role": "user", "content": "hi"}]},
    timeout=60)
print("STATUS:", r.status_code)
print("BODY:", r.text[:400])
