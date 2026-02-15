class Chatbot {
    constructor() {
        this.chatWidget = document.getElementById('chat-widget');
        this.toggleBtn = document.getElementById('chat-toggle-btn');
        this.closeBtn = document.getElementById('chat-close-btn');
        this.sendBtn = document.getElementById('chat-send-btn');
        this.inputField = document.getElementById('chat-input');
        this.messagesContainer = document.getElementById('chat-messages');
        this.typingIndicator = document.getElementById('typing-indicator');

        this.isOpen = false;
        this.isTyping = false;

        this.init();
    }

    init() {
        // Event Listeners
        this.toggleBtn.addEventListener('click', () => this.toggleChat());
        this.closeBtn.addEventListener('click', () => this.toggleChat());
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.inputField.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });

        // Initial Greeting
        setTimeout(() => {
            if (this.messagesContainer.children.length === 0) {
                this.addMessage("Hello! I am PriorityMed AI. I can help assess your symptoms and guide you to the right department. How are you feeling today?", 'bot');
            }
        }, 1000);
    }

    toggleChat() {
        this.isOpen = !this.isOpen;
        if (this.isOpen) {
            this.chatWidget.classList.add('active');
            this.toggleBtn.classList.add('hidden');
            this.inputField.focus();
        } else {
            this.chatWidget.classList.remove('active');
            this.toggleBtn.classList.remove('hidden');
        }
    }

    async sendMessage() {
        const text = this.inputField.value.trim();
        if (!text) return;

        // Add user message
        this.addMessage(text, 'user');
        this.inputField.value = '';

        // Show typing indicator
        this.showTyping();

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message: text })
            });

            const data = await response.json();

            // Simulation of thinking delay for realism
            setTimeout(() => {
                this.hideTyping();
                this.addMessage(data.response, 'bot');
            }, 1000);

        } catch (error) {
            console.error('Error:', error);
            this.hideTyping();
            this.addMessage("I apologize, but I'm having trouble connecting to my triage engine right now. Please try again.", 'bot');
        }
    }

    addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender);

        // Parse markdown-like bolding
        const formattedText = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');

        messageDiv.innerHTML = formattedText;
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    showTyping() {
        this.typingIndicator.style.display = 'flex';
        this.scrollToBottom();
    }

    hideTyping() {
        this.typingIndicator.style.display = 'none';
    }

    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }
}

// Initialize Chatbot when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new Chatbot();
});
