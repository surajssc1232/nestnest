import os
import google.generativeai as genai
from dotenv import load_dotenv
import PyPDF2
import io
import requests
from youtube_transcript_api import YouTubeTranscriptApi, CouldNotRetrieveTranscript
import sys
import time
import threading
from bs4 import BeautifulSoup
import re

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
        print(f"Attempting to read PDF from: {pdf_path}")
        
        if not os.path.exists(pdf_path):
            error_msg = f"PDF file does not exist at path: {pdf_path}"
            print(error_msg)
            return f"Error: {error_msg}"
            
        if not os.path.isfile(pdf_path):
            error_msg = f"Path exists but is not a file: {pdf_path}"
            print(error_msg)
            return f"Error: {error_msg}"
            
        if not pdf_path.lower().endswith('.pdf'):
            error_msg = f"File does not appear to be a PDF: {pdf_path}"
            print(error_msg)
            return f"Error: {error_msg}"
            
        text = ""
        with open(pdf_path, 'rb') as file:
            try:
                reader = PyPDF2.PdfReader(file)
                
                # Check if PDF is encrypted
                if reader.is_encrypted:
                    return f"Error: PDF file is encrypted and cannot be read: {pdf_path}"
                    
                page_count = len(reader.pages)
                print(f"PDF has {page_count} pages")
                
                for page_num in range(page_count):
                    try:
                        page_text = reader.pages[page_num].extract_text()
                        if page_text:
                            text += page_text + "\n"
                        else:
                            print(f"Warning: No text extracted from page {page_num+1}")
                    except Exception as page_error:
                        print(f"Error extracting text from page {page_num+1}: {str(page_error)}")
                
                # If we didn't get any text but no errors occurred, the PDF might be image-based
                if not text.strip():
                    return "Error: Could not extract text from PDF. The file may contain scanned images rather than text."
                    
                return text
            except PyPDF2.errors.PdfReadError as pdf_error:
                error_msg = f"Invalid or corrupted PDF file: {str(pdf_error)}"
                print(error_msg)
                return f"Error: {error_msg}"
    except Exception as e:
        error_msg = f"Error extracting PDF text: {str(e)}"
        print(error_msg)
        return f"Error: {error_msg}"

def extract_webpage_text(url):
    """Extract text from a webpage using BeautifulSoup for better HTML parsing."""
    try:
        print(f"Fetching webpage content from: {url}")
        
        # Set a user agent to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return f"Error fetching webpage: HTTP {response.status_code}"
            
        # Get content type to check if it's HTML
        content_type = response.headers.get('Content-Type', '').lower()
        if 'text/html' not in content_type:
            return f"URL does not point to HTML content: {content_type}"
            
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "header", "footer", "nav"]):
            script.extract()
            
        # Get text and clean it
        text = soup.get_text(separator=' ')
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        if not text:
            return "Error: No text content found on the webpage."
            
        print(f"Successfully extracted {len(text)} characters from webpage")
        return text
    except Exception as e:
        print(f"Error extracting webpage text: {str(e)}")
        return f"Error extracting webpage text: {str(e)}"

def extract_youtube_transcript(video_id):
    """Extract transcript from a YouTube video with better error handling."""
    try:
        if not video_id:
            print("No video ID provided for transcript extraction")
            return "Error: No valid YouTube video ID found in the URL."
            
        print(f"Fetching transcript for YouTube video: {video_id}")
        
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        if not transcript_list:
            return "Error: No transcript available for this video (it might be disabled or the video might not have one)."
            
        transcript = " ".join([item['text'] for item in transcript_list])
        
        # Add video ID to the transcript for future reference
        transcript = f"YouTube Video ID: {video_id}\n\n{transcript}"
        
        print(f"Successfully extracted transcript of length {len(transcript)}")
        return transcript
    except CouldNotRetrieveTranscript as e:
        error_msg = str(e)
        print(f"YouTubeTranscriptApi error: {error_msg}")
        if "subtitles are disabled" in error_msg.lower():
            return "Error: Cannot retrieve transcript because subtitles are disabled for this video."
        elif "no transcript found" in error_msg.lower():
            return "Error: No transcript or subtitles found for this video."
        else:
            return f"Error: Could not retrieve transcript. The video may not have one, or an API error occurred: {error_msg}"
    except Exception as e:
        error_msg = str(e)
        print(f"Error extracting YouTube transcript: {error_msg}")
        return f"Error extracting YouTube transcript: {error_msg}"

def extract_youtube_id(url):
    """Extract YouTube video ID from URL with improved handling of different formats."""
    try:
        import re
        import urllib.parse

        print(f"Extracting YouTube ID from: {url}")
        
        # Handle empty or None URLs
        if not url:
            print("URL is empty")
            return None
        
        # First pattern: standard youtube.com/watch?v=ID
        if 'youtube.com/watch' in url:
            parsed_url = urllib.parse.urlparse(url)
            params = urllib.parse.parse_qs(parsed_url.query)
            video_id = params.get('v', [''])[0]
            if video_id:
                print(f"Extracted YouTube ID: {video_id}")
                return video_id
        
        # Second pattern: youtu.be/ID
        if 'youtu.be/' in url:
            video_id = url.split('youtu.be/')[-1].split('?')[0].split('&')[0]
            if video_id:
                print(f"Extracted YouTube ID: {video_id}")
                return video_id
        
        # Third pattern: youtube.com/embed/ID
        if 'youtube.com/embed/' in url:
            video_id = url.split('youtube.com/embed/')[-1].split('?')[0].split('&')[0]
            if video_id:
                print(f"Extracted YouTube ID: {video_id}")
                return video_id
                
        # Fourth pattern: youtube.com/v/ID
        if 'youtube.com/v/' in url:
            video_id = url.split('youtube.com/v/')[-1].split('?')[0].split('&')[0]
            if video_id:
                print(f"Extracted YouTube ID: {video_id}")
                return video_id
                
        # Use regex as a fallback to find video IDs
        video_id_regex = r'(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
        match = re.search(video_id_regex, url)
        if match:
            video_id = match.group(1)
            print(f"Extracted YouTube ID using regex: {video_id}")
            return video_id
            
        print("Could not extract YouTube ID from URL")
        return None
    except Exception as e:
        print(f"Error extracting YouTube ID: {str(e)}")
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
        # Check if it's a playlist URL
        if 'list=' in content:
            print(f"Playlist URL detected for chatbot: {content}")
            return "Error: Summaries and quizzes are currently only available for individual YouTube videos, not playlists."
        
        # YouTube video
        video_id = extract_youtube_id(content)
        if video_id:
            return extract_youtube_transcript(video_id)
        else:
            return "Error: Could not extract a valid YouTube video ID from the provided URL for chatbot processing."
    else:
        return "Error: Unsupported resource type for chatbot processing."

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
