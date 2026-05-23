import os
import asyncio
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()

async def test_groq():
    client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))
    try:
        models = await client.models.list()
        print("Available models:")
        for model in models.data:
            print(f"- {model.id}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_groq())
