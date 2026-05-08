import os
import httpx
from dotenv import load_dotenv

def test_groq_key():
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY not found in .env")
        return

    print(f"Testing key: {api_key[:10]}...")

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": "Hello, are you working?"}],
        "max_tokens": 10
    }

    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=10.0)
        if response.status_code == 200:
            print("SUCCESS: Groq API key is working!")
            print("Response:", response.json()["choices"][0]["message"]["content"])
        else:
            print(f"FAILURE: Status {response.status_code}")
            print("Detail:", response.text)
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_groq_key()
