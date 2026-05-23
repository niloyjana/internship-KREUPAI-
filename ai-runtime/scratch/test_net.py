import urllib.request
import urllib.error
import os
import json
from dotenv import load_dotenv

load_dotenv()

def test_connection():
    print("Testing general internet connectivity (httpbin)...")
    try:
        response = urllib.request.urlopen("https://httpbin.org/get", timeout=5)
        print(f"Internet Status: Connected (HTTP {response.getcode()})")
    except Exception as e:
        print(f"Internet Status: Failed to connect ({e})")

    groq_key = os.environ.get("GROQ_API_KEY")
    print(f"Testing direct Groq API access with key: {'***' + groq_key[-4:] if groq_key else 'None'}")
    
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/models",
        headers={"Authorization": f"Bearer {groq_key}"} if groq_key else {}
    )
    
    try:
        response = urllib.request.urlopen(req, timeout=5)
        print(f"Groq API connection successful! Status: {response.getcode()}")
        data = json.loads(response.read().decode())
        print(f"Available Groq models count: {len(data.get('data', []))}")
    except urllib.error.HTTPError as e:
        print(f"Groq API returned HTTP error: {e.code} - {e.reason}")
        try:
            err_body = e.read().decode()
            print(f"Error details: {err_body}")
        except Exception:
            pass
    except Exception as e:
        print(f"Groq API connection failed: {e}")

if __name__ == "__main__":
    test_connection()
