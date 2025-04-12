// Main JavaScript for CryptoTravel.AI web interface

document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const chatContainer = document.getElementById('chatContainer');
    const chatToggle = document.getElementById('chatToggle');
    const generateBtn = document.getElementById('generateBtn');
    const userPrompt = document.getElementById('userPrompt');
    const loadingContainer = document.getElementById('loadingContainer');
    const resultsContainer = document.getElementById('resultsContainer');
    const resultsContent = document.getElementById('resultsContent');
    const copyBtn = document.getElementById('copyBtn');
    
    // Toggle chat visibility
    chatToggle.addEventListener('change', function() {
        chatContainer.style.display = this.checked ? 'block' : 'none';
    });
    
    // Load chat messages
    loadChatMessages();
    
    // Generate travel plan button
    generateBtn.addEventListener('click', function() {
        const prompt = userPrompt.value.trim();
        if (prompt) {
            generateTravelPlan(prompt);
        } else {
            alert('Please enter a travel request');
        }
    });
    
    // Copy button
    copyBtn.addEventListener('click', function() {
        const text = resultsContent.innerText;
        navigator.clipboard.writeText(text).then(() => {
            // Show copy notification
            copyBtn.innerHTML = '<i class="fas fa-check"></i>';
            setTimeout(() => {
                copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
            }, 2000);
        });
    });
    
    // Load chat messages from API
    async function loadChatMessages() {
        try {
            const response = await fetch('/api/chat-context');
            const data = await response.json();
            
            // Clear loading state
            chatContainer.innerHTML = '';
            
            // Render messages
            data.forEach(message => {
                const messageEl = document.createElement('div');
                messageEl.className = `chat-message message-${message.sender.toLowerCase()}`;
                
                const senderEl = document.createElement('div');
                senderEl.className = 'message-sender';
                senderEl.textContent = message.sender;
                
                const contentEl = document.createElement('div');
                contentEl.className = 'message-content';
                contentEl.textContent = message.message;
                
                const timeEl = document.createElement('div');
                timeEl.className = 'message-time';
                timeEl.textContent = message.timestamp;
                
                messageEl.appendChild(senderEl);
                messageEl.appendChild(contentEl);
                messageEl.appendChild(timeEl);
                
                chatContainer.appendChild(messageEl);
            });
            
            // Scroll to bottom
            chatContainer.scrollTop = chatContainer.scrollHeight;
            
        } catch (error) {
            console.error('Error loading chat messages:', error);
            chatContainer.innerHTML = '<p class="error-message">Failed to load chat messages. Please try again.</p>';
        }
    }
    
    // Generate travel plan
    async function generateTravelPlan(prompt) {
        // Show loading, hide results
        loadingContainer.style.display = 'block';
        resultsContainer.style.display = 'none';
        generateBtn.disabled = true;
        generateBtn.querySelector('.btn-text').textContent = 'Generating...';
        
        try {
            const response = await fetch('/api/travel-plan', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ user_input: prompt })
            });
            
            const data = await response.json();
            
            // Wait a bit for effect
            setTimeout(() => {
                // Hide loading
                loadingContainer.style.display = 'none';
                
                if (data.success) {
                    // Format and display the results
                    resultsContent.innerHTML = formatMarkdown(data.travel_plan);
                    resultsContainer.style.display = 'block';
                    
                    // Smooth scroll to results
                    resultsContainer.scrollIntoView({ behavior: 'smooth' });
                } else {
                    alert(`Error: ${data.error}`);
                }
                
                // Reset button
                generateBtn.disabled = false;
                generateBtn.querySelector('.btn-text').textContent = 'Generate Travel Plan';
            }, 3000); // 3 second delay for terminal effect
            
        } catch (error) {
            console.error('Error generating travel plan:', error);
            loadingContainer.style.display = 'none';
            alert('Failed to generate travel plan. Please try again.');
            
            // Reset button
            generateBtn.disabled = false;
            generateBtn.querySelector('.btn-text').textContent = 'Generate Travel Plan';
        }
    }
    
    // Format markdown text
    function formatMarkdown(text) {
        if (!text) return '';
        
        // Replace markdown headers
        text = text.replace(/^# (.*$)/gm, '<h1>$1</h1>');
        text = text.replace(/^## (.*$)/gm, '<h2>$1</h2>');
        text = text.replace(/^### (.*$)/gm, '<h3>$1</h3>');
        text = text.replace(/^#### (.*$)/gm, '<h4>$1</h4>');
        
        // Replace bold and italic
        text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        // Replace lists
        text = text.replace(/^\s*\d+\.\s+(.*$)/gm, '<li>$1</li>');
        text = text.replace(/^\s*\-\s+(.*$)/gm, '<li>$1</li>');
        
        // Replace paragraphs
        text = text.replace(/^(?!<[h|l])(.*$)/gm, function(m) {
            return m.trim() === '' ? '' : '<p>' + m + '</p>';
        });
        
        // Wrap lists
        text = text.replace(/<li>(.*?)<\/li>/g, function(match) {
            return '<ul>' + match + '</ul>';
        }).replace(/<\/ul><ul>/g, '');
        
        return text;
    }
});
