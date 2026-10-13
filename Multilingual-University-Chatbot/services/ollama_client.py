import logging
import time
import requests
import json
from typing import Dict, List, Optional
import threading
from datetime import datetime, timedelta

from config import Config

logger = logging.getLogger(__name__)

class CircuitBreaker:
    def __init__(self, failure_threshold: int, timeout: int):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half-open
        self.lock = threading.Lock()
    
    def call(self, func, *args, **kwargs):
        with self.lock:
            if self.state == 'open':
                if datetime.now() - self.last_failure_time > timedelta(seconds=self.timeout):
                    self.state = 'half-open'
                else:
                    raise Exception("Circuit breaker is open")
            
            try:
                result = func(*args, **kwargs)
                if self.state == 'half-open':
                    self.state = 'closed'
                    self.failure_count = 0
                return result
            except Exception as e:
                self.failure_count += 1
                self.last_failure_time = datetime.now()
                
                if self.failure_count >= self.failure_threshold:
                    self.state = 'open'
                
                raise e

class OllamaClient:
    def __init__(self):
        self.base_url = getattr(Config, 'OLLAMA_BASE_URL', 'http://localhost:11434')
        self.model = getattr(Config, 'OLLAMA_MODEL', 'llama3.2:3b')
        self.timeout = 60 #getattr(Config, 'OPENAI_TIMEOUT', 30)
        self.max_retries = getattr(Config, 'OPENAI_MAX_RETRIES', 3)
        
        # Initialize circuit breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=Config.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
            timeout=Config.CIRCUIT_BREAKER_TIMEOUT
        )
        
        # Request tracking
        self.request_times = []
        self.token_usage = {'input': 0, 'output': 0, 'total': 0}
        self.last_reset = datetime.now()
        self.lock = threading.Lock()
        
        # Test connection
        self._test_connection()
    
    def _test_connection(self):
        """Test if Ollama is running and model is available"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models_data = response.json()
                models = [m['name'] for m in models_data.get('models', [])]
                logger.info(f"✅ Ollama connected. Available models: {models}")
                
                # Check if our model is available
                if self.model not in models:
                    logger.warning(f"⚠️ Model {self.model} not found. Available: {models}")
                    if models:
                        # Use first available model
                        self.model = models[0]
                        logger.info(f"Switching to available model: {self.model}")
                    else:
                        logger.error("❌ No models available. Please install a model with: ollama pull llama3.2:3b")
                else:
                    logger.info(f"✅ Using model: {self.model}")
            else:
                logger.error(f"❌ Ollama not responding: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Ollama connection failed: {e}")
            logger.info("💡 Please start Ollama with: ollama serve")
    
    def chat_completion(self, messages: List[Dict], temperature: float = None, max_tokens: int = None) -> Dict:
        """
        Chat completion using Ollama (compatible with OpenAI interface)
        """
        if temperature is None:
            temperature = Config.OPENAI_TEMPERATURE
        if max_tokens is None:
            max_tokens = Config.OPENAI_MAX_TOKENS
        
        try:
            # Check rate limits (similar to OpenAI client)
            self._check_rate_limits()
            
            # Make request through circuit breaker
            response = self.circuit_breaker.call(
                self._make_request,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Ollama request failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'content': '',
                'tokens_used': 0
            }
    
    def _make_request(self, messages: List[Dict], temperature: float, max_tokens: int) -> Dict:
        """Make the actual Ollama request"""
        try:
            # Convert OpenAI messages format to Ollama prompt
            prompt = self._convert_messages_to_prompt(messages)
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "stop": ["Human:", "Assistant:", "\n\nHuman:", "\n\nAssistant:", "User:", "System:"],
                    "top_p": 0.9,
                    "repeat_penalty": 1.1
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=60 #self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result.get('response', '').strip()
                
                # Update token usage tracking
                with self.lock:
                    prompt_tokens = result.get('prompt_eval_count', 0)
                    completion_tokens = result.get('eval_count', 0)
                    total_tokens = prompt_tokens + completion_tokens
                    
                    self.token_usage['input'] += prompt_tokens
                    self.token_usage['output'] += completion_tokens
                    self.token_usage['total'] += total_tokens
                
                return {
                    'success': True,
                    'content': generated_text,
                    'error': '',
                    'tokens_used': result.get('eval_count', 0)
                }
            else:
                error_msg = f"Ollama API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'content': '',
                    'error': error_msg,
                    'tokens_used': 0
                }
                
        except Exception as e:
            logger.error(f"Ollama request exception: {e}")
            raise e
    
    def _convert_messages_to_prompt(self, messages: List[Dict]) -> str:
        """Convert OpenAI messages format to a single prompt for Ollama"""
        prompt_parts = []
        
        for message in messages:
            role = message.get('role', '')
            content = message.get('content', '')
            
            if role == 'system':
                prompt_parts.append(f"System: {content}")
            elif role == 'user':
                prompt_parts.append(f"Human: {content}")
            elif role == 'assistant':
                prompt_parts.append(f"Assistant: {content}")
        
        # Add final prompt for assistant response
        prompt_parts.append("Assistant:")
        return '\n\n'.join(prompt_parts)
    
    def _check_rate_limits(self):
        """Simple client-side rate limiting (adapted from OpenAI client)"""
        with self.lock:
            now = datetime.now()
            
            # Reset counters every hour
            if now - self.last_reset > timedelta(hours=1):
                self.token_usage = {'input': 0, 'output': 0, 'total': 0}
                self.request_times = []
                self.last_reset = now
            
            # Remove old request times (older than 1 minute)
            minute_ago = now - timedelta(minutes=1)
            self.request_times = [t for t in self.request_times if t > minute_ago]
            
            # Record this request
            self.request_times.append(now)
    
    def test_connection(self) -> Dict:
        """Test the Ollama connection"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                return {
                    'success': True,
                    'message': f'Ollama connected successfully. Model: {self.model}'
                }
            else:
                return {
                    'success': False,
                    'message': f'Ollama connection failed: HTTP {response.status_code}'
                }
        except Exception as e:
            return {
                'success': False,
                'message': f'Ollama connection failed: {str(e)}'
            }
    
    def get_usage_stats(self) -> Dict:
        """Get current usage statistics"""
        with self.lock:
            return {
                'tokens_used': self.token_usage.copy(),
                'requests_last_minute': len([
                    t for t in self.request_times 
                    if datetime.now() - t < timedelta(minutes=1)
                ]),
                'circuit_breaker_state': self.circuit_breaker.state,
                'model_used': self.model,
                'base_url': self.base_url,
                'last_reset': self.last_reset.isoformat()
            }
    
    def reset_circuit_breaker(self):
        """Manually reset the circuit breaker"""
        with self.circuit_breaker.lock:
            self.circuit_breaker.state = 'closed'
            self.circuit_breaker.failure_count = 0
            self.circuit_breaker.last_failure_time = None
        
        logger.info("Circuit breaker manually reset")
