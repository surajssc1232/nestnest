import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Error: GEMINI_API_KEY is not set in the environment.")
    exit(1)

print(f"API key length: {len(api_key)} characters")

# Check if it starts with "AIza" (common for Google API keys)
if api_key.startswith("AIza"):
    print("✅ API key has the correct prefix format (AIza...)")
else:
    print("⚠️ API key doesn't have the expected prefix. Google API keys typically start with 'AIza'")

# Check length (Google API keys are typically 39 characters)
if len(api_key) == 39:
    print("✅ API key has the expected length (39 characters)")
else:
    print(f"⚠️ API key length is {len(api_key)}, Google API keys are typically 39 characters")

print("\nPlease verify your key in the Google AI Studio:")
print("1. Go to https://makersuite.google.com/app/apikeys")
print("2. Check if this key is listed and active")
print("3. Verify that it has access to Gemini models")
print("\nIf the key is not listed or is inactive, you may need to create a new one.")
