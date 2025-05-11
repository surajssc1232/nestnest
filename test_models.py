import os
import google.generativeai as genai
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY is not set in the environment.")
    exit(1)

print(f"API key set: {bool(api_key)}")

# Configure the API
genai.configure(api_key=api_key)

# Define different model names to try
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

# Try creating a model and generating content with each model name
for model_name in model_names:
    print(f"\nTrying model: {model_name}")
    try:
        start_time = time.time()
        print(f"Creating model...")
        model = genai.GenerativeModel(model_name=model_name)
        
        print(f"Testing generation...")
        response = model.generate_content("Hello, what can you do?")
        
        time_taken = time.time() - start_time
        print(f"Success! Model {model_name} works.")
        print(f"Time taken: {time_taken:.2f} seconds")
        print(f"Response preview: {response.text[:100]}...")
        
        # Try chat functionality
        print(f"\nTesting chat functionality with {model_name}...")
        try:
            chat = model.start_chat(history=[])
            response = chat.send_message("Can you understand me?")
            print(f"Chat response: {response.text[:100]}...")
            print("Chat functionality works!")
        except Exception as chat_error:
            print(f"Chat functionality error: {str(chat_error)}")
        
        print("\n" + "="*50)
    except Exception as e:
        print(f"Error with model {model_name}: {str(e)}")
        print("\n" + "="*50)

print("\nTest completed. If any model worked, you can update the chatbot.py file to use that specific model name.")
