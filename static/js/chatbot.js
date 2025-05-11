// Chatbot functionality for NestCircle
document.addEventListener('DOMContentLoaded', function() {
    let currentResourceId = null;
    let chatSessionId = null;
    let chatbotInitialized = false;

    // Create chatbot elements if we're on a resource page
    function createChatbotElements() {
        // Only initialize on resource pages
        const resourceIdElement = document.getElementById('resource-id');
        if (!resourceIdElement) return;
        
        currentResourceId = resourceIdElement.value;
        if (!currentResourceId) return;

        // Create chatbot button
        const chatbotButton = document.createElement('div');
        chatbotButton.className = 'chatbot-button';
        chatbotButton.innerHTML = '<i class="fas fa-robot"></i>';
        chatbotButton.title = 'Ask AI about this resource';
        document.body.appendChild(chatbotButton);

        // Create chatbot window
        const chatbotWindow = document.createElement('div');
        chatbotWindow.className = 'chatbot-window';
        chatbotWindow.innerHTML = `
            <div class="chatbot-header">
                <h5 class="mb-0">NestCircle AI Assistant</h5>
                <button class="chatbot-close">&times;</button>
            </div>
            <div class="chatbot-messages" id="chatbot-messages">
                <div class="chat-message bot-message">
                    Hello! I can help you understand this resource better. What would you like to know?
                </div>
            </div>
            <div class="chatbot-input">
                <input type="text" placeholder="Ask something about this resource..." id="chatbot-input-field">
                <button id="chatbot-send-btn"><i class="fas fa-paper-plane"></i></button>
            </div>
        `;
        document.body.appendChild(chatbotWindow);

        // Add event listeners
        chatbotButton.addEventListener('click', toggleChatbot);
        document.querySelector('.chatbot-close').addEventListener('click', toggleChatbot);
        
        const sendButton = document.getElementById('chatbot-send-btn');
        const inputField = document.getElementById('chatbot-input-field');
        
        sendButton.addEventListener('click', sendMessage);
        inputField.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    }

    function toggleChatbot() {
        const chatbotWindow = document.querySelector('.chatbot-window');
        chatbotWindow.classList.toggle('active');
        
        // Initialize chatbot session if not already done
        if (chatbotWindow.classList.contains('active') && !chatbotInitialized) {
            initializeChatbot();
        }

        // Focus on input field when opening
        if (chatbotWindow.classList.contains('active')) {
            document.getElementById('chatbot-input-field').focus();
        }
    }

    function initializeChatbot() {
        const messageContainer = document.getElementById('chatbot-messages');
        
        // Show loading message
        const loadingMessage = document.createElement('div');
        loadingMessage.className = 'chat-message bot-message chatbot-loading';
        loadingMessage.innerHTML = `
            <div class="typing-indicator">
                <span></span><span></span><span></span>
            </div>
        `;
        messageContainer.appendChild(loadingMessage);
        
        // Set timeout to add warning if response takes too long
        const timeoutWarning = setTimeout(() => {
            loadingMessage.classList.add('timeout-warning');
        }, 8000); // Show warning after 8 seconds
        
        // Scroll to bottom
        messageContainer.scrollTop = messageContainer.scrollHeight;
        
        // Call API to initialize chatbot with resource content
        fetch(`/api/chatbot/init/${currentResourceId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            // Clear timeout
            clearTimeout(timeoutWarning);
            
            // Remove loading message
            messageContainer.removeChild(loadingMessage);
            
            if (data.success) {
                chatSessionId = data.session_id;
                chatbotInitialized = true;
                
                // Add message about resource type and model
                let resourceTypeMessage = '';
                switch(data.resource_type) {
                    case 'pdf':
                        resourceTypeMessage = "I've analyzed the PDF document. What would you like to know about it?";
                        break;
                    case 'youtube':
                        resourceTypeMessage = "I've analyzed the YouTube video transcript. What would you like to know about it?";
                        break;
                    case 'link':
                        resourceTypeMessage = "I've analyzed the web content. What would you like to know about it?";
                        break;
                    default:
                        resourceTypeMessage = "I've analyzed the resource. What would you like to know about it?";
                }
                
                const typeMessage = document.createElement('div');
                typeMessage.className = 'chat-message bot-message';
                typeMessage.textContent = resourceTypeMessage;
                messageContainer.appendChild(typeMessage);
                
                // If the model info is available, show which model is being used
                if (data.model) {
                    const modelMessage = document.createElement('div');
                    modelMessage.className = 'chat-message bot-message model-info';
                    modelMessage.innerHTML = `<small>Using ${data.model}</small>`;
                    messageContainer.appendChild(modelMessage);
                }
                
                // Scroll to bottom
                messageContainer.scrollTop = messageContainer.scrollHeight;
            } else {
                // Display specific error from the server if available
                const errorMsg = data.error || "Sorry, I couldn't analyze this resource. Please try again later.";
                
                const errorMessage = document.createElement('div');
                errorMessage.className = 'chat-message bot-message error-message';
                errorMessage.textContent = errorMsg;
                messageContainer.appendChild(errorMessage);
                
                // Add configuration hint if it's an API key issue
                if (errorMsg.includes("API key")) {
                    const configHint = document.createElement('div');
                    configHint.className = 'chat-message bot-message hint-message';
                    configHint.innerHTML = "It looks like the AI service is not configured properly. " +
                        "Please make sure you have set up a valid Gemini API key in the server's .env file.";
                    messageContainer.appendChild(configHint);
                }
            }
        })
        .catch(error => {
            // Clear timeout
            clearTimeout(timeoutWarning);
            
            // Remove loading message
            messageContainer.removeChild(loadingMessage);
            
            console.error('Error initializing chatbot:', error);
            const errorMessage = document.createElement('div');
            errorMessage.className = 'chat-message bot-message error-message';
            errorMessage.textContent = "Sorry, there was an error connecting to the AI assistant. Please try again later.";
            messageContainer.appendChild(errorMessage);
            
            // Scroll to bottom
            messageContainer.scrollTop = messageContainer.scrollHeight;
        });
    }

    function sendMessage() {
        const inputField = document.getElementById('chatbot-input-field');
        const messageContainer = document.getElementById('chatbot-messages');
        const userMessage = inputField.value.trim();
        
        if (!userMessage || !chatSessionId) return;
        
        // Add user message to chat
        const userMessageElement = document.createElement('div');
        userMessageElement.className = 'chat-message user-message';
        userMessageElement.textContent = userMessage;
        messageContainer.appendChild(userMessageElement);
        
        // Clear input field
        inputField.value = '';
        
        // Show loading indicator
        const loadingMessage = document.createElement('div');
        loadingMessage.className = 'chat-message bot-message chatbot-loading';
        loadingMessage.innerHTML = `
            <div class="typing-indicator">
                <span></span><span></span><span></span>
            </div>
        `;
        messageContainer.appendChild(loadingMessage);
        
        // Set timeout to add warning if response takes too long
        const timeoutWarning = setTimeout(() => {
            loadingMessage.classList.add('timeout-warning');
        }, 8000); // Show warning after 8 seconds
        
        // Scroll to bottom
        messageContainer.scrollTop = messageContainer.scrollHeight;
        
        // Send message to server
        fetch('/api/chatbot/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_id: chatSessionId,
                prompt: userMessage
            })
        })
        .then(response => response.json())
        .then(data => {
            // Clear timeout
            clearTimeout(timeoutWarning);
            
            // Remove loading indicator
            messageContainer.removeChild(loadingMessage);
            
            if (data.success) {
                // Format response with markdown
                const formattedResponse = formatBotResponse(data.response);
                
                // Add bot response to chat
                const botMessageElement = document.createElement('div');
                botMessageElement.className = 'chat-message bot-message';
                botMessageElement.innerHTML = formattedResponse;
                messageContainer.appendChild(botMessageElement);
            } else {
                // Display specific error message from server
                const errorMsg = data.error || "Sorry, I couldn't process your request. Please try again.";
                
                const errorMessage = document.createElement('div');
                errorMessage.className = 'chat-message bot-message error-message';
                errorMessage.textContent = errorMsg;
                messageContainer.appendChild(errorMessage);
                
                // Show retry suggestion if it looks like a temporary error
                if (errorMsg.includes("encountered an error") || errorMsg.includes("try again")) {
                    const retryMessage = document.createElement('div');
                    retryMessage.className = 'chat-message bot-message hint-message';
                    retryMessage.textContent = "This might be a temporary issue. You can try asking again in a moment.";
                    messageContainer.appendChild(retryMessage);
                }
                
                // Add configuration hint if it's an API key issue
                if (errorMsg.includes("API key")) {
                    const configHint = document.createElement('div');
                    configHint.className = 'chat-message bot-message hint-message';
                    configHint.innerHTML = "It looks like the AI service is not configured properly. " +
                        "Please make sure you have set up a valid Gemini API key in the server's .env file.";
                    messageContainer.appendChild(configHint);
                }
            }
            
            // Scroll to bottom
            messageContainer.scrollTop = messageContainer.scrollHeight;
        })
        .catch(error => {
            // Clear timeout
            clearTimeout(timeoutWarning);
            
            // Remove loading indicator
            messageContainer.removeChild(loadingMessage);
            
            console.error('Error sending message:', error);
            const errorMessage = document.createElement('div');
            errorMessage.className = 'chat-message bot-message error-message';
            errorMessage.textContent = "Sorry, there was an error processing your message. Please try again.";
            messageContainer.appendChild(errorMessage);
            
            // Scroll to bottom
            messageContainer.scrollTop = messageContainer.scrollHeight;
        });
    }

    // Helper function to format bot responses with code blocks and basic markdown
    function formatBotResponse(text) {
        // Handle code blocks
        let formattedText = text.replace(/```([^`]+)```/g, function(match, code) {
            return `<pre>${code}</pre>`;
        });
        
        // Handle bold text
        formattedText = formattedText.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        
        // Handle italics
        formattedText = formattedText.replace(/\*([^*]+)\*/g, '<em>$1</em>');
        
        // Handle line breaks
        formattedText = formattedText.replace(/\n/g, '<br>');
        
        return formattedText;
    }

    // Initialize chatbot elements
    createChatbotElements();
});
