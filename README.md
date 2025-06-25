# 🤖 OpenRouter Chat UI

A sleek, modern web interface for chatting with 55+ free AI models through OpenRouter API.

## ✨ Features

- **55+ Free Models**: Access to Llama, Gemma, Mistral, Qwen, DeepSeek and more
- **Modern UI**: Clean, responsive design similar to ChatGPT/Claude
- **Real-time Chat**: Instant responses with typing indicators
- **Model Selection**: Easy dropdown to switch between models
- **Token Tracking**: Monitor usage with token counts
- **Chat History**: Maintains conversation context
- **Mobile Friendly**: Responsive design for all devices

## 🚀 Quick Start

1. **Install Dependencies**:
   ```bash
   cd chat_ui
   python -m venv chat_env
   source chat_env/bin/activate  # On Windows: chat_env\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Start the Server**:
   ```bash
   python start.py
   ```

3. **Open Your Browser**:
   - Go to the URL shown in the terminal (e.g., `http://localhost:58567`)
   - Select a free model from the dropdown
   - Start chatting!

## 📁 Files Structure

```
chat_ui/
├── index.html      # Main HTML structure  
├── style.css       # Modern CSS styling
├── script.js       # JavaScript functionality
├── app.py          # Flask backend API
├── start.py        # Easy startup script
├── requirements.txt # Python dependencies
└── README.md       # This file
```

## 🛠️ How It Works

- **Frontend**: Modern HTML/CSS/JS with responsive design
- **Backend**: Flask API that communicates with OpenRouter
- **Models**: Only uses free tier models (those with `:free` suffix)
- **Context**: Maintains chat history for better conversations

## 🔧 Configuration

The app automatically loads your OpenRouter API key from `../api_keys.env`.
Make sure your API key file contains:
```
openrouter_api_key=sk-or-v1-your-key-here
```

## 🆓 Free Models Available

- **Meta Llama**: 3.1/3.3 series (8B, 70B variants)
- **Google Gemma**: 2/3 series (9B, 12B, 27B variants)  
- **Mistral**: 7B, 24B instruction models
- **Qwen**: 2.5 series (8B, 32B, 72B variants)
- **DeepSeek**: V3, R1 reasoning models
- **And many more!**

## 💡 Tips

- Use Shift+Enter for new lines in messages
- Switch models anytime during conversation
- Clear chat to start fresh conversations
- Check token usage to monitor API calls

Enjoy chatting with AI! 🤖✨