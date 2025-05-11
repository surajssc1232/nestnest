import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv("GEMINI_API_KEY")
print(f"API key found: {bool(api_key)}")

# Configure the API
genai.configure(api_key=api_key)

# List available models
try:
    print("Attempting to list models...")
    models = list(genai.list_models())
    print(f"Found {len(models)} models")
    for model in models:
        print(f"Model: {model.name}")
        print(f"  Supported methods: {model.supported_generation_methods}")
        print(f"  Display name: {getattr(model, 'display_name', 'N/A')}")
        print("-" * 40)
except Exception as e:
    print(f"Error listing models: {str(e)}")
    import traceback
    traceback.print_exc()
