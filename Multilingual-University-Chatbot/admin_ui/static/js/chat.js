// Modern University Chatbot JavaScript

class UniversityChatbot {
    constructor() {
        this.userId = this.generateUserId();
        this.conversationId = null;
        this.currentLanguage = 'en';
        this.isTyping = false;
        this.messageHistory = [];
        
        this.initializeElements();
        this.bindEvents();
        this.loadTheme();
        this.checkConnection();
    }
    
    generateUserId() {
        return 'user_' + Math.random().toString(36).substr(2, 9);
    }
    
    initializeElements() {
        this.elements = {
            messagesContainer: document.getElementById('chat-messages'),
            messageInput: document.getElementById('message-input'),
            sendButton: document.getElementById('send-btn'),
            typingIndicator: document.getElementById('typing-indicator'),
            quickActions: document.getElementById('quick-actions'),
            themeToggle: document.getElementById('theme-toggle'),
            languageButtons: document.querySelectorAll('.language-btn'),
            botStatus: document.getElementById('bot-status'),
            connectionToast: document.getElementById('connection-toast'),
            connectionMessage: document.getElementById('connection-message')
        };
    }
    
    bindEvents() {
        // Send message on button click
        this.elements.sendButton.addEventListener('click', () => this.sendMessage());
        
        // Send message on Enter (but not Shift+Enter)
        this.elements.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Auto-resize textarea
        this.elements.messageInput.addEventListener('input', () => this.autoResize());
        
        // Quick action buttons
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('quick-action-btn') || 
                e.target.closest('.quick-action-btn')) {
                const btn = e.target.classList.contains('quick-action-btn') ? 
                    e.target : e.target.closest('.quick-action-btn');
                const message = btn.dataset.message;
                if (message) {
                    this.elements.messageInput.value = message;
                    this.sendMessage();
                }
            }
        });
        
        // Language toggle
        this.elements.languageButtons.forEach(btn => {
            btn.addEventListener('click', () => this.switchLanguage(btn.dataset.lang));
        });
        
        // Theme toggle
        this.elements.themeToggle.addEventListener('click', () => this.toggleTheme());
        
        // Hide quick actions when user starts typing
        this.elements.messageInput.addEventListener('focus', () => {
            this.elements.quickActions.style.display = 'none';
        });
    }
    
    autoResize() {
        const textarea = this.elements.messageInput;
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }
    
    async sendMessage() {
        const message = this.elements.messageInput.value.trim();
        if (!message || this.isTyping) return;
        
        // Add user message to UI
        this.addMessage({
            type: 'user',
            content: message,
            timestamp: new Date()
        });
        
        // Clear input and show typing
        this.elements.messageInput.value = '';
        this.autoResize();
        this.showTyping();
        
        // Hide quick actions after first message
        this.elements.quickActions.style.display = 'none';
        
        try {
            const response = await this.callChatAPI(message);
            this.hideTyping();
            
            // Add bot response
            this.addMessage({
                type: 'bot',
                content: response.response,
                timestamp: new Date(),
                pipeline: response.pipeline_used,
                language: response.language
            });
            
            // Update conversation ID
            if (response.conversation_id) {
                this.conversationId = response.conversation_id;
            }
            
            // Update status
            this.updateBotStatus('Online • Ready to help');
            
        } catch (error) {
            this.hideTyping();
            console.error('Chat error:', error);
            
            this.addMessage({
                type: 'bot',
                content: 'I\'m experiencing technical difficulties. Please try again in a moment.',
                timestamp: new Date(),
                pipeline: 'error',
                isError: true
            });
            
            this.updateBotStatus('Connection issues');
            this.showConnectionToast('Connection error. Please check your internet.', 'error');
        }
    }
    
    async callChatAPI(message) {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: this.userId,
                message: message,
                conversation_id: this.conversationId,
                language: this.currentLanguage
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        return await response.json();
    }
    
    addMessage(message) {
        this.messageHistory.push(message);
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `${message.type}-message fade-in`;
        
        const timestamp = this.formatTime(message.timestamp);
        const avatar = message.type === 'user' ? 
            '<i class="fas fa-user"></i>' : 
            '<i class="fas fa-graduation-cap"></i>';
        
        let pipelineBadge = '';
        if (message.pipeline) {
            const badgeClass = message.isError ? 'error' : message.pipeline;
            pipelineBadge = `<span class="pipeline-badge ${badgeClass}">${message.pipeline}</span>`;
        }
        
        messageDiv.innerHTML = `
            <div class="message-avatar">
                ${avatar}
            </div>
            <div class="message-content">
                <div class="message-bubble ${message.type} ${message.isError ? 'error-message' : ''}">
                    ${this.formatMessageContent(message.content)}
                </div>
                <div class="message-time">
                    ${message.type === 'bot' ? pipelineBadge : ''}
                    <span>${timestamp}</span>
                </div>
            </div>
        `;
        
        this.elements.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    formatMessageContent(content) {
        // Convert markdown-like formatting
        return content
            .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            .replace(/\*([^*]+)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>');
    }
    
    formatTime(date) {
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
        
        return date.toLocaleDateString();
    }
    
    showTyping() {
        this.isTyping = true;
        this.elements.typingIndicator.style.display = 'flex';
        this.elements.sendButton.classList.add('loading');
        this.updateBotStatus('Typing...');
        this.scrollToBottom();
    }
    
    hideTyping() {
        this.isTyping = false;
        this.elements.typingIndicator.style.display = 'none';
        this.elements.sendButton.classList.remove('loading');
    }
    
    updateBotStatus(status) {
        this.elements.botStatus.textContent = status;
    }
    
    scrollToBottom() {
        setTimeout(() => {
            this.elements.messagesContainer.scrollTop = this.elements.messagesContainer.scrollHeight;
        }, 100);
    }
    
    switchLanguage(lang) {
        this.currentLanguage = lang;
        
        // Update button states
        this.elements.languageButtons.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.lang === lang);
        });
        
        // Update placeholder text
        const placeholders = {
            'en': 'Type your question here... (Press Enter to send)',
            'hi': 'यहाँ अपना प्रश्न लिखें... (भेजने के लिए Enter दबाएं)'
        };
        
        this.elements.messageInput.placeholder = placeholders[lang] || placeholders['en'];
        
        // Show language change notification
        this.showConnectionToast(`Switched to ${lang === 'hi' ? 'Hindi' : 'English'}`, 'info');
    }
    
    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('chat-theme', newTheme);
        
        // Update theme toggle icon
        const icon = this.elements.themeToggle.querySelector('i');
        icon.className = newTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }
    
    loadTheme() {
        const savedTheme = localStorage.getItem('chat-theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
        
        const icon = this.elements.themeToggle.querySelector('i');
        icon.className = savedTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }
    
    async checkConnection() {
        try {
            const response = await fetch('/health');
            if (response.ok) {
                this.showConnectionToast('Connected to chatbot server', 'success');
            } else {
                throw new Error('Server error');
            }
        } catch (error) {
            this.showConnectionToast('Unable to connect to server', 'error');
        }
    }
    
    showConnectionToast(message, type = 'info') {
        this.elements.connectionMessage.textContent = message;
        
        const toast = new bootstrap.Toast(this.elements.connectionToast, {
            delay: 3000
        });
        
        // Update toast styling based on type
        const toastHeader = this.elements.connectionToast.querySelector('.toast-header');
        toastHeader.className = `toast-header bg-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'} text-white`;
        
        toast.show();
    }
}

// Initialize chatbot when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.chatbot = new UniversityChatbot();
});

// Service Worker for offline functionality (optional)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/sw.js')
            .then(registration => console.log('SW registered'))
            .catch(error => console.log('SW registration failed'));
    });
}
