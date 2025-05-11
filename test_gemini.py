import google.generativeai as genai
import os
from dotenv import load_dotenv
import sys

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY is not set in the environment.")
    sys.exit(1)

print(f"API key length: {len(api_key)} characters")

# Configure the API
genai.configure(api_key=api_key)

def test_model(model_name):
    """Test if a model works."""
    print(f"\nTesting model: {model_name}")
    try:
        model = genai.GenerativeModel(model_name=model_name)
        response = model.generate_content("Hello, are you working?")
        print(f"✓ Success! Model {model_name} responded with: {response.text[:50]}...")
        return True
    except Exception as e:
        print(f"✗ Failed: {str(e)}")
        return False

# Test different model names
model_names = [
    "gemini-flash",              # New 2.0 Flash model (faster)
    "gemini-2.0-flash",          # Alternative naming for 2.0 Flash
    "models/gemini-flash",       # Full path for Flash model
    "models/gemini-2.0-flash",   # Full path with version
    "gemini-pro",
    "gemini-1.0-pro",
    "gemini-1.5-pro",
    "models/gemini-pro", 
    "models/gemini-1.0-pro",
    "models/gemini-1.5-pro"
]

print("\nTesting models...")
working_models = []

for name in model_names:
    if test_model(name):
        working_models.append(name)

print("\nSummary:")
if working_models:
    print(f"Working models: {', '.join(working_models)}")
else:
    print("No models are working. Please check your API key and internet connection.")
