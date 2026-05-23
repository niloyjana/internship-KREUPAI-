import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from groq import AsyncGroq
import httpx

async def main():
    print("Initializing AsyncGroq with default client...")
    try:
        # Test default client initialization
        client = AsyncGroq(timeout=5.0)
        print("AsyncGroq initialized successfully.")
        
        print("Sending simple model list request...")
        models = await client.models.list()
        print(f"Success! Models listed: {len(models.data)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
