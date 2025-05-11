import os
import google.generativeai as genai
from dotenv import load_dotenv
import time
import signal
import sys

# Set timeout handler
def timeout_handler(signum, frame):
    print("\nTimeout occurred! The API call is taking too long.")
    sys.exit(1)

# Set 30 second timeout
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(30)

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY is not set in the environment.")
    sys.exit(1)

print(f"API key length: {len(api_key)} characters")
print(f"First 4 chars: {api_key[:4]}")

try:
    # Configure the API
    print("Configuring API with key...")
    genai.configure(api_key=api_key)
    print("API configured successfully")

    # Define models to test
    models_to_test = [
        "gemini-flash",
        "gemini-2.0-flash",
        "models/gemini-flash",
        "models/gemini-2.0-flash"
    ]

    # Try each model
    for model_name in models_to_test:
        print(f"\n-------------------------------------------")
        print(f"Testing model: {model_name}")
        print(f"-------------------------------------------")
        
        try:
            print("Creating model instance...")
            model = genai.GenerativeModel(model_name=model_name)
            print("Model instance created successfully")
            
            print("Generating a test response (this may take a few seconds)...")
            start_time = time.time()
            response = model.generate_content("Hello, please respond with just 'ok' to test if you're working.")
            end_time = time.time()
            
            print(f"Success! Model responded in {end_time - start_time:.2f} seconds")
            print(f"Response: {response.text}")
            
            print("\nThis model works and can be used in your application!")
            sys.exit(0)  # Exit with success if any model works
            
        except Exception as e:
            print(f"Error testing {model_name}: {str(e)}")
            print("Trying next model...\n")

    # If we get here, no models worked
    print("\nNone of the Gemini 2.0 Flash models worked with your API key.")
    print("Please check:")
    print("1. Your API key is valid")
    print("2. You have access to the Gemini 2.0 models")
    print("3. Your network connection")
    
except Exception as e:
    print(f"An error occurred: {str(e)}")

finally:
    # Cancel the alarm
    signal.alarm(0)
