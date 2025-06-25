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

def get_free_models():
    """Get list of free models from OpenRouter"""
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
            
            # Filter for free models and include rich metadata
            free_models = []
            for model in models:
                pricing = model.get('pricing', {})
                prompt_price = pricing.get('prompt', '0')
                
                # Check if model is free
                if prompt_price == '0' or ':free' in model.get('id', ''):
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
                    
                    free_models.append({
                        'id': model.get('id'),
                        'name': model.get('name', 'Unknown'),
                        'description': model.get('description', ''),
                        'context_length': model.get('context_length', 'Unknown'),
                        'provider': provider,
                        'created_date': created_date,
                        'hugging_face_id': model.get('hugging_face_id', ''),
                        'canonical_slug': model.get('canonical_slug', ''),
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
            
            return free_models
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
def get_models():
    """API endpoint to get available free models"""
    try:
        models = get_free_models()
        return jsonify({
            'success': True,
            'models': models,
            'count': len(models)
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