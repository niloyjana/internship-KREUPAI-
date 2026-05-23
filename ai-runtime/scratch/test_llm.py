import asyncio
import os
import sys
from dotenv import load_dotenv

# Ensure we're in the right directory to load the module
sys.path.append(os.getcwd())
load_dotenv(override=True)

from llm.gateway import LLMGateway

async def test_llm():
    print(f"Default Provider: {os.environ.get('LLM_DEFAULT_PROVIDER')}")
    print(f"Groq API Key exists: {bool(os.environ.get('GROQ_API_KEY'))}")
    
    gateway = LLMGateway()
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, say the word 'active' if you can hear me."}
    ]
    try:
        print("Sending request to LLM Gateway...")
        response = await gateway.complete(messages)
        print(f"Provider used: {response.provider}")
        print(f"Model used: {response.model}")
        print(f"Content: {response.content}")
    except Exception as e:
        print(f"Error calling LLM Gateway: {e}")

if __name__ == "__main__":
    asyncio.run(test_llm())
