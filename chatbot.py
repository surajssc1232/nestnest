import os
import google.generativeai as genai
from dotenv import load_dotenv
import PyPDF2
import io
import requests
from youtube_transcript_api import YouTubeTranscriptApi
import sys
import time
import threading

# Load environment variables
load_dotenv()

# Check if API key is set
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("WARNING: GEMINI_API_KEY is not set in the environment. The chatbot will not function properly.")
    api_key = "not_set"  # Placeholder to prevent errors during startup

# Configure the Gemini API with timeout
genai.configure(api_key=api_key)

# Set up the model
generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 2048,
}

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

# Global variable to track if model works
model_works = False
model = None

class TimeoutError(Exception):
    pass

def timeout_handler():
    raise TimeoutError("API call timed out")

def with_timeout(func, timeout_seconds, *args, **kwargs):
    """Run a function with a timeout."""
    result = [None]
    error = [None]
    completed = [False]
    
    def worker():
        try:
            result[0] = func(*args, **kwargs)
            completed[0] = True
        except Exception as e:
            error[0] = e
    
    thread = threading.Thread(target=worker)
    thread.daemon = True
    thread.start()
    thread.join(timeout_seconds)
    
    if completed[0]:
        return result[0]
    if error[0]:
        raise error[0]
    raise TimeoutError(f"Function call timed out after {timeout_seconds} seconds")

def initialize_model(timeout=20):
    """Initialize the Gemini model with the appropriate model name based on availability."""
    global model, model_works
    
    if api_key == "not_set":
        print("Cannot initialize model without a valid API key")
        return None
        
    # Model names to try, in order of preference
    models_to_try = [
        "gemini-2.0-flash",          # New 2.0 Flash model (faster) 
        "gemini-pro",            # Standard model as fallback
        "models/gemini-flash",   # Full path for Flash model
        "models/gemini-pro"      # Full path for standard model
    ]
    
    for model_name in models_to_try:
        try:
            print(f"Trying to initialize model: {model_name}")
            
            # Create the model with a timeout
            def create_model():
                return genai.GenerativeModel(
                    model_name=model_name,
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
            
            model_instance = with_timeout(create_model, timeout)
            
            # Test the model with a simple prompt
            def test_model():
                return model_instance.generate_content("Test")
            
            try:
                print(f"Testing model {model_name}...")
                response = with_timeout(test_model, timeout)
                print(f"Successfully initialized model: {model_name}")
                model_works = True
                model = model_instance
                return model
            except TimeoutError:
                print(f"Model {model_name} timed out during testing")
            except Exception as test_error:
                print(f"Model {model_name} failed during testing: {str(test_error)}")
                
        except TimeoutError:
            print(f"Model {model_name} initialization timed out")
        except Exception as e:
            print(f"Failed to initialize model {model_name}: {str(e)}")
    
    # If we reach here, all models failed
    print("All model initialization attempts failed.")
    return None

# Initialize the model
print("Starting model initialization...")
model = initialize_model()
print(f"Model initialization complete. Model works: {model_works}")

def extract_pdf_text(pdf_path):
    """Extract text from a PDF file."""
    try:
        text = ""
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page_num in range(len(reader.pages)):
                text += reader.pages[page_num].extract_text() + "\n"
        return text
    except Exception as e:
        return f"Error extracting PDF text: {str(e)}"

def extract_webpage_text(url):
    """Extract text from a webpage."""
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        else:
            return f"Error fetching webpage: HTTP {response.status_code}"
    except Exception as e:
        return f"Error extracting webpage text: {str(e)}"

def extract_youtube_transcript(video_id):
    """Extract transcript from a YouTube video."""
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript = " ".join([item['text'] for item in transcript_list])
        return transcript
    except Exception as e:
        return f"Error extracting YouTube transcript: {str(e)}"

def extract_youtube_id(url):
    """Extract YouTube video ID from URL."""
    if 'youtu.be' in url:
        return url.split('/')[-1].split('?')[0]
    elif 'youtube.com/watch' in url:
        import urllib.parse
        query = urllib.parse.urlparse(url).query
        params = urllib.parse.parse_qs(query)
        return params.get('v', [''])[0]
    return None

def get_resource_text(resource_type, content):
    """Get text from different resource types."""
    if resource_type == 'pdf':
        # Assuming content is a path to the PDF file
        return extract_pdf_text(content)
    elif resource_type == 'link':
        # Web link
        return extract_webpage_text(content)
    elif resource_type == 'youtube':
        # YouTube video
        video_id = extract_youtube_id(content)
        if video_id:
            return extract_youtube_transcript(video_id)
        else:
            return "Could not extract YouTube video ID."
    else:
        return "Unsupported resource type."

def chat_with_gemini(prompt, resource_text=None, chat_history=None, timeout=30):
    """Chat with Gemini API."""
    global model, model_works
    
    # Check if model initialization succeeded
    if not model_works or model is None:
        error_msg = ("The AI chatbot is currently unavailable. "
                    "Please check the API key configuration in the .env file and ensure "
                    "you have a valid Google AI API key.")
        print("Model not available: " + error_msg)
        return error_msg, chat_history if chat_history else []
        
    try:
        # Prepare context
        if resource_text:
            context = f"Context information from the resource:\n{resource_text[:8000]}\n\nUser query: {prompt}"
        else:
            context = prompt
            
        # Define function to start chat
        def start_chat():
            if chat_history is None:
                return model.start_chat(history=[])
            else:
                return model.start_chat(history=chat_history)
                
        # Start a chat session with timeout
        try:
            print("Starting chat session...")
            chat = with_timeout(start_chat, timeout)
            
            # Define function to send message
            def send_message():
                return chat.send_message(context)
                
            # Generate response with timeout
            try:
                print(f"Sending message to model: {prompt[:50]}...")
                response = with_timeout(send_message, timeout)
                print(f"Received response from model: {str(response.text)[:50]}...")
                return response.text, chat.history
            except TimeoutError:
                print("Message generation timed out, trying direct generation")
                
                # Try a more direct approach with timeout if chat fails
                def generate_content():
                    return model.generate_content(context)
                    
                try:
                    response = with_timeout(generate_content, timeout)
                    return response.text, chat_history if chat_history else []
                except TimeoutError:
                    return "The AI model took too long to respond. Please try a simpler question.", chat_history if chat_history else []
                except Exception as e2:
                    print(f"Error in generate_content: {str(e2)}")
                    return f"Error generating response: {str(e2)}", chat_history if chat_history else []
            
        except TimeoutError:
            return "The AI model took too long to initialize. Please try again later.", chat_history if chat_history else []
        except Exception as e:
            print(f"Error in chat.send_message: {str(e)}")
            return f"Error in chat session: {str(e)}", chat_history if chat_history else []
            
    except Exception as e:
        error_message = str(e)
        print(f"Error generating response: {error_message}")
        
        if "404" in error_message and "not found" in error_message:
            return "Sorry, there was an issue with the AI model. Please check your API key and model configuration.", chat_history if chat_history else []
        elif "429" in error_message:
            return "Too many requests to the AI service. Please try again later.", chat_history if chat_history else []
        else:
            return f"Error generating response: {error_message}", chat_history if chat_history else []
