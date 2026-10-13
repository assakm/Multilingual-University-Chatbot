import logging
import time
from typing import Dict, List, Optional
import openai
from openai import OpenAI
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

class OpenAIClient:
    def __init__(self):
        if not Config.OPENAI_API_KEY:
            logger.error("OpenAI API key not found")
            self.client = None
        else:
            self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        
        # Initialize circuit breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=Config.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
            timeout=Config.CIRCUIT_BREAKER_TIMEOUT
        )
        
        # Rate limiting
        self.request_times = []
        self.token_usage = {'input': 0, 'output': 0, 'total': 0}
        self.last_reset = datetime.now()
        self.lock = threading.Lock()
        
        # Retry configuration
        self.max_retries = Config.OPENAI_MAX_RETRIES
        self.base_delay = 1  # Base delay for exponential backoff
    
    def chat_completion(self, messages: List[Dict], temperature: float = None, max_tokens: int = None) -> Dict:
        """
        Make a chat completion request with error handling and retries
        """
        if not self.client:
            return {
                'success': False,
                'error': 'OpenAI client not initialized (missing API key)',
                'content': '',
                'tokens_used': 0
            }
        
        if temperature is None:
            temperature = Config.OPENAI_TEMPERATURE
        if max_tokens is None:
            max_tokens = Config.OPENAI_MAX_TOKENS
        
        try:
            # Check rate limits
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
            logger.error(f"OpenAI request failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'content': '',
                'tokens_used': 0
            }
    
    def _make_request(self, messages: List[Dict], temperature: float, max_tokens: int) -> Dict:
        """
        Make the actual OpenAI request with retries
        """
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=Config.OPENAI_MODEL,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=Config.OPENAI_TIMEOUT
                )
                
                # Update token usage
                with self.lock:
                    if hasattr(response, 'usage') and response.usage:
                        self.token_usage['input'] += getattr(response.usage, 'prompt_tokens', 0)
                        self.token_usage['output'] += getattr(response.usage, 'completion_tokens', 0)
                        self.token_usage['total'] += getattr(response.usage, 'total_tokens', 0)
                
                return {
                    'success': True,
                    'content': response.choices[0].message.content,
                    'error': '',
                    'tokens_used': getattr(response.usage, 'total_tokens', 0) if hasattr(response, 'usage') else 0
                }
                
            except openai.RateLimitError as e:
                logger.warning(f"Rate limit hit on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    delay = self._calculate_backoff_delay(attempt)
                    time.sleep(delay)
                    continue
                raise e
                
            except openai.APITimeoutError as e:
                logger.warning(f"Timeout on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    delay = self._calculate_backoff_delay(attempt)
                    time.sleep(delay)
                    continue
                raise e
                
            except openai.APIError as e:
                if e.status_code >= 500:  # Server errors
                    logger.warning(f"Server error on attempt {attempt + 1}: {e}")
                    if attempt < self.max_retries - 1:
                        delay = self._calculate_backoff_delay(attempt)
                        time.sleep(delay)
                        continue
                raise e
                
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                raise e
        
        raise Exception(f"Request failed after {self.max_retries} attempts")
    
    def _calculate_backoff_delay(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay with jitter
        """
        import random
        delay = self.base_delay * (2 ** attempt)
        jitter = random.uniform(0, 0.1) * delay  # Add up to 10% jitter
        return min(delay + jitter, 60)  # Cap at 60 seconds
    
    def _check_rate_limits(self):
        """
        Simple client-side rate limiting
        """
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
            
            # Check request rate (simple check for 20 requests per minute)
            if len(self.request_times) >= 20:
                oldest_request = min(self.request_times)
                sleep_time = 60 - (now - oldest_request).total_seconds()
                if sleep_time > 0:
                    logger.warning(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
                    time.sleep(sleep_time)
            
            # Record this request
            self.request_times.append(now)
    
    def get_usage_stats(self) -> Dict:
        """
        Get current usage statistics
        """
        with self.lock:
            return {
                'tokens_used': self.token_usage.copy(),
                'requests_last_minute': len([
                    t for t in self.request_times 
                    if datetime.now() - t < timedelta(minutes=1)
                ]),
                'circuit_breaker_state': self.circuit_breaker.state,
                'last_reset': self.last_reset.isoformat()
            }
    
    def reset_circuit_breaker(self):
        """
        Manually reset the circuit breaker
        """
        with self.circuit_breaker.lock:
            self.circuit_breaker.state = 'closed'
            self.circuit_breaker.failure_count = 0
            self.circuit_breaker.last_failure_time = None
        
        logger.info("Circuit breaker manually reset")
    
    def test_connection(self) -> Dict:
        """
        Test the OpenAI connection
        """
        test_messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, this is a connection test."}
        ]
        
        try:
            response = self.chat_completion(test_messages, temperature=0.1, max_tokens=10)
            return {
                'success': response['success'],
                'message': 'Connection test successful' if response['success'] else response['error']
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Connection test failed: {str(e)}'
            }
