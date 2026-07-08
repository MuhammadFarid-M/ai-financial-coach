import os
from dotenv import load_dotenv
import httpx
load_dotenv()
key = os.getenv("GROQ_API_KEY")
print("Key present:", bool(key), "| starts with:", (key or "")[:4])
r = httpx.post("https://api.groq.com/openai/v1/chat/completions",
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    json={"model": "openai/gpt-oss-120b", "messages": [{"role":"user","content":"say hi in 3 words"}]}, timeout=60)
print("GROQ STATUS:", r.status_code)
print(r.text[:300])
