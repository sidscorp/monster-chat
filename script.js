class ChatApp {
    constructor() {
        this.messages = [];
        this.currentModel = '';
        this.isTyping = false;
        this.allModels = [];
        this.categories = [];
        this.currentPriceFilter = 'all';
        this.currentCategoryFilter = 'all';
        this.useStreaming = true;
        this.currentStreamingMessage = null;
        this.activeTab = 'chat';
        
        this.initializeElements();
        this.attachEventListeners();
        this.initializeUI();
        this.loadModels();
    }

    initializeElements() {
        this.chatMessages = document.getElementById('chat-messages');
        this.chatInput = document.getElementById('chat-input');
        this.sendBtn = document.getElementById('send-btn');
        this.modelSelect = document.getElementById('model-select');
        this.clearBtn = document.getElementById('clear-chat');
        this.tokenCount = document.getElementById('token-count');
        this.status = document.getElementById('status');
        this.loadingOverlay = document.getElementById('loading-overlay');
        this.modelInfo = document.getElementById('model-info');
        this.priceFilter = document.getElementById('price-filter');
        this.categoryFilter = document.getElementById('category-filter');
        this.modelControlsSection = document.getElementById('model-controls-section');
        this.tabButtons = document.querySelectorAll('.tab-btn');
        this.tabPanels = document.querySelectorAll('.tab-panel');
        
        // Debug logging
        console.log('Price filter element:', this.priceFilter);
        console.log('Category filter element:', this.categoryFilter);
        console.log('Model controls section:', this.modelControlsSection);
        
        // Test if elements are clickable
        if (this.priceFilter) {
            this.priceFilter.onclick = () => console.log('Price filter clicked!');
        }
        if (this.categoryFilter) {
            this.categoryFilter.onclick = () => console.log('Category filter clicked!');
        }
    }

    attachEventListeners() {
        // Send message with debounce
        this.sendBtn.addEventListener('click', () => {
            if (!this.isTyping) {
                this.sendMessage();
            }
        });
        
        // Enter to send, Shift+Enter for new line
        this.chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey && !this.isTyping) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Auto-resize textarea
        this.chatInput.addEventListener('input', () => {
            this.autoResizeTextarea();
            this.updateTokenCount();
            this.updateSendButton();
        });

        // Model selection
        this.modelSelect.addEventListener('change', () => {
            this.currentModel = this.modelSelect.value;
            this.updateModelInfo();
            this.updateSendButton();
        });

        // Clear chat
        this.clearBtn.addEventListener('click', () => this.clearChat());

        // Price filter
        if (this.priceFilter) {
            this.priceFilter.addEventListener('change', () => {
                this.currentPriceFilter = this.priceFilter.value;
                this.populateModelSelect();
            });
        }

        // Category filter
        if (this.categoryFilter) {
            this.categoryFilter.addEventListener('change', () => {
                this.currentCategoryFilter = this.categoryFilter.value;
                this.populateModelSelect();
            });
        }

        // Tab switching
        if (this.tabButtons) {
            this.tabButtons.forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const tabName = e.target.closest('.tab-btn').dataset.tab;
                    this.switchTab(tabName);
                });
            });
        }
    }

    initializeUI() {
        // Ensure we start on the chat tab with model controls visible
        if (this.modelControlsSection) {
            this.modelControlsSection.style.display = 'block';
        }
        
        // Set active tab button
        if (this.tabButtons) {
            this.tabButtons.forEach(btn => {
                btn.classList.toggle('active', btn.dataset.tab === 'chat');
            });
        }
        
        // Set active tab panel
        if (this.tabPanels) {
            this.tabPanels.forEach(panel => {
                panel.classList.toggle('active', panel.id === 'chat-tab');
            });
        }
    }

    switchTab(tabName) {
        // Update active tab button
        this.tabButtons.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });

        // Update active tab panel
        this.tabPanels.forEach(panel => {
            panel.classList.toggle('active', panel.id === `${tabName}-tab`);
        });

        // Show/hide model controls based on tab
        if (this.modelControlsSection) {
            if (tabName === 'chat') {
                this.modelControlsSection.style.display = 'block';
            } else {
                this.modelControlsSection.style.display = 'none';
            }
        }

        this.activeTab = tabName;
    }

    async loadModels() {
        try {
            this.updateStatus('🧬 Awakening creatures...', 'thinking');
            
            // Load models and categories in parallel
            const [modelsResponse, categoriesResponse] = await Promise.all([
                fetch('/api/models?price=all&category=all'),
                fetch('/api/categories')
            ]);
            
            const modelsData = await modelsResponse.json();
            const categoriesData = await categoriesResponse.json();
            
            if (modelsData.success && categoriesData.success) {
                this.allModels = modelsData.models;
                this.categories = categoriesData.categories;
                this.populateCategoryFilter();
                this.populateModelSelect();
                this.updateStatus(`🎉 Lab ready! ${modelsData.count} creatures awakened!`, 'ready');
            } else {
                throw new Error(modelsData.error || categoriesData.error || 'Failed to awaken creatures');
            }
        } catch (error) {
            console.error('Error loading models:', error);
            this.updateStatus('⚠️ Creature revival failed', 'error');
            this.showFallbackModels();
        }
    }

    populateCategoryFilter() {
        this.categoryFilter.innerHTML = '<option value="all">All Categories</option>';
        
        this.categories.forEach(category => {
            const option = document.createElement('option');
            option.value = category.value;
            option.textContent = category.label;
            this.categoryFilter.appendChild(option);
        });
    }

    populateModelSelect() {
        this.modelSelect.innerHTML = '<option value="">🔬 Choose your creature...</option>';
        
        // Filter models based on current filters
        const filteredModels = this.allModels.filter(model => {
            // Price filter
            if (this.currentPriceFilter === 'free' && !model.pricing?.is_free) return false;
            if (this.currentPriceFilter === 'paid' && model.pricing?.is_free) return false;
            
            // Category filter
            if (this.currentCategoryFilter !== 'all') {
                const categories = model.categories || [];
                if (!categories.includes(this.currentCategoryFilter)) return false;
            }
            
            return true;
        });
        
        // Group models by provider
        const groupedModels = this.groupModelsByProvider(filteredModels);
        
        Object.keys(groupedModels).forEach(provider => {
            const optgroup = document.createElement('optgroup');
            optgroup.label = this.formatProviderName(provider);
            
            groupedModels[provider].forEach(model => {
                const option = document.createElement('option');
                option.value = model.id;
                const priceLabel = model.pricing?.is_free ? ' (Free)' : ' (Paid)';
                option.textContent = model.name + priceLabel;
                optgroup.appendChild(option);
            });
            
            this.modelSelect.appendChild(optgroup);
        });
    }

    groupModelsByProvider(models) {
        const grouped = {};
        
        models.forEach(model => {
            const provider = model.id.split('/')[0] || 'other';
            if (!grouped[provider]) {
                grouped[provider] = [];
            }
            grouped[provider].push(model);
        });
        
        return grouped;
    }

    formatProviderName(provider) {
        const providerNames = {
            'meta-llama': 'Meta (Llama)',
            'google': 'Google',
            'mistralai': 'Mistral AI',
            'deepseek': 'DeepSeek',
            'qwen': 'Qwen',
            'anthropic': 'Anthropic',
            'openai': 'OpenAI'
        };
        
        return providerNames[provider] || provider.charAt(0).toUpperCase() + provider.slice(1);
    }

    showFallbackModels() {
        // Fallback models if API fails
        const fallbackModels = [
            { id: 'meta-llama/llama-3.1-8b-instruct:free', name: 'Llama 3.1 8B (Free)' },
            { id: 'google/gemma-2-9b-it:free', name: 'Gemma 2 9B (Free)' },
            { id: 'mistralai/mistral-7b-instruct:free', name: 'Mistral 7B (Free)' },
            { id: 'qwen/qwen-2.5-72b-instruct:free', name: 'Qwen 2.5 72B (Free)' }
        ];
        
        this.modelSelect.innerHTML = '<option value="">🔬 Choose your creature...</option>';
        
        fallbackModels.forEach(model => {
            const option = document.createElement('option');
            option.value = model.id;
            option.textContent = model.name;
            this.modelSelect.appendChild(option);
        });
    }

    updateModelInfo() {
        if (this.currentModel) {
            const selectedModel = this.allModels.find(m => m.id === this.currentModel);
            if (selectedModel) {
                this.modelInfo.innerHTML = this.generateModelInfoCard(selectedModel);
            }
        } else {
            this.modelInfo.innerHTML = '<p>🧬 Choose from hundreds of AI creatures with unique personalities and abilities. Each creature has different traits, intelligence levels, and behaviors. Start creating your own mini monster interactions!</p>';
        }
    }

    generateModelInfoCard(model) {
        const creatureName = this.getCreatureName(model.id);
        
        // Format capabilities
        const capabilities = [];
        if (model.architecture?.input_modalities?.includes('image')) capabilities.push('🖼️ Vision');
        if (model.architecture?.input_modalities?.includes('file')) capabilities.push('📁 Files');
        if (model.capabilities?.supported_parameters?.includes('tools')) capabilities.push('🛠️ Tools');
        if (model.capabilities?.supported_parameters?.includes('reasoning')) capabilities.push('🧠 Reasoning');
        
        // Safety indicators
        const safetyBadges = [];
        if (model.safety_info?.is_moderated) safetyBadges.push('<span class="safety-badge moderated">🛡️ Moderated</span>');
        if (model.capabilities?.max_completion_tokens) safetyBadges.push(`<span class="safety-badge">📝 Max: ${this.formatNumber(model.capabilities.max_completion_tokens)} tokens</span>`);
        
        // Provider info
        const providerInfo = this.getProviderInfo(model.provider);
        
        return `
            <div class="model-info-card">
                <div class="model-header">
                    <div class="creature-name">${creatureName}</div>
                    <div class="provider-badge">${providerInfo.icon} ${providerInfo.name}</div>
                </div>
                
                <div class="model-stats">
                    <div class="stat">
                        <span class="stat-label">🧬 Species:</span>
                        <span class="stat-value">${model.name}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">💰 Cost:</span>
                        <span class="stat-value ${model.pricing?.is_free ? 'free-badge' : 'paid-badge'}">
                            ${model.pricing?.is_free ? '🆓 Free' : '💳 Paid'}
                        </span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">📅 Created:</span>
                        <span class="stat-value">${model.created_date}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">🧠 Memory:</span>
                        <span class="stat-value">${this.formatContextLength(model.context_length)} tokens</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">⚡ Type:</span>
                        <span class="stat-value">${model.architecture?.modality || 'Text'}</span>
                    </div>
                </div>

                ${capabilities.length > 0 ? `
                <div class="capabilities">
                    <div class="section-title">🎯 Abilities:</div>
                    <div class="capability-tags">
                        ${capabilities.map(cap => `<span class="capability-tag">${cap}</span>`).join('')}
                    </div>
                </div>
                ` : ''}

                ${safetyBadges.length > 0 ? `
                <div class="safety-info">
                    <div class="section-title">🛡️ Safety:</div>
                    <div class="safety-badges">
                        ${safetyBadges.join('')}
                    </div>
                </div>
                ` : ''}

                ${model.description ? `
                <div class="description">
                    <div class="section-title">📖 Research Notes:</div>
                    <div class="description-text">${this.truncateDescription(model.description)}</div>
                    ${model.description.length > 200 ? `
                        <button class="show-more-btn" onclick="this.style.display='none'; this.previousElementSibling.textContent='${model.description.replace(/'/g, "\\'")}'"}>Show more</button>
                    ` : ''}
                </div>
                ` : ''}

                ${model.hugging_face_id ? `
                <div class="external-links">
                    <a href="https://huggingface.co/${model.hugging_face_id}" target="_blank" class="hf-link">
                        🤗 View on Hugging Face
                    </a>
                </div>
                ` : ''}
            </div>
        `;
    }

    getProviderInfo(provider) {
        const providers = {
            'meta-llama': { name: 'Meta', icon: '🦙' },
            'google': { name: 'Google', icon: '🔷' },
            'mistralai': { name: 'Mistral AI', icon: '🌪️' },
            'deepseek': { name: 'DeepSeek', icon: '🔍' },
            'qwen': { name: 'Qwen/Alibaba', icon: '🐉' },
            'anthropic': { name: 'Anthropic', icon: '🎭' },
            'openai': { name: 'OpenAI', icon: '🤖' },
            'microsoft': { name: 'Microsoft', icon: '🪟' },
            'nvidia': { name: 'NVIDIA', icon: '💚' }
        };
        
        return providers[provider] || { name: provider.charAt(0).toUpperCase() + provider.slice(1), icon: '🔬' };
    }

    truncateDescription(description) {
        if (!description) return '';
        return description.length > 200 ? description.substring(0, 200) + '...' : description;
    }

    formatNumber(num) {
        if (typeof num !== 'number') return num;
        if (num >= 1000) return (num / 1000).toFixed(0) + 'K';
        return num.toString();
    }

    formatContextLength(length) {
        if (typeof length === 'number') {
            return length.toLocaleString();
        }
        return length || 'Unknown';
    }

    autoResizeTextarea() {
        this.chatInput.style.height = 'auto';
        this.chatInput.style.height = Math.min(this.chatInput.scrollHeight, 120) + 'px';
    }

    updateTokenCount() {
        const text = this.chatInput.value;
        const approxTokens = Math.ceil(text.length / 4); // Rough approximation
        this.tokenCount.textContent = `~${approxTokens} tokens`;
    }

    updateSendButton() {
        const hasText = this.chatInput.value.trim().length > 0;
        const hasModel = this.currentModel.length > 0;
        const canSend = hasText && hasModel && !this.isTyping;
        
        this.sendBtn.disabled = !canSend;
    }

    updateStatus(message, type = 'ready') {
        this.status.textContent = message;
        this.status.className = `status ${type}`;
    }

    getCreatureName(modelId) {
        const creatureNames = {
            'meta-llama': ['🦙 Llama Beast', '🦙 Alpha Llama', '🦙 Mega Llama'],
            'google': ['🤖 Gemini Twin', '🔮 Crystal Gem', '💎 Prism Spirit'],
            'mistralai': ['🌪️ Wind Wraith', '⚡ Storm Dancer', '🌊 Mist Walker'],
            'deepseek': ['🕳️ Void Seeker', '🔍 Truth Hunter', '🧠 Mind Delver'],
            'qwen': ['🐉 Wisdom Dragon', '📚 Knowledge Spirit', '✨ Sage Companion'],
            'anthropic': ['🎭 Claude Mimic', '🎪 Circus Master', '🎨 Art Creature'],
            'openai': ['🤖 GPT Guardian', '⚡ Neural Beast', '🔥 Spark Entity']
        };
        
        const provider = modelId.split('/')[0] || 'unknown';
        const names = creatureNames[provider] || ['🎲 Mystery Creature', '❓ Unknown Beast', '🌟 Rare Entity'];
        return names[Math.floor(Math.random() * names.length)];
    }

    async sendMessage() {
        const message = this.chatInput.value.trim();
        if (!message || !this.currentModel || this.isTyping) return;

        // Prevent double sending
        this.isTyping = true;
        this.updateSendButton();

        // Add user message
        this.addMessage('user', message);
        this.chatInput.value = '';
        this.autoResizeTextarea();
        this.updateTokenCount();

        // Show typing indicator
        this.showTypingIndicator();
        this.updateStatus('🧬 Your creature is evolving thoughts...', 'thinking');

        if (this.useStreaming) {
            await this.sendStreamingMessage(message);
        } else {
            await this.sendRegularMessage(message);
        }
    }

    async sendStreamingMessage(message) {
        try {
            // Hide typing indicator and start streaming message
            this.hideTypingIndicator();
            
            // Create empty assistant message that we'll update
            this.currentStreamingMessage = {
                role: 'assistant',
                content: '',
                timestamp: new Date(),
                usage: null
            };
            
            this.messages.push(this.currentStreamingMessage);
            this.renderStreamingMessage(this.currentStreamingMessage);
            
            const response = await fetch('/api/chat/stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    model: this.currentModel,
                    message: message,
                    history: this.messages.slice(-11, -1) // Exclude the current streaming message
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            
                            if (data.error) {
                                this.handleStreamingError(data.error);
                                return;
                            }
                            
                            if (data.type === 'chunk') {
                                this.updateStreamingMessage(data.content);
                            } else if (data.type === 'done') {
                                this.finalizeStreamingMessage(data.usage);
                                this.updateStatus('🎉 Creature awakened!', 'ready');
                                return;
                            }
                        } catch (e) {
                            // Skip invalid JSON
                            continue;
                        }
                    }
                }
            }
        } catch (error) {
            this.handleStreamingError(`🌐 Connection to monster lab lost: ${error.message}`);
        } finally {
            this.isTyping = false;
            this.updateSendButton();
            this.currentStreamingMessage = null;
        }
    }

    async sendRegularMessage(message) {
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    model: this.currentModel,
                    message: message,
                    history: this.messages.slice(-10) // Send last 10 messages for context
                })
            });

            const data = await response.json();
            
            this.hideTypingIndicator();
            
            if (data.success) {
                this.addMessage('assistant', data.response, data.usage);
                this.updateStatus('🎉 Creature awakened!', 'ready');
            } else {
                this.addMessage('assistant', `💥 Creature malfunction: ${data.error}`, null, true);
                this.updateStatus('⚠️ Lab error detected', 'error');
            }
        } catch (error) {
            this.hideTypingIndicator();
            this.addMessage('assistant', `🌐 Connection to monster lab lost: ${error.message}`, null, true);
            this.updateStatus('🔌 Lab offline', 'error');
        } finally {
            this.isTyping = false;
            this.updateSendButton();
        }
    }

    updateStreamingMessage(content) {
        if (this.currentStreamingMessage) {
            this.currentStreamingMessage.content += content;
            this.updateStreamingMessageDisplay();
        }
    }

    updateStreamingMessageDisplay() {
        const messageElement = document.querySelector('#streaming-message .message-text');
        if (messageElement && this.currentStreamingMessage) {
            try {
                messageElement.innerHTML = marked.parse(this.currentStreamingMessage.content);
                // Highlight code blocks
                messageElement.querySelectorAll('pre code').forEach((block) => {
                    hljs.highlightElement(block);
                });
            } catch (e) {
                messageElement.textContent = this.currentStreamingMessage.content;
            }
            this.scrollToBottom();
        }
    }

    finalizeStreamingMessage(usage) {
        if (this.currentStreamingMessage) {
            this.currentStreamingMessage.usage = usage;
            
            // Update the message display with usage info
            const messageDiv = document.getElementById('streaming-message');
            if (messageDiv && usage) {
                const content = messageDiv.querySelector('.message-content');
                if (content) {
                    const info = document.createElement('div');
                    info.className = 'message-info';
                    info.innerHTML = `
                        <span>${this.formatTime(this.currentStreamingMessage.timestamp)}</span>
                        <span>${usage.total_tokens} tokens used</span>
                    `;
                    content.appendChild(info);
                }
            }
            
            // Remove streaming ID
            if (messageDiv) {
                messageDiv.removeAttribute('id');
            }
        }
    }

    handleStreamingError(error) {
        if (this.currentStreamingMessage) {
            // Replace streaming message with error
            this.currentStreamingMessage.content = `💥 ${error}`;
            this.updateStreamingMessageDisplay();
            
            const messageDiv = document.getElementById('streaming-message');
            if (messageDiv) {
                const content = messageDiv.querySelector('.message-content');
                content.style.background = '#fef2f2';
                content.style.borderColor = '#fecaca';
                content.style.color = '#dc2626';
                messageDiv.removeAttribute('id');
            }
        }
        this.updateStatus('⚠️ Lab error detected', 'error');
    }

    renderStreamingMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message assistant';
        messageDiv.id = 'streaming-message';
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = '<i class="fas fa-dragon"></i>';
        
        const content = document.createElement('div');
        content.className = 'message-content';
        
        const text = document.createElement('div');
        text.className = 'message-text';
        text.innerHTML = '<span class="streaming-cursor">▎</span>'; // Blinking cursor
        
        content.appendChild(text);
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(content);
        
        // Remove welcome message if it exists
        const welcomeMessage = this.chatMessages.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.remove();
        }
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    addMessage(role, content, usage = null, isError = false) {
        const message = {
            role,
            content,
            timestamp: new Date(),
            usage
        };
        
        this.messages.push(message);
        this.renderMessage(message, isError);
        this.scrollToBottom();
    }

    renderMessage(message, isError = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${message.role}`;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = message.role === 'user' 
            ? '<i class="fas fa-user-astronaut"></i>' 
            : '<i class="fas fa-dragon"></i>';
        
        const content = document.createElement('div');
        content.className = 'message-content';
        
        const text = document.createElement('div');
        text.className = 'message-text';
        
        if (message.role === 'assistant' && !isError) {
            // Render markdown for AI responses
            try {
                text.innerHTML = marked.parse(message.content);
                // Highlight code blocks
                text.querySelectorAll('pre code').forEach((block) => {
                    hljs.highlightElement(block);
                });
            } catch (e) {
                // Fallback to plain text if markdown parsing fails
                text.textContent = message.content;
            }
        } else {
            // Plain text for user messages and errors
            text.textContent = message.content;
        }
        
        if (isError) {
            content.style.background = '#fef2f2';
            content.style.borderColor = '#fecaca';
            content.style.color = '#dc2626';
        }
        
        content.appendChild(text);
        
        // Add message info for assistant messages
        if (message.role === 'assistant' && message.usage) {
            const info = document.createElement('div');
            info.className = 'message-info';
            info.innerHTML = `
                <span>${this.formatTime(message.timestamp)}</span>
                <span>${message.usage.total_tokens} tokens used</span>
            `;
            content.appendChild(info);
        } else if (message.role === 'user') {
            const info = document.createElement('div');
            info.className = 'message-info';
            info.innerHTML = `<span>${this.formatTime(message.timestamp)}</span>`;
            content.appendChild(info);
        }
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(content);
        
        // Remove welcome message if it exists
        const welcomeMessage = this.chatMessages.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.remove();
        }
        
        this.chatMessages.appendChild(messageDiv);
    }

    showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message assistant typing-indicator';
        typingDiv.id = 'typing-indicator';
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = '<i class="fas fa-dna"></i>';
        
        const content = document.createElement('div');
        content.className = 'message-content';
        content.innerHTML = `
            <div class="typing-indicator">
                <span>🧬 Your creature is mutating ideas</span>
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;
        
        typingDiv.appendChild(avatar);
        typingDiv.appendChild(content);
        
        // Remove welcome message if it exists
        const welcomeMessage = this.chatMessages.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.remove();
        }
        
        this.chatMessages.appendChild(typingDiv);
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    formatTime(date) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    scrollToBottom() {
        setTimeout(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }, 100);
    }

    clearChat() {
        if (confirm('Are you sure you want to clear all messages?')) {
            this.messages = [];
            this.chatMessages.innerHTML = `
                <div class="welcome-message">
                    <div class="welcome-icon">
                        <i class="fas fa-flask"></i>
                    </div>
                    <h2>🧪 Welcome to the Mini Monsters Lab!</h2>
                    <p>Select a creature from the genetic library and begin your experiment!</p>
                    <div class="model-info" id="model-info">
                        <p>🧬 Choose from 55+ AI creatures with unique personalities and abilities. Each creature has different traits, intelligence levels, and behaviors. Start creating your own mini monster interactions!</p>
                    </div>
                </div>
            `;
            this.modelInfo = document.getElementById('model-info');
            this.updateModelInfo();
        }
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ChatApp();
});