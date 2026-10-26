# scripts/list_models.py
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY not found in .env file.")
    exit(1)

# Try initializing with both possible API versions
for version in ["v1beta", "v1"]:
    try:
        print(f"\n--- Testing with API version: {version} ---")
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(api_version=version)
        )
        print("Available models for generateContent:")
        found = False
        for model in client.models.list():
            # Check if the model supports generateContent
            if "generateContent" in model.supported_actions:
                print(f"  - {model.name}")
                found = True
        if not found:
            print("  (No models found that support generateContent)")
    except Exception as e:
        print(f"  Error with version {version}: {e}")