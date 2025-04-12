// Main JavaScript for Side Trip - Planning Your Next Side Trip

document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const dataContainer = document.getElementById('dataContainer');
    const chatContainer = document.getElementById('chatContainer');
    const emailContainer = document.getElementById('emailContainer');
    const dataToggle = document.getElementById('dataToggle');
    const chatTab = document.getElementById('chatTab');
    const emailTab = document.getElementById('emailTab');
    const generateBtn = document.getElementById('generateBtn');
    const userPrompt = document.getElementById('userPrompt');
    const loadingContainer = document.getElementById('loadingContainer');
    const resultsContainer = document.getElementById('resultsContainer');
    const resultsContent = document.getElementById('resultsContent');
    const copyBtn = document.getElementById('copyBtn');
    const micBtn = document.getElementById('micBtn');
    const recordingIndicator = document.getElementById('recordingIndicator');
    
    // Toggle data panel visibility
    dataToggle.addEventListener('change', function() {
        dataContainer.style.display = this.checked ? 'block' : 'none';
    });
    
    // Tab switching functionality
    chatTab.addEventListener('click', function() {
        switchTab('chat');
    });
    
    emailTab.addEventListener('click', function() {
        switchTab('email');
    });
    
    function switchTab(tabName) {
        // Hide all tab contents
        document.querySelectorAll('.tab-content').forEach(tab => {
            tab.classList.remove('active');
        });
        
        // Remove active class from all tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        // Show selected tab content and make its button active
        if (tabName === 'chat') {
            chatContainer.classList.add('active');
            chatTab.classList.add('active');
        } else if (tabName === 'email') {
            emailContainer.classList.add('active');
            emailTab.classList.add('active');
        }
    }
    
    // Load data sources
    loadChatMessages();
    loadEmailData();
    
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
    
    // Voice input functionality
    let mediaRecorder;
    let audioChunks = [];
    let isRecording = false;
    
    // Check if browser supports audio recording
    const hasGetUserMedia = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    
    if (!hasGetUserMedia) {
        micBtn.style.display = 'none';
        console.warn('Browser does not support audio recording');
    }
    
    // Microphone button click handler
    micBtn.addEventListener('click', function() {
        if (isRecording) {
            stopRecording();
        } else {
            startRecording();
        }
    });
    
    // Recording indicator click also stops recording
    recordingIndicator.addEventListener('click', function() {
        if (isRecording) {
            stopRecording();
        }
    });
    
    // Start audio recording
    function startRecording() {
        if (!hasGetUserMedia) return;
        
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(stream => {
                isRecording = true;
                micBtn.classList.add('recording');
                micBtn.innerHTML = '<i class="fas fa-stop"></i>';
                recordingIndicator.style.display = 'flex';
                
                // Create media recorder
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];
                
                // Handle data available event
                mediaRecorder.ondataavailable = (event) => {
                    if (event.data.size > 0) {
                        audioChunks.push(event.data);
                    }
                };
                
                // Handle recording stop
                mediaRecorder.onstop = () => {
                    // Stop all audio tracks
                    stream.getTracks().forEach(track => track.stop());
                    
                    // Process audio data
                    const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                    sendAudioToServer(audioBlob);
                };
                
                // Start recording
                mediaRecorder.start();
                
                // Auto-stop recording after 15 seconds
                setTimeout(() => {
                    if (isRecording) {
                        stopRecording();
                    }
                }, 15000); // 15 seconds max recording time
            })
            .catch(error => {
                console.error('Error accessing microphone:', error);
                alert('Could not access microphone. Please check permissions and try again.');
            });
    }
    
    // Stop audio recording
    function stopRecording() {
        if (!isRecording || !mediaRecorder) return;
        
        isRecording = false;
        micBtn.classList.remove('recording');
        micBtn.innerHTML = '<i class="fas fa-microphone"></i>';
        recordingIndicator.style.display = 'none';
        
        // Stop recording
        if (mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
        }
    }
    
    // Send audio to the server for processing
    function sendAudioToServer(audioBlob) {
        // Show a loading indicator
        userPrompt.disabled = true;
        micBtn.disabled = true;
        userPrompt.placeholder = 'Transcribing your audio...';
        
        // Create form data
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.wav');
        
        // Send to server
        fetch('/api/speech-to-text', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success && data.transcript) {
                // Set transcribed text in the textarea
                userPrompt.value = data.transcript;
            } else {
                alert(`Error transcribing audio: ${data.error || 'Unknown error'}`);
            }
        })
        .catch(error => {
            console.error('Error sending audio:', error);
            alert('Error processing audio. Please try again.');
        })
        .finally(() => {
            // Re-enable the input
            userPrompt.disabled = false;
            micBtn.disabled = false;
            userPrompt.placeholder = 'Enter your travel request here...';
            userPrompt.focus();
        });
    }
    
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
    
    // Load email data from API
    async function loadEmailData() {
        try {
            const response = await fetch('/api/email-context');
            const emails = await response.json();
            
            // Clear loading state
            emailContainer.innerHTML = '';
            
            // Render emails
            emails.forEach(email => {
                const emailEl = document.createElement('div');
                emailEl.className = 'email-message';
                
                // Email header with subject and date
                const headerEl = document.createElement('div');
                headerEl.className = 'email-header';
                
                const subjectEl = document.createElement('div');
                subjectEl.className = 'email-subject';
                subjectEl.textContent = email.subject;
                
                const dateEl = document.createElement('div');
                dateEl.className = 'email-date';
                dateEl.textContent = email.date;
                
                headerEl.appendChild(subjectEl);
                headerEl.appendChild(dateEl);
                
                // From line
                const fromEl = document.createElement('div');
                fromEl.className = 'email-from';
                fromEl.textContent = `From: ${email.sender}`;
                
                // Email content
                const contentEl = document.createElement('div');
                contentEl.className = 'email-content';
                contentEl.textContent = email.content;
                
                // Add all elements to the email container
                emailEl.appendChild(headerEl);
                emailEl.appendChild(fromEl);
                emailEl.appendChild(contentEl);
                
                emailContainer.appendChild(emailEl);
            });
            
        } catch (error) {
            console.error('Error loading email data:', error);
            emailContainer.innerHTML = '<p class="error-message">Failed to load email data. Please try again.</p>';
        }
    }
    
    // Generate travel plan
    async function generateTravelPlan(prompt) {
        // Show loading, hide results
        loadingContainer.style.display = 'block';
        resultsContainer.style.display = 'none';
        generateBtn.disabled = true;
        generateBtn.querySelector('.btn-text').textContent = 'Generating...';
        
        // Reset terminal lines to default state
        const terminalLines = document.querySelectorAll('.terminal-line');
        terminalLines.forEach((line, index) => {
            if (index === 0) {
                line.classList.add('blink');
            } else {
                line.style.visibility = 'hidden';
                line.classList.remove('blink');
            }
        });
        
        try {
            // Make the API call early but continue with the animation sequence
            const responsePromise = fetch('/api/travel-plan', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ user_input: prompt })
            });
            
            // First step: Extract from email (1.5 seconds)
            await new Promise(resolve => setTimeout(resolve, 1500));
            
            // Second step: Extract from Telegram
            terminalLines[0].classList.remove('blink');
            terminalLines[1].style.visibility = 'visible';
            terminalLines[1].classList.add('blink');
            await new Promise(resolve => setTimeout(resolve, 1500));
            
            // Third step: Generate plan
            terminalLines[1].classList.remove('blink');
            terminalLines[2].style.visibility = 'visible';
            terminalLines[2].classList.add('blink');
            
            // Now wait for the API response to complete
            const response = await responsePromise;
            const data = await response.json();
            
            // Wait a bit for effect
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            // Hide loading
            loadingContainer.style.display = 'none';
            
            if (data.success) {
                // Format and display the results as visual travel itinerary
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
            
        } catch (error) {
            console.error('Error generating travel plan:', error);
            loadingContainer.style.display = 'none';
            alert('Failed to generate travel plan. Please try again.');
            
            // Reset button
            generateBtn.disabled = false;
            generateBtn.querySelector('.btn-text').textContent = 'Generate Travel Plan';
        }
    }
    
    // Format markdown text into visual travel itinerary
    function formatMarkdown(text) {
        if (!text) return '';
        
        // Structure the output in sections
        let formattedHtml = '<div class="itinerary-container">';
        
        // Extract sections using headers
        const sections = text.split(/^#+\s+/gm);
        
        // Process each section
        sections.forEach((section, index) => {
            if (!section.trim()) return;
            
            // Extract the section title and content
            const lines = section.split('\n');
            const sectionTitle = lines[0].trim();
            const sectionContent = lines.slice(1).join('\n').trim();
            
            // Skip if empty
            if (!sectionTitle) return;
            
            // Create section container
            formattedHtml += `<div class="itinerary-section">`;
            
            // Add appropriate heading level
            const headingLevel = index === 0 ? 1 : index === 1 ? 2 : 3;
            formattedHtml += `<h${headingLevel}>${sectionTitle}</h${headingLevel}>`;
            
            // Process content based on section type
            if (sectionTitle.toLowerCase().includes('accommodation') || 
                sectionTitle.toLowerCase().includes('hotel')) {
                formattedHtml += formatAccommodationSection(sectionContent);
            } 
            else if (sectionTitle.toLowerCase().includes('restaurant') || 
                     sectionTitle.toLowerCase().includes('dining')) {
                formattedHtml += formatRestaurantSection(sectionContent);
            }
            else if (sectionTitle.toLowerCase().includes('attraction') || 
                     sectionTitle.toLowerCase().includes('sight')) {
                formattedHtml += formatAttractionSection(sectionContent);
            }
            else if (sectionTitle.toLowerCase().includes('itinerary') || 
                     sectionTitle.toLowerCase().includes('day')) {
                formattedHtml += formatItinerarySection(sectionContent);
            }
            else if (sectionTitle.toLowerCase().includes('transport')) {
                formattedHtml += formatTransportSection(sectionContent);
            }
            else if (sectionTitle.toLowerCase().includes('event') || 
                     sectionTitle.toLowerCase().includes('crypto') || 
                     sectionTitle.toLowerCase().includes('meetup')) {
                formattedHtml += formatEventSection(sectionContent);
            }
            else {
                // Default formatting for other sections
                formattedHtml += formatGeneralSection(sectionContent);
            }
            
            formattedHtml += '</div>';
        });
        
        formattedHtml += '</div>';
        return formattedHtml;
    }
    
    // Format accommodation section
    function formatAccommodationSection(content) {
        let html = '';
        const options = content.split(/\n\s*\d+\.\s+|\n\s*-\s+/g).filter(Boolean);
        
        options.forEach(option => {
            // Check if this is a valid hotel option (not just a paragraph)
            if (option.length > 20) {
                html += '<div class="hotel-card">';
                
                // Try to extract hotel name
                const hotelNameMatch = option.match(/\*\*([^*]+)\*\*/); // Find bold text for hotel name
                if (hotelNameMatch) {
                    html += `<h4>${hotelNameMatch[1]}</h4>`;
                    option = option.replace(hotelNameMatch[0], '');
                }
                
                // Try to extract price
                const priceMatch = option.match(/\$(\d+)[^\d]*per night|\$(\d+\.?\d*)[^\d]*night/);
                if (priceMatch) {
                    const price = priceMatch[1] || priceMatch[2];
                    html += `<div class="price-tag">$${price}/night</div>`;
                }
                
                // Format the rest of the content
                html += `<p>${formatBasicMarkdown(option)}</p>`;
                html += '</div>';
            } else {
                html += `<p>${formatBasicMarkdown(option)}</p>`;
            }
        });
        
        return html;
    }
    
    // Format restaurant section
    function formatRestaurantSection(content) {
        let html = '';
        const options = content.split(/\n\s*\d+\.\s+|\n\s*-\s+/g).filter(Boolean);
        
        options.forEach(option => {
            if (option.length > 20) {
                html += '<div class="restaurant-card">';
                
                // Try to extract restaurant name
                const nameMatch = option.match(/\*\*([^*]+)\*\*/); 
                if (nameMatch) {
                    html += `<h4>${nameMatch[1]}</h4>`;
                    option = option.replace(nameMatch[0], '');
                }
                
                // Format the rest of the content
                html += `<p>${formatBasicMarkdown(option)}</p>`;
                html += '</div>';
            } else {
                html += `<p>${formatBasicMarkdown(option)}</p>`;
            }
        });
        
        return html;
    }
    
    // Format attraction section
    function formatAttractionSection(content) {
        let html = '';
        const options = content.split(/\n\s*\d+\.\s+|\n\s*-\s+/g).filter(Boolean);
        
        options.forEach(option => {
            if (option.length > 20) {
                html += '<div class="attraction-card">';
                
                // Try to extract attraction name
                const nameMatch = option.match(/\*\*([^*]+)\*\*/); 
                if (nameMatch) {
                    html += `<h4>${nameMatch[1]}</h4>`;
                    option = option.replace(nameMatch[0], '');
                }
                
                // Format the rest of the content
                html += `<p>${formatBasicMarkdown(option)}</p>`;
                html += '</div>';
            } else {
                html += `<p>${formatBasicMarkdown(option)}</p>`;
            }
        });
        
        return html;
    }
    
    // Format itinerary/daily plans section
    function formatItinerarySection(content) {
        let html = '';
        
        // Split by day headers
        const dayMatches = content.match(/\n\s*\*\*Day \d+[^*]*\*\*[^\n]*/g);
        
        if (dayMatches) {
            const dayPlans = content.split(/\n\s*\*\*Day \d+[^*]*\*\*/g);
            dayPlans.shift(); // Remove the first empty part
            
            dayMatches.forEach((dayHeader, index) => {
                // Extract day number and title
                const dayTitle = dayHeader.match(/\*\*([^*]+)\*\*/)[1];
                html += `<div class="day-plan">`;
                html += `<h4>${dayTitle}</h4>`;
                
                // Format day content
                if (dayPlans[index]) {
                    html += formatBasicMarkdown(dayPlans[index]);
                }
                
                html += '</div>';
            });
        } else {
            // If no day headers, just format as a list
            html += formatGeneralSection(content);
        }
        
        return html;
    }
    
    // Format transportation section
    function formatTransportSection(content) {
        let html = '<div class="transport-options">';
        const options = content.split(/\n\s*\d+\.\s+|\n\s*-\s+/g).filter(Boolean);
        
        if (options.length > 1) {
            html += '<ul>';
            options.forEach(option => {
                html += `<li>${formatBasicMarkdown(option)}</li>`;
            });
            html += '</ul>';
        } else {
            html += formatBasicMarkdown(content);
        }
        
        html += '</div>';
        return html;
    }
    
    // Format events/meetups section
    function formatEventSection(content) {
        let html = '<div class="events-list">';
        const options = content.split(/\n\s*\d+\.\s+|\n\s*-\s+/g).filter(Boolean);
        
        if (options.length > 1) {
            options.forEach(option => {
                html += '<div class="attraction-card">';
                
                // Try to extract event name
                const nameMatch = option.match(/\*\*([^*]+)\*\*/); 
                if (nameMatch) {
                    html += `<h4>${nameMatch[1]}</h4>`;
                    option = option.replace(nameMatch[0], '');
                }
                
                html += `<p>${formatBasicMarkdown(option)}</p>`;
                html += '</div>';
            });
        } else {
            html += formatBasicMarkdown(content);
        }
        
        html += '</div>';
        return html;
    }
    
    // Format general sections
    function formatGeneralSection(content) {
        return formatBasicMarkdown(content);
    }
    
    // Basic markdown formatting for inline elements
    function formatBasicMarkdown(text) {
        if (!text) return '';
        
        // Replace bold and italic
        text = text.replace(/\*\*(.*?)\*\*/g, '<span class="highlight-text">$1</span>');
        text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        // Replace lists
        const listItems = [];
        let hasListItems = false;
        
        text = text.replace(/^\s*\d+\.\s+(.*$)/gm, function(match, item) {
            hasListItems = true;
            listItems.push(item);
            return ''; // Remove from the original text
        });
        
        text = text.replace(/^\s*-\s+(.*$)/gm, function(match, item) {
            hasListItems = true;
            listItems.push(item);
            return ''; // Remove from the original text
        });
        
        // Format paragraphs (non-list text)
        const paragraphs = text.split('\n').filter(line => line.trim() !== '');
        let html = '';
        
        paragraphs.forEach(paragraph => {
            html += `<p>${paragraph}</p>`;
        });
        
        // Add list items if any
        if (hasListItems && listItems.length > 0) {
            html += '<ul>';
            listItems.forEach(item => {
                html += `<li>${item}</li>`;
            });
            html += '</ul>';
        }
        
        return html;
    }
});
