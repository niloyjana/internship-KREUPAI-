import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from groq import AsyncGroq
import httpx

async def main():
    print("Initializing AsyncGroq with explicit httpx.AsyncClient()...")
    try:
        # Use explicit http_client to bypass proxies issue
        client = AsyncGroq(
            http_client=httpx.AsyncClient(),
            timeout=5.0
        )
        print("AsyncGroq initialized successfully.")
        
        print("Sending completions request...")
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": "Hello, say the word 'active'."}],
            temperature=0.2,
            max_tokens=50
        )
        print("Success!")
        print(f"Content: {response.choices[0].message.content}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
