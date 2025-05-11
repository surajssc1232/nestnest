import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY is not set in the environment.")
    sys.exit(1)

print(f"API key length: {len(api_key)} characters")
print(f"API key begins with: {api_key[:10]}...")
print(f"API key ends with: ...{api_key[-5:]}")

# Try to import the google package
try:
    import google.generativeai as genai
    print("Successfully imported google.generativeai")
except Exception as e:
    print(f"Error importing google.generativeai: {str(e)}")
    sys.exit(1)

# Test basic configuration
try:
    genai.configure(api_key=api_key)
    print("API configured successfully")
except Exception as e:
    print(f"Error configuring API: {str(e)}")
    sys.exit(1)

# Try to list available models
print("\nAttempting to list available models...")
try:
    models = list(genai.list_models())
    print(f"Found {len(models)} models")
    for model in models:
        print(f"- {model.name}")
except Exception as e:
    print(f"Error listing models: {str(e)}")
