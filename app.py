#!/usr/bin/env python3
from flask import Flask, render_template, request, jsonify, send_from_directory, Response
from flask_cors import CORS
import requests
import json
import os
from pathlib import Path
import time
import uuid

app = Flask(__name__)
CORS(app)

def load_api_key():
    """Load OpenRouter API key from environment variable or file"""
    # Try environment variable first (for production)
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if api_key:
        return api_key
    
    # Fall back to local file (for development)
    env_file = Path.home() / "api_keys.env"
    if not env_file.exists():
        env_file = Path(__file__).parent.parent.parent / "api_keys.env"
    
    if not env_file.exists():
        raise FileNotFoundError(f"API keys file not found at {env_file}")
    
    with open(env_file, 'r') as f:
        for line in f:
            if line.startswith('openrouter_api_key='):
                return line.split('=', 1)[1].strip()
    
    raise ValueError("openrouter_api_key not found in api_keys.env")

def generate_model_categories(model):
    """Generate categories/tags for a model based on its metadata"""
    categories = []
    
    # Get model info
    name = model.get('name', '').lower()
    description = model.get('description', '').lower()
    model_id = model.get('id', '').lower()
    architecture = model.get('architecture', {})
    capabilities = model.get('capabilities', {})
    
    # Modality-based categories
    input_modalities = architecture.get('input_modalities', [])
    if 'image' in input_modalities:
        categories.append('vision')
    if 'text' in input_modalities and 'image' in input_modalities:
        categories.append('multimodal')
    
    # Capability-based categories
    supported_params = capabilities.get('supported_parameters', [])
    if 'tools' in supported_params:
        categories.append('tools')
    if 'reasoning' in supported_params:
        categories.append('reasoning')
        
    # Content analysis from name and description
    content_keywords = {
        'code': ['code', 'programming', 'developer', 'coding', 'github', 'python', 'javascript'],
        'math': ['math', 'mathematical', 'calculation', 'solver', 'theorem'],
        'reasoning': ['reasoning', 'logic', 'analysis', 'think', 'step-by-step'],
        'creative': ['creative', 'writing', 'story', 'literature', 'poetry', 'novel'],
        'roleplay': ['roleplay', 'character', 'persona', 'chat', 'assistant'],
        'uncensored': ['uncensored', 'nsfw', 'unfiltered', 'unconstrained'],
        'fast': ['fast', 'speed', 'quick', 'nano', 'turbo', 'instant'],
        'large': ['large', 'big', 'giant', 'huge', 'massive'],
        'small': ['small', 'mini', 'tiny', 'lite', 'compact']
    }
    
    combined_text = f"{name} {description} {model_id}"
    
    for category, keywords in content_keywords.items():
        if any(keyword in combined_text for keyword in keywords):
            categories.append(category)
    
    # Provider-specific categories
    provider = model.get('id', '').split('/')[0]
    provider_specialties = {
        'anthropic': ['reasoning', 'helpful'],
        'openai': ['general', 'popular'],
        'meta-llama': ['open-source'],
        'google': ['research', 'advanced'],
        'mistralai': ['efficient'],
        'deepseek': ['reasoning', 'code'],
        'qwen': ['multilingual'],
        'microsoft': ['enterprise'],
        'cohere': ['search', 'embeddings']
    }
    
    if provider in provider_specialties:
        categories.extend(provider_specialties[provider])
    
    # Context length categories
    context_length = model.get('context_length', 0)
    if isinstance(context_length, int):
        if context_length >= 128000:
            categories.append('long-context')
        elif context_length >= 32000:
            categories.append('medium-context')
        elif context_length <= 8192:
            categories.append('short-context')
    
    # Remove duplicates and return
    return list(set(categories))

def get_models(filter_type='all'):
    """Get list of models from OpenRouter with optional filtering"""
    try:
        api_key = load_api_key()
        
        response = requests.get(
            url="https://openrouter.ai/api/v1/models",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            models = data.get('data', [])
            
            # Filter models based on filter_type and include rich metadata
            filtered_models = []
            for model in models:
                pricing = model.get('pricing', {})
                prompt_price = pricing.get('prompt', '0')
                
                # Apply filtering based on filter_type
                is_free = prompt_price == '0' or ':free' in model.get('id', '')
                
                if filter_type == 'free' and not is_free:
                    continue
                elif filter_type == 'paid' and is_free:
                    continue
                # filter_type == 'all' includes everything
                
                # Extract architecture info
                architecture = model.get('architecture', {})
                
                # Extract provider info
                top_provider = model.get('top_provider', {})
                
                # Parse model ID for provider
                model_id = model.get('id', '')
                provider = model_id.split('/')[0] if '/' in model_id else 'unknown'
                
                # Format creation date
                created_timestamp = model.get('created', 0)
                import datetime
                try:
                    created_date = datetime.datetime.fromtimestamp(created_timestamp).strftime('%Y-%m-%d') if created_timestamp else 'Unknown'
                except:
                    created_date = 'Unknown'
                
                # Add pricing info
                price_info = {
                    'is_free': is_free,
                    'prompt_price': prompt_price,
                    'completion_price': pricing.get('completion', '0')
                }
                
                # Generate categories/tags
                categories = generate_model_categories(model)
                
                filtered_models.append({
                    'id': model.get('id'),
                    'name': model.get('name', 'Unknown'),
                    'description': model.get('description', ''),
                    'context_length': model.get('context_length', 'Unknown'),
                    'provider': provider,
                    'created_date': created_date,
                    'hugging_face_id': model.get('hugging_face_id', ''),
                    'canonical_slug': model.get('canonical_slug', ''),
                    'pricing': price_info,
                    'categories': categories,
                    'architecture': {
                        'modality': architecture.get('modality', 'Unknown'),
                        'input_modalities': architecture.get('input_modalities', []),
                        'output_modalities': architecture.get('output_modalities', []),
                        'tokenizer': architecture.get('tokenizer', 'Unknown'),
                        'instruct_type': architecture.get('instruct_type', None)
                    },
                    'capabilities': {
                        'max_completion_tokens': top_provider.get('max_completion_tokens', 'Unknown'),
                        'is_moderated': top_provider.get('is_moderated', False),
                        'supported_parameters': model.get('supported_parameters', [])
                    },
                    'safety_info': {
                        'is_moderated': top_provider.get('is_moderated', False),
                        'per_request_limits': model.get('per_request_limits', None)
                    }
                })
            
            return filtered_models
        else:
            raise Exception(f"API returned status {response.status_code}")
            
    except Exception as e:
        print(f"Error fetching models: {e}")
        # Return fallback models
        return [
            {
                'id': 'meta-llama/llama-3.1-8b-instruct:free',
                'name': 'Llama 3.1 8B (Free)',
                'description': 'Meta\'s Llama 3.1 8B model',
                'context_length': 131072
            },
            {
                'id': 'google/gemma-2-9b-it:free',
                'name': 'Gemma 2 9B (Free)',
                'description': 'Google\'s Gemma 2 9B model',
                'context_length': 8192
            },
            {
                'id': 'mistralai/mistral-7b-instruct:free',
                'name': 'Mistral 7B (Free)',
                'description': 'Mistral\'s 7B instruction model',
                'context_length': 32768
            },
            {
                'id': 'qwen/qwen-2.5-72b-instruct:free',
                'name': 'Qwen 2.5 72B (Free)',
                'description': 'Qwen\'s large language model',
                'context_length': 32768
            }
        ]

def chat_with_model_streaming(model_id, message, history=None):
    """Send message to OpenRouter model with streaming response"""
    try:
        api_key = load_api_key()
        
        # Prepare messages
        messages = []
        
        # Add conversation history
        if history:
            for msg in history[-6:]:  # Keep last 6 messages for context
                messages.append({
                    "role": msg.get('role', 'user'),
                    "content": msg.get('content', '')
                })
        
        # Add current message
        messages.append({
            "role": "user",
            "content": message
        })
        
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model_id,
                "messages": messages,
                "max_tokens": 1000,
                "temperature": 0.7,
                "stream": True
            },
            timeout=30,
            stream=True
        )
        
        if response.status_code == 200:
            return response
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            error_message = error_data.get('error', {}).get('message', f"HTTP {response.status_code}")
            
            return {
                'success': False,
                'error': error_message
            }
            
    except requests.exceptions.Timeout:
        return {
            'success': False,
            'error': 'Request timed out. Please try again.'
        }
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'error': f'Network error: {str(e)}'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }

def chat_with_model(model_id, message, history=None):
    """Send message to OpenRouter model (non-streaming fallback)"""
    try:
        api_key = load_api_key()
        
        # Prepare messages
        messages = []
        
        # Add conversation history
        if history:
            for msg in history[-6:]:  # Keep last 6 messages for context
                messages.append({
                    "role": msg.get('role', 'user'),
                    "content": msg.get('content', '')
                })
        
        # Add current message
        messages.append({
            "role": "user",
            "content": message
        })
        
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model_id,
                "messages": messages,
                "max_tokens": 1000,
                "temperature": 0.7
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Extract response
            content = result['choices'][0]['message']['content']
            
            # Extract usage info
            usage = result.get('usage', {})
            
            return {
                'success': True,
                'response': content,
                'usage': {
                    'prompt_tokens': usage.get('prompt_tokens', 0),
                    'completion_tokens': usage.get('completion_tokens', 0),
                    'total_tokens': usage.get('total_tokens', 0)
                }
            }
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            error_message = error_data.get('error', {}).get('message', f"HTTP {response.status_code}")
            
            return {
                'success': False,
                'error': error_message
            }
            
    except requests.exceptions.Timeout:
        return {
            'success': False,
            'error': 'Request timed out. Please try again.'
        }
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'error': f'Network error: {str(e)}'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }

@app.route('/')
def index():
    """Serve the main chat interface"""
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files (CSS, JS)"""
    return send_from_directory('.', filename)

@app.route('/api/models', methods=['GET'])
def get_models_endpoint():
    """API endpoint to get available models with optional filtering"""
    try:
        price_filter = request.args.get('price', 'all')  # 'all', 'free', or 'paid'
        category_filter = request.args.get('category', 'all')  # category name or 'all'
        
        models = get_models('all')  # Get all models first
        
        # Apply price filtering
        if price_filter == 'free':
            models = [m for m in models if m['pricing']['is_free']]
        elif price_filter == 'paid':
            models = [m for m in models if not m['pricing']['is_free']]
        
        # Apply category filtering
        if category_filter != 'all':
            models = [m for m in models if category_filter in m.get('categories', [])]
        
        return jsonify({
            'success': True,
            'models': models,
            'count': len(models),
            'price_filter': price_filter,
            'category_filter': category_filter
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/categories', methods=['GET'])
def get_categories():
    """API endpoint to get all available categories"""
    try:
        models = get_models('all')
        all_categories = set()
        
        for model in models:
            all_categories.update(model.get('categories', []))
        
        # Sort categories and create display names
        category_list = []
        category_display_names = {
            'vision': '👁️ Vision',
            'multimodal': '🔄 Multimodal',
            'tools': '🛠️ Tools',
            'reasoning': '🧠 Reasoning',
            'code': '💻 Code',
            'math': '🔢 Math',
            'creative': '🎨 Creative',
            'roleplay': '🎭 Roleplay',
            'uncensored': '🔓 Uncensored',
            'fast': '⚡ Fast',
            'large': '📏 Large',
            'small': '📦 Small',
            'long-context': '📜 Long Context',
            'medium-context': '📄 Medium Context',
            'short-context': '📝 Short Context',
            'open-source': '🌍 Open Source',
            'general': '🌐 General',
            'popular': '⭐ Popular',
            'research': '🔬 Research',
            'advanced': '🚀 Advanced',
            'efficient': '⚙️ Efficient',
            'multilingual': '🌎 Multilingual',
            'enterprise': '🏢 Enterprise',
            'helpful': '🤝 Helpful',
            'search': '🔍 Search',
            'embeddings': '🔗 Embeddings'
        }
        
        for category in sorted(all_categories):
            category_list.append({
                'value': category,
                'label': category_display_names.get(category, category.title())
            })
        
        return jsonify({
            'success': True,
            'categories': category_list
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    """API endpoint for streaming chat messages"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        model_id = data.get('model')
        message = data.get('message')
        history = data.get('history', [])
        
        if not model_id or not message:
            return jsonify({
                'success': False,
                'error': 'Model and message are required'
            }), 400
        
        def generate():
            try:
                response = chat_with_model_streaming(model_id, message, history)
                
                if isinstance(response, dict) and not response.get('success', True):
                    yield f"data: {json.dumps({'error': response['error']})}\n\n"
                    return
                
                accumulated_content = ""
                total_tokens = 0
                
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        
                        if line_str.startswith('data: '):
                            data_str = line_str[6:]
                            
                            if data_str.strip() == '[DONE]':
                                # Send final message with complete content and usage
                                yield f"data: {json.dumps({'type': 'done', 'content': accumulated_content, 'usage': {'total_tokens': total_tokens}})}\n\n"
                                break
                            
                            try:
                                chunk_data = json.loads(data_str)
                                
                                if 'choices' in chunk_data and len(chunk_data['choices']) > 0:
                                    delta = chunk_data['choices'][0].get('delta', {})
                                    
                                    if 'content' in delta:
                                        content_chunk = delta['content']
                                        accumulated_content += content_chunk
                                        total_tokens += 1  # Rough approximation
                                        
                                        # Send the chunk
                                        yield f"data: {json.dumps({'type': 'chunk', 'content': content_chunk})}\n\n"
                                
                            except json.JSONDecodeError:
                                continue
                
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        return Response(
            generate(),
            mimetype='text/plain',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type'
            }
        )
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """API endpoint for chat messages (non-streaming fallback)"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        model_id = data.get('model')
        message = data.get('message')
        history = data.get('history', [])
        
        if not model_id or not message:
            return jsonify({
                'success': False,
                'error': 'Model and message are required'
            }), 400
        
        # Chat with the model
        result = chat_with_model(model_id, message, history)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    
    if debug:
        print("🚀 Starting OpenRouter Chat UI...")
        print(f"📱 Open your browser and go to: http://localhost:{port}")
        print("🤖 Enjoy chatting with free AI models!")
        print("🛑 Press Ctrl+C to stop the server")
    
    app.run(debug=debug, host='0.0.0.0', port=port)