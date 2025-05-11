# NestCircle AI Chatbot

This document describes the AI-powered chatbot feature in NestCircle which uses Google's Gemini API.

## Features

The chatbot allows users to interact with various learning resources (PDF files, web links, YouTube videos) by asking questions about the content.

- **Resource Analysis**: Automatically extracts and analyzes content from different resource types
- **Interactive Chat**: Users can ask questions about the content in natural language
- **Multiple Resource Types**: Supports PDFs, web links, and YouTube videos
- **Gemini 2.0 Flash**: Uses the latest Gemini 2.0 Flash model for faster responses
- **Error Handling**: Robust error handling and timeout management

## Setup

1. Obtain a Gemini API key from the [Google AI Studio](https://ai.google.dev/)
2. Add your API key to the `.env` file:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```
3. Install required packages:
   ```
   pip install google-generativeai python-dotenv requests youtube-transcript-api PyPDF2
   ```

## Testing the Chatbot

The following scripts are available to test the Gemini API integration:

- `test_flash.py`: Tests the Gemini 2.0 Flash model specifically
- `test_models.py`: Tests multiple model variations
- `test_gemini.py`: Basic API connection test

Run these scripts to verify your API key is working properly:

```bash
python test_flash.py
```

## How the Chatbot Works

1. **Resource Processing**:
   - PDF files: Text is extracted using PyPDF2
   - YouTube videos: Transcripts are fetched using youtube-transcript-api
   - Web links: Content is scraped using requests

2. **Model Selection**:
   - First tries the Gemini 2.0 Flash model
   - Falls back to other model versions if needed

3. **Conversation Management**:
   - Uses Gemini's chat API to maintain context
   - Limits resource context to prevent token limits

## Troubleshooting

If you encounter issues with the chatbot:

1. Make sure your API key is valid and properly set in the `.env` file
2. Check if your API key has access to the Gemini 2.0 Flash model
3. Look for error messages in the Python console
4. Try running the testing scripts to identify specific issues
5. Check network connectivity to Google's API servers

## Timeout Handling

The chatbot implements several timeout mechanisms:
- Client-side visual indicators for long-running requests
- Server-side timeouts for API calls
- Graceful degradation with informative error messages
