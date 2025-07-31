// iMessage CRM Dashboard JavaScript
class Dashboard {
    constructor() {
        this.currentChatId = null;
        this.conversations = [];
        this.cachedAnalysis = {}; // Cache analysis results by chat_id
        this.previousStarters = {}; // Track previously generated starters by chat_id
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadConversations();
    }
    
    setupEventListeners() {
        // Analyze button
        document.getElementById('analyzeBtn').addEventListener('click', () => {
            if (this.currentChatId) {
                this.analyzeConversation(this.currentChatId);
            }
        });
        
        // Generate starters button
        document.getElementById('generateStarters').addEventListener('click', () => {
            this.generateStarters();
        });
        
        // Clear starter history button
        document.getElementById('clearStarterHistory').addEventListener('click', () => {
            this.clearStarterHistory();
        });
        
        // Mode toggle for starters
        document.querySelectorAll('input[name="starterMode"]').forEach(radio => {
            radio.addEventListener('change', () => {
                this.toggleStarterMode();
            });
        });
        
        // Message limit selector
        document.getElementById('messageLimit').addEventListener('change', () => {
            if (this.currentChatId) {
                this.loadMessages(this.currentChatId);
            }
        });
    }
    
    async loadConversations() {
        try {
            const response = await fetch('/api/v1/conversations');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            this.conversations = await response.json();
            this.renderConversations();
        } catch (error) {
            console.error('Error loading conversations:', error);
            this.showError('conversationList', 'Failed to load conversations');
        }
    }
    
    renderConversations() {
        const container = document.getElementById('conversationList');
        
        if (this.conversations.length === 0) {
            container.innerHTML = '<div class="loading">No conversations found</div>';
            return;
        }
        
        container.innerHTML = this.conversations.map(conv => {
            // Check if conversation has sufficient data for analysis
            const hasMetadataMessages = conv.message_count > 0;
            
            let statusIndicator, statusText, cssClass;
            
            if (conv.message_count >= 10) {
                statusIndicator = '✅';
                statusText = 'Ready for analysis';
                cssClass = '';
            } else if (hasMetadataMessages) {
                statusIndicator = '⚠️';
                statusText = 'Limited data (may affect analysis quality)';
                cssClass = 'insufficient-data';
            } else {
                statusIndicator = '❌';
                statusText = 'No messages found';
                cssClass = 'insufficient-data';
            }
            
            return `
                <div class="conversation-item ${cssClass}" data-chat-id="${conv.chat_id}">
                    <div class="conversation-name">
                        ${statusIndicator} ${conv.contact_name || this.formatContactName(conv.chat_id)}
                    </div>
                    <div class="conversation-meta">
                        ${conv.message_count} messages
                        ${conv.last_message_date ? `• ${this.formatDate(conv.last_message_date)}` : ''}
                        <br><small style="opacity: 0.7;">${statusText}</small>
                    </div>
                </div>
            `;
        }).join('');
        
        // Add click listeners
        container.querySelectorAll('.conversation-item').forEach(item => {
            item.addEventListener('click', () => {
                this.selectConversation(item.dataset.chatId);
            });
        });
    }
    
    selectConversation(chatId) {
        this.currentChatId = chatId;
        
        // Update UI state
        document.querySelectorAll('.conversation-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`[data-chat-id="${chatId}"]`).classList.add('active');
        
        // Enable analyze button
        const analyzeBtn = document.getElementById('analyzeBtn');
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = 'Analyze Conversation';
        
        // Load messages
        this.loadMessages(chatId);
        
        // Clear previous results
        document.getElementById('analysisResults').style.display = 'none';
        document.getElementById('starterResults').innerHTML = '';
        
        // Clear cached analysis and previous starters if switching to a different conversation
        if (this.currentChatId && this.currentChatId !== chatId) {
            delete this.cachedAnalysis[this.currentChatId];
            delete this.previousStarters[this.currentChatId];
        }
    }
    
    async loadMessages(chatId) {
        const container = document.getElementById('messagesContainer');
        const limitSelector = document.getElementById('messageLimit');
        const limit = limitSelector.value || 500;
        
        container.innerHTML = '<div class="loading">Loading messages...</div>';
        
        try {
            const response = await fetch(`/api/v1/conversations/${encodeURIComponent(chatId)}/messages?limit=${limit}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const messages = await response.json();
            this.renderMessages(messages);
            
            // Update the header to show message count
            const messagesHeader = document.querySelector('.column:nth-child(2) .column-header');
            const headerText = messagesHeader.childNodes[0];
            headerText.textContent = `Messages (${messages.length})`;
        } catch (error) {
            console.error('Error loading messages:', error);
            this.showError('messagesContainer', 'Failed to load messages');
        }
    }
    
    renderMessages(messages) {
        const container = document.getElementById('messagesContainer');
        
        if (messages.length === 0) {
            container.innerHTML = '<div class="loading">No messages found</div>';
            return;
        }
        
        // Keep original order (newest first) and reverse for display (oldest first)
        const sortedMessages = messages.reverse();
        
        container.innerHTML = sortedMessages.map(msg => `
            <div class="message ${msg.is_from_me ? 'from-me' : ''}">
                <div class="message-bubble">
                    ${this.renderMessageContent(msg)}
                </div>
                <div class="message-time">
                    ${msg.date ? this.formatDate(msg.date) : 'Unknown time'}
                </div>
            </div>
        `).join('');
        
        // Scroll to bottom after content is rendered - target the correct scrollable element
        requestAnimationFrame(() => {
            // The actual scrollable element is the parent column, not the messages container
            const scrollableColumn = container.parentElement;
            if (scrollableColumn) {
                scrollableColumn.scrollTop = scrollableColumn.scrollHeight;
                
                // Backup methods for maximum compatibility
                setTimeout(() => {
                    scrollableColumn.scrollTop = scrollableColumn.scrollHeight;
                    
                    // Alternative: scroll the last message into view
                    const lastMessage = container.lastElementChild;
                    if (lastMessage) {
                        lastMessage.scrollIntoView({ behavior: 'smooth', block: 'end' });
                    }
                }, 100);
            }
        });
    }
    
    async analyzeConversation(chatId) {
        const analyzeBtn = document.getElementById('analyzeBtn');
        const resultsDiv = document.getElementById('analysisResults');
        const limitSelector = document.getElementById('messageLimit');
        const limit = limitSelector.value || 500;
        
        analyzeBtn.disabled = true;
        analyzeBtn.textContent = 'Analyzing...';
        resultsDiv.style.display = 'none';
        
        try {
            const response = await fetch(`/api/v1/conversations/${encodeURIComponent(chatId)}/analyze?limit=${limit}`, {
                method: 'POST'
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            this.renderAnalysisResults(result, limit);
            
            // Cache the analysis for starter generation
            this.cachedAnalysis[chatId] = result.analysis;
            
            // Show starter form after successful analysis
            document.getElementById('starterForm').style.display = 'block';
            
        } catch (error) {
            console.error('Error analyzing conversation:', error);
            
            // Handle specific "not enough messages" error
            if (error.message.includes('400')) {
                this.showError('analysisResults', 'This conversation doesn\'t have enough messages for analysis (minimum 3 text messages required)');
            } else {
                this.showError('analysisResults', 'Failed to analyze conversation');
            }
            resultsDiv.style.display = 'block';
        } finally {
            analyzeBtn.disabled = false;
            analyzeBtn.textContent = 'Re-analyze Conversation';
        }
    }
    
    renderAnalysisResults(result, limit) {
        const container = document.getElementById('analysisResults');
        const analysis = result.analysis;
        
        container.innerHTML = `
            <div class="analysis-item">
                <span class="analysis-label">Messages Analyzed:</span> ${result.messages_analyzed} (from ${limit} loaded)
            </div>
            <div class="analysis-item">
                <span class="analysis-label">Summary:</span> ${analysis.summary || 'Not available'}
            </div>
            <div class="analysis-item">
                <span class="analysis-label">Sentiment:</span> ${analysis.sentiment_label || 'Unknown'} (${(analysis.sentiment || 0).toFixed(2)})
            </div>
            <div class="analysis-item">
                <span class="analysis-label">Topics:</span> ${(analysis.topics || []).join(', ') || 'None identified'}
            </div>
            <div class="analysis-item">
                <span class="analysis-label">Relationship:</span> ${analysis.relationship_context || 'Unknown'}
            </div>
            <div class="analysis-item">
                <span class="analysis-label">Follow-up Needed:</span> ${analysis.follow_up_needed ? 'Yes' : 'No'}
            </div>
        `;
        
        container.style.display = 'block';
    }
    
    toggleStarterMode() {
        const goalInput = document.getElementById('goalInput');
        const selectedMode = document.querySelector('input[name="starterMode"]:checked').value;
        
        if (selectedMode === 'goal') {
            goalInput.style.display = 'block';
        } else {
            goalInput.style.display = 'none';
        }
    }
    
    clearStarterHistory() {
        if (!this.currentChatId) {
            alert('Please select a conversation first');
            return;
        }
        
        // Clear the previous starters for the current conversation
        delete this.previousStarters[this.currentChatId];
        
        // Clear the results display
        document.getElementById('starterResults').innerHTML = '';
        
        // Show confirmation
        const resultsDiv = document.getElementById('starterResults');
        resultsDiv.innerHTML = '<div style="color: #28a745; padding: 1rem; background: #f8f9fa; border-radius: 6px; margin-bottom: 1rem;">✅ Starter history cleared! You\'ll get fresh starters next time.</div>';
        
        // Clear the message after 3 seconds
        setTimeout(() => {
            resultsDiv.innerHTML = '';
        }, 3000);
    }
    
    async generateStarters() {
        if (!this.currentChatId) {
            alert('Please select a conversation first');
            return;
        }
        
        const generateBtn = document.getElementById('generateStarters');
        const resultsDiv = document.getElementById('starterResults');
        const selectedMode = document.querySelector('input[name="starterMode"]:checked').value;
        const goalText = document.getElementById('goalText').value.trim();
        
        // Validate goal-driven mode
        if (selectedMode === 'goal' && !goalText) {
            alert('Please enter what you want to accomplish');
            return;
        }
        
        generateBtn.disabled = true;
        generateBtn.textContent = 'Generating...';
        resultsDiv.innerHTML = '<div class="loading">Generating message starters...</div>';
        
        try {
            const url = `/api/v1/conversations/${encodeURIComponent(this.currentChatId)}/starters`;
            
            // Get the current message limit from the dropdown
            const limitSelector = document.getElementById('messageLimit');
            const limit = limitSelector.value || 500;
            
            // Build query parameters
            const queryParams = new URLSearchParams();
            if (selectedMode === 'goal' && goalText) {
                queryParams.append('goal', goalText);
            }
            queryParams.append('limit', limit);
            
            // Check if we have cached analysis for this conversation
            const cachedAnalysis = this.cachedAnalysis[this.currentChatId];
            const previousStarters = this.previousStarters[this.currentChatId] || [];
            
            const requestBody = {};
            if (cachedAnalysis) {
                requestBody.analysis = cachedAnalysis;
            }
            if (previousStarters.length > 0) {
                requestBody.previous_starters = previousStarters;
            }
            
            const hasBody = Object.keys(requestBody).length > 0;
            const response = await fetch(`${url}?${queryParams.toString()}`, {
                method: 'POST',
                ...(hasBody && {
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(requestBody)
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            this.renderStarterResults(result);
            
            // Store the new starters to avoid them in future generations
            if (!this.previousStarters[this.currentChatId]) {
                this.previousStarters[this.currentChatId] = [];
            }
            this.previousStarters[this.currentChatId].push(...result.starters);
            
        } catch (error) {
            console.error('Error generating starters:', error);
            this.showError('starterResults', 'Failed to generate starters');
        } finally {
            generateBtn.disabled = false;
            generateBtn.textContent = 'Generate Starters';
        }
    }
    
    renderStarterResults(result) {
        const container = document.getElementById('starterResults');
        
        if (!result.starters || result.starters.length === 0) {
            container.innerHTML = '<div class="error">No starters were generated</div>';
            return;
        }
        
        const goalText = result.goal ? ` for "${result.goal}"` : ' from your conversation history';
        const cacheInfo = result.used_cached_analysis ? ' (using cached analysis)' : '';
        const previousCount = this.previousStarters[this.currentChatId] ? this.previousStarters[this.currentChatId].length - result.starters.length : 0;
        const historyInfo = previousCount > 0 ? ` (avoiding ${previousCount} previous starters)` : '';
        
        container.innerHTML = `
            <h4>Generated ${result.generated_count} Starters${goalText}${cacheInfo}${historyInfo}</h4>
            ${result.starters.map((starter, index) => `
                <div class="starter-item">
                    <div class="starter-text">${this.escapeHtml(starter)}</div>
                    <div class="starter-actions">
                        <button class="copy-btn" onclick="dashboard.copyToClipboard('${this.escapeForJs(starter)}', this)">
                            Copy
                        </button>
                    </div>
                </div>
            `).join('')}
            <button class="btn btn-secondary" onclick="dashboard.generateStarters()" style="margin-top: 1rem;">
                Generate More
            </button>
        `;
    }
    
    async copyToClipboard(text, button) {
        try {
            await navigator.clipboard.writeText(text);
            const originalText = button.textContent;
            button.textContent = 'Copied!';
            button.classList.add('copied');
            
            setTimeout(() => {
                button.textContent = originalText;
                button.classList.remove('copied');
            }, 2000);
        } catch (error) {
            console.error('Failed to copy to clipboard:', error);
            // Fallback for older browsers
            this.fallbackCopyToClipboard(text, button);
        }
    }
    
    fallbackCopyToClipboard(text, button) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        
        try {
            document.execCommand('copy');
            button.textContent = 'Copied!';
            button.classList.add('copied');
            
            setTimeout(() => {
                button.textContent = 'Copy';
                button.classList.remove('copied');
            }, 2000);
        } catch (error) {
            console.error('Fallback copy failed:', error);
        }
        
        document.body.removeChild(textArea);
    }
    
    escapeForJs(str) {
        return str.replace(/'/g, "\\'").replace(/"/g, '\\"').replace(/\n/g, '\\n');
    }
    
    getContactDisplayName(chatId) {
        // Find the contact in our conversations list
        const conversation = this.conversations.find(conv => conv.chat_id === chatId);
        if (conversation && conversation.contact_name && conversation.contact_name !== chatId) {
            return conversation.contact_name;
        }
        return this.formatContactName(chatId);
    }
    
    formatContactName(chatId) {
        if (chatId.startsWith('+')) {
            return chatId.replace('+1', '').replace(/(\d{3})(\d{3})(\d{4})/, '($1) $2-$3');
        }
        return chatId;
    }
    
    formatDate(dateStr) {
        try {
            const date = new Date(dateStr);
            return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        } catch {
            return dateStr;
        }
    }
    
    cleanMessageText(text) {
        if (!text) return 'No text content';
        
        // Clean up common encoding issues
        let cleaned = text
            // Handle various diamond character representations
            .replace(/\uE001/g, '')    // Remove Apple private use character
            .replace(/\uE002/g, '')    // Remove Apple private use character  
            .replace(/♦♦/g, '')        // Remove diamond symbols
            .replace(/♦/g, '')         // Remove single diamond
            .replace(/\uFFFD/g, '')    // Remove replacement character
            .replace(/\ufffc/g, '[📎 attachment]')  // Object replacement character
            .replace(/\u0000/g, '')    // Remove null characters
            // Clean up the kIMFileTransferGUID stuff
            .replace(/.*kIMFileTransferGUIDAttributeName.*/, '[📎 attachment]')
            .replace(/\s+/g, ' ')      // Normalize whitespace
            .trim();
        
        // If message is now empty or just weird characters, show placeholder
        if (!cleaned || cleaned.length < 2 || /^[\u0000-\u001F\u007F-\u009F]*$/.test(cleaned)) {
            return '[📎 attachment or media]';
        }
        
        // Escape HTML but preserve emojis
        const div = document.createElement('div');
        div.textContent = cleaned;
        return div.innerHTML;
    }

    renderMessageContent(msg) {
        let content = '';
        
        // Handle text content
        if (msg.text && msg.text.trim()) {
            content += this.cleanMessageText(msg.text);
        }
        
        // Handle attachment content
        if (msg.has_attachment && msg.attachment) {
            const attachmentDisplay = this.renderAttachment(msg.attachment);
            
            // If we have both text and attachment, show both
            if (content && content !== 'No text content') {
                content += '<br>' + attachmentDisplay;
            } else {
                // Just attachment, no meaningful text
                content = attachmentDisplay;
            }
        }
        
        // Fallback if no content at all
        if (!content || content.trim() === '') {
            content = msg.has_attachment ? '[📎 attachment]' : 'No text content';
        }
        
        return content;
    }

    renderAttachment(attachment) {
        if (!attachment) {
            return '[📎 attachment]';
        }
        
        const filename = attachment.filename || 'unknown file';
        const attachmentType = attachment.attachment_type || 'unknown';
        const mimeType = attachment.mime_type || '';
        
        // Type-specific icons and styling
        const typeInfo = {
            'image': { icon: '🖼️', label: 'image', class: 'attachment-image' },
            'video': { icon: '🎥', label: 'video', class: 'attachment-video' },
            'audio': { icon: '🎵', label: 'audio', class: 'attachment-audio' },
            'document': { icon: '📄', label: 'document', class: 'attachment-document' },
            'unknown': { icon: '📎', label: 'file', class: 'attachment-unknown' }
        };
        
        const info = typeInfo[attachmentType] || typeInfo['unknown'];
        
        // Create display text based on available information
        let displayText = '';
        if (filename && filename !== 'unknown file' && filename.length < 50) {
            displayText = filename;
        } else if (mimeType) {
            displayText = `${info.label} (${mimeType})`;
        } else {
            displayText = info.label;
        }
        
        return `<span class="attachment-indicator ${info.class}" title="${mimeType || 'Unknown type'}">${info.icon} ${displayText}</span>`;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    showError(containerId, message) {
        const container = document.getElementById(containerId);
        container.innerHTML = `<div class="error">${message}</div>`;
    }
}

// Initialize dashboard when page loads
let dashboard;
document.addEventListener('DOMContentLoaded', () => {
    dashboard = new Dashboard();
});