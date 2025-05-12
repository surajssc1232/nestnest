// Chatbot functionality for NestCircle
document.addEventListener('DOMContentLoaded', function() {
    let currentResourceId = null;
    let chatSessionId = null;
    let chatbotInitialized = false;
    let isFullscreen = false;
    
    // Available slash commands
    const slashCommands = [
        { command: '/summarize', description: 'Summarize the content' },
        { command: '/quiz', description: 'Generate a quiz based on content' },
        { command: '/help', description: 'Show available commands' }
    ];

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
                <div class="chatbot-controls">
                    <button class="chatbot-fullscreen" title="Toggle fullscreen"><i class="fas fa-expand"></i></button>
                    <button class="chatbot-close" title="Close">&times;</button>
                </div>
            </div>
            <div class="chatbot-messages" id="chatbot-messages">
                <div class="chat-message bot-message">
                    Hello! I can help you understand this resource better. What would you like to know?
                </div>
                <div class="chat-message bot-message hint-message">
                    <strong>Pro tip:</strong> Try special commands:
                    <br><code>/summarize</code> - Summarize the content
                    <br><code>/quiz [options]</code> - Generate a quiz (e.g., '/quiz make 5 questions about chapter 2')
                    <br><code>/help</code> - Show available commands
                </div>
            </div>
            <div class="command-suggestions" id="command-suggestions" style="display: none;"></div>
            <div class="chatbot-input">
                <input type="text" placeholder="Ask something or use /commands..." id="chatbot-input-field">
                <button id="chatbot-send-btn"><i class="fas fa-paper-plane"></i></button>
            </div>
        `;
        document.body.appendChild(chatbotWindow);

        // Add event listeners
        chatbotButton.addEventListener('click', toggleChatbot);
        document.querySelector('.chatbot-close').addEventListener('click', toggleChatbot);
        document.querySelector('.chatbot-fullscreen').addEventListener('click', toggleFullscreen);
        
        const sendButton = document.getElementById('chatbot-send-btn');
        const inputField = document.getElementById('chatbot-input-field');
        const commandSuggestions = document.getElementById('command-suggestions');
        
        sendButton.addEventListener('click', function() {
            handleUserInput();
        });
        
        inputField.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                handleUserInput();
            }
        });
        
        // Add event listeners for slash command suggestions
        inputField.addEventListener('input', function() {
            const value = this.value.trim();
            
            // Hide command suggestions if not starting with /
            if (!value.startsWith('/')) {
                commandSuggestions.style.display = 'none';
                return;
            }
            
            // Show command suggestions
            showCommandSuggestions(value);
        });
        
        // Handle clicking a suggestion
        commandSuggestions.addEventListener('click', function(e) {
            if (e.target.classList.contains('command-suggestion')) {
                inputField.value = e.target.dataset.command;
                commandSuggestions.style.display = 'none';
                inputField.focus();
            }
        });
        
        // Close suggestions when clicking outside
        document.addEventListener('click', function(e) {
            if (e.target !== inputField && e.target !== commandSuggestions) {
                commandSuggestions.style.display = 'none';
            }
        });
        
        // Handle keyboard navigation for suggestions
        inputField.addEventListener('keydown', function(e) {
            if (commandSuggestions.style.display === 'none') return;
            
            const suggestionItems = commandSuggestions.querySelectorAll('.command-suggestion');
            if (!suggestionItems.length) return;
            
            // Get the currently highlighted item
            const highlighted = commandSuggestions.querySelector('.highlighted');
            let index = -1;
            
            if (highlighted) {
                for (let i = 0; i < suggestionItems.length; i++) {
                    if (suggestionItems[i] === highlighted) {
                        index = i;
                        break;
                    }
                }
            }
            
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                const nextIndex = (index + 1) % suggestionItems.length;
                if (highlighted) highlighted.classList.remove('highlighted');
                suggestionItems[nextIndex].classList.add('highlighted');
                
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                const prevIndex = index < 0 ? suggestionItems.length - 1 : (index - 1 + suggestionItems.length) % suggestionItems.length;
                if (highlighted) highlighted.classList.remove('highlighted');
                suggestionItems[prevIndex].classList.add('highlighted');
                
            } else if (e.key === 'Tab') {
                e.preventDefault();
                if (highlighted) {
                    inputField.value = highlighted.dataset.command;
                    commandSuggestions.style.display = 'none';
                } else if (suggestionItems.length) {
                    inputField.value = suggestionItems[0].dataset.command;
                    commandSuggestions.style.display = 'none';
                }
            }
        });
    }
    
    // Show command suggestions based on input
    function showCommandSuggestions(input) {
        const commandSuggestions = document.getElementById('command-suggestions');
        const matchingCommands = slashCommands.filter(cmd => 
            cmd.command.startsWith(input) || input === '/'
        );
        
        if (!matchingCommands.length) {
            commandSuggestions.style.display = 'none';
            return;
        }
        
        commandSuggestions.innerHTML = '';
        
        // Create suggestion elements
        matchingCommands.forEach(cmd => {
            const suggestion = document.createElement('div');
            suggestion.className = 'command-suggestion';
            suggestion.dataset.command = cmd.command;
            suggestion.innerHTML = `<strong>${cmd.command}</strong> - ${cmd.description}`;
            commandSuggestions.appendChild(suggestion);
        });
        
        commandSuggestions.style.display = 'block';
    }
    
    // Toggle fullscreen mode
    function toggleFullscreen() {
        const chatbotWindow = document.querySelector('.chatbot-window');
        const fullscreenButton = document.querySelector('.chatbot-fullscreen i');
        
        isFullscreen = !isFullscreen;
        
        if (isFullscreen) {
            chatbotWindow.classList.add('fullscreen');
            fullscreenButton.classList.remove('fa-expand');
            fullscreenButton.classList.add('fa-compress');
        } else {
            chatbotWindow.classList.remove('fullscreen');
            fullscreenButton.classList.remove('fa-compress');
            fullscreenButton.classList.add('fa-expand');
        }
        
        // Scroll to bottom after resize
        const messageContainer = document.getElementById('chatbot-messages');
        messageContainer.scrollTop = messageContainer.scrollHeight;
    }

    function toggleChatbot() {
        const chatbotWindow = document.querySelector('.chatbot-window');
        chatbotWindow.classList.toggle('active');
        
        // Reset fullscreen when closing
        if (!chatbotWindow.classList.contains('active') && isFullscreen) {
            toggleFullscreen();
        }
        
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

    // Handle special commands and regular messages
    function handleUserInput() {
        const inputField = document.getElementById('chatbot-input-field');
        const commandSuggestions = document.getElementById('command-suggestions');
        const userMessage = inputField.value.trim();
        
        if (!userMessage || !chatSessionId) return;
        
        // Hide command suggestions if visible
        commandSuggestions.style.display = 'none';
        
        // Handle help command
        if (userMessage === '/help') {
            // Create a help message without sending to the server
            displayHelpMessage();
            inputField.value = '';
            return;
        }
        
        // Check for special commands
        if (userMessage.startsWith('/summarize')) {
            // Extract any additional parameters after /summarize
            const params = userMessage.substring('/summarize'.length).trim();
            let prompt = "Please summarize the main points of this content";
            
            if (params) {
                prompt += " with focus on " + params;
            }
            
            sendMessage(userMessage, prompt);
        } 
        else if (userMessage.startsWith('/quiz')) {
            // Extract parameters after /quiz
            const params = userMessage.substring('/quiz'.length).trim();
            
            if (params) {
                // Use the parameters provided by the user
                sendMessage(userMessage, "Please generate a quiz based on this content: " + params);
            } else {
                // Default quiz request
                sendMessage(userMessage, "Please generate a quiz with 5 questions based on this content.");
            }
        }
        else {
            // Regular message
            sendMessage(userMessage);
        }
    }
    
    // Display help message with available commands
    function displayHelpMessage() {
        const messageContainer = document.getElementById('chatbot-messages');
        
        // Add user message to chat
        const userMessageElement = document.createElement('div');
        userMessageElement.className = 'chat-message user-message';
        userMessageElement.textContent = '/help';
        messageContainer.appendChild(userMessageElement);
        
        // Add help message
        const helpMessage = document.createElement('div');
        helpMessage.className = 'chat-message bot-message';
        helpMessage.innerHTML = `
            <strong>Available Commands:</strong><br>
            <code>/summarize [focus]</code> - Summarize the content, optionally with a specific focus<br>
            <code>/quiz [options]</code> - Generate a quiz based on the content<br>
            Examples:<br>
            <code>/summarize key concepts</code> - Summarize focusing on key concepts<br>
            <code>/quiz make 10 multiple choice questions about chapter 3</code> - Create a specific quiz
        `;
        messageContainer.appendChild(helpMessage);
        
        // Scroll to bottom
        messageContainer.scrollTop = messageContainer.scrollHeight;
    }

    function sendMessage(userMessage, processedMessage = null) {
        const messageContainer = document.getElementById('chatbot-messages');
        const inputField = document.getElementById('chatbot-input-field');
        
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
        
        // Use processed message if provided, otherwise use original message
        const messageToSend = processedMessage || userMessage;
        
        // Send message to server
        fetch('/api/chatbot/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_id: chatSessionId,
                prompt: messageToSend
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
        
        // Handle inline code
        formattedText = formattedText.replace(/`([^`]+)`/g, function(match, code) {
            return `<code>${code}</code>`;
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
