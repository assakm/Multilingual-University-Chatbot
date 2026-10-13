import logging
import time
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import json
import uuid

from config import Config
from services.nlp import NLPService
from services.matcher import MatcherService
from services.retriever import RetrieverService
from services.rag import RAGService
from services.openai_client import OpenAIClient
from services.admin import AdminService
from services.ollama_client import OllamaClient
from flask import render_template, jsonify, request
import uuid

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize metrics
request_counter = Counter('chatbot_requests_total', 'Total chatbot requests', ['language', 'pipeline_path'])
response_time = Histogram('chatbot_response_time_seconds', 'Response time in seconds')
openai_calls = Counter('openai_calls_total', 'Total OpenAI API calls')
openai_errors = Counter('openai_errors_total', 'Total OpenAI API errors')
fallback_counter = Counter('fallbacks_total', 'Total fallback responses')
faq_hits = Counter('faq_hits_total', 'Total FAQ hits', ['match_type'])

# Initialize services
nlp_service = NLPService()
matcher_service = MatcherService()
retriever_service = RetrieverService()
openai_client = OllamaClient()
rag_service = RAGService(retriever_service, openai_client)
admin_service = AdminService()

class ChatbotPipeline:
    def __init__(self):
        pass
    
    def process_request(self, user_id: str, message: str, conversation_id: str = None, metadata: dict = None):
        start_time = time.time()
        pipeline_path = "unknown"
        user_lang = "en"
        response = None
        
        try:
            # Step 1: Language detection and normalization
            user_lang = nlp_service.detect_language(message)
            normalized_message = nlp_service.normalize_text(message, user_lang)
            
            # Step 2: Rule-based checks
            rule_response = matcher_service.check_rules(normalized_message, user_lang)
            if rule_response:
                pipeline_path = "rule_based"
                response = rule_response
                return self._create_response(response, user_lang, pipeline_path, start_time)
            
            # Step 3: FAQ exact/fuzzy lookup
            faq_result = matcher_service.match_faq(normalized_message, user_lang)
            if faq_result['match_type'] in ['exact', 'high_fuzzy']:
                pipeline_path = f"faq_{faq_result['match_type']}"
                faq_hits.labels(match_type=faq_result['match_type']).inc()
                response = faq_result['answer']
                return self._create_response(response, user_lang, pipeline_path, start_time)
            elif faq_result['match_type'] == 'low_fuzzy':
                pipeline_path = "faq_suggestion"
                faq_hits.labels(match_type='low_fuzzy').inc()
                response = f"{faq_result['answer']}\n\nDid you mean: {faq_result['suggested_question']}?"
                return self._create_response(response, user_lang, pipeline_path, start_time)
            
            # Step 4: Intent detection
            intent_result = matcher_service.detect_intent(normalized_message, user_lang)
            if intent_result['confidence'] >= Config.INTENT_HIGH_THRESHOLD:
                pipeline_path = "intent_detection"
                response = intent_result['response']
                return self._create_response(response, user_lang, pipeline_path, start_time)
            
            # Step 5: RAG pipeline
            rag_result = rag_service.generate_response(
                query=normalized_message,
                user_lang=user_lang,
                conversation_history=self._get_conversation_history(conversation_id),
                user_id=user_id
            )
            
            if rag_result['used_openai']:
                pipeline_path = "rag_with_openai"
                openai_calls.inc()
            else:
                pipeline_path = "rag_no_openai"
                fallback_counter.inc()
                
            response = rag_result['answer']
            
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            pipeline_path = "error"
            fallback_counter.inc()
            response = self._get_fallback_response(user_lang)
        
        return self._create_response(response, user_lang, pipeline_path, start_time)
    
    def _create_response(self, answer: str, user_lang: str, pipeline_path: str, start_time: float):
        response_time_seconds = time.time() - start_time
        
        request_counter.labels(language=user_lang, pipeline_path=pipeline_path).inc()
        response_time.observe(response_time_seconds)
        
        return {
            'answer': answer,
            'language': user_lang,
            'pipeline_path': pipeline_path,
            'response_time': response_time_seconds,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _get_conversation_history(self, conversation_id: str):
        # Implementation for conversation history retrieval
        # This would typically involve database queries
        return []
    
    def _get_fallback_response(self, user_lang: str):
        fallback_messages = {
            'en': "I'm not sure about that. Please rephrase your question or contact our support team at support@university.edu",
            'hi': "मुझे इसके बारे में यकीन नहीं है। कृपया अपना प्रश्न दोबारा पूछें या हमारी सहायता टीम से support@university.edu पर संपर्क करें",
            'ta': "என்னால் இது பற்றி உறுதியாக சொல்ல முடியவില்லை. தயவுசெய்து உங்கள் கேள்வியை மறுபடி கேட்கவும் அல்லது support@university.edu இல் எங்கள் ஆதரவு குழுவைத் தொடர்பு கொள்ளவும்",
            'te': "దీని గురించి నాకు ఖచ్చితంగా తెలియదు. దయచేసి మీ ప్రశ్నను మళ్లీ అడగండి లేదా support@university.edu వద్ద మా మద్దతు బృందాన్ని సంప్రదించండి"
        }
        return fallback_messages.get(user_lang, fallback_messages['en'])

# Initialize pipeline
chatbot_pipeline = ChatbotPipeline()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })

@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@app.route('/chat', methods=['POST'])
def chat():
    """Main chat endpoint"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or 'message' not in data or 'user_id' not in data:
            return jsonify({'error': 'Missing required fields: user_id and message'}), 400
        
        user_id = data['user_id']
        message = data['message'].strip()
        conversation_id = data.get('conversation_id', str(uuid.uuid4()))
        metadata = data.get('metadata', {})
        
        # Input validation
        if len(message) > Config.MAX_INPUT_LENGTH:
            return jsonify({'error': f'Message too long. Maximum {Config.MAX_INPUT_LENGTH} characters allowed'}), 400
        
        if not message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        # Process the request
        response = chatbot_pipeline.process_request(user_id, message, conversation_id, metadata)
        
        # Log conversation if enabled
        if Config.LOG_CONVERSATIONS:
            logger.info(f"Conversation - User: {user_id}, Message: {message[:100]}..., Response: {response['answer'][:100]}...")
        
        return jsonify({
            'conversation_id': conversation_id,
            'response': response['answer'],
            'language': response['language'],
            'pipeline_used': response['pipeline_path'],
            'response_time': response['response_time']
        })
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/faq', methods=['POST', 'PUT'])
def manage_faq():
    """Admin endpoint to add/update FAQ entries"""
    try:
        data = request.get_json()
        
        if request.method == 'POST':
            result = admin_service.add_faq_entry(data)
        else:  # PUT
            result = admin_service.update_faq_entry(data)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error in FAQ management: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/faq', methods=['GET'])
def get_faq():
    """Get all FAQ entries"""
    try:
        faqs = admin_service.get_all_faqs()
        return jsonify({'faqs': faqs})
    except Exception as e:
        logger.error(f"Error getting FAQs: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/faq/<faq_id>', methods=['DELETE'])
def delete_faq(faq_id):
    """Delete FAQ entry"""
    try:
        result = admin_service.delete_faq_entry(faq_id)
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
    except Exception as e:
        logger.error(f"Error deleting FAQ: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/reindex', methods=['POST'])
def reindex():
    """Admin endpoint to trigger reindexing"""
    try:
        result = admin_service.reindex_documents()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error during reindexing: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin', methods=['GET'])
def admin_dashboard():
    """Simple admin dashboard"""
    return render_template('admin.html')

@app.route('/admin/stats', methods=['GET'])
def admin_stats():
    """Get admin statistics"""
    try:
        stats = admin_service.get_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
    
@app.route('/')
def index():
    """Main chat interface"""
    return render_template('index.html')

@app.route('/admin-ui')
def admin_ui():
    """Admin interface"""
    return render_template('admin.html')

'''@app.route('/api/chat', methods=['POST'])
def api_chat():
    """API endpoint for frontend (different from /chat to avoid conflicts)"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        user_id = data.get('user_id', f'user_{uuid.uuid4().hex[:8]}')
        message = data.get('message', '').strip()
        conversation_id = data.get('conversation_id')
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Process the request using existing pipeline
        result = chatbot_pipeline.process_request(
            user_id=user_id,
            message=message,
            conversation_id=conversation_id
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in frontend chat API: {e}")
        return jsonify({
            'error': 'Internal server error',
            'conversation_id': str(uuid.uuid4()),
            'response': "I'm experiencing technical difficulties. Please try again.",
            'pipeline_used': 'error',
            'language': 'en'
        }), 500'''

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """API endpoint for frontend (different from /chat to avoid conflicts)"""
    try:
        # Add logging to debug
        logger.info(f"Frontend API request: {request.get_json()}")
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        user_id = data.get('user_id', f'user_{uuid.uuid4().hex[:8]}')
        message = data.get('message', '').strip()
        conversation_id = data.get('conversation_id', str(uuid.uuid4()))
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        logger.info(f"Processing frontend message: '{message}' from user: {user_id}")
        
        # Process the request using existing pipeline
        result = chatbot_pipeline.process_request(
            user_id=user_id,
            message=message,
            conversation_id=conversation_id
        )
        
        logger.info(f"Frontend response: {result.get('pipeline_path', 'unknown')} - {result.get('answer', '')[:100]}...")
        
        # Return in the format expected by frontend (same as /chat endpoint)
        response = {
            'conversation_id': conversation_id,
            'response': result['answer'],           # Frontend expects 'response', not 'answer'
            'language': result['language'],
            'pipeline_used': result['pipeline_path'], # Frontend expects 'pipeline_used', not 'pipeline_path'
            'response_time': result['response_time']
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in frontend chat API: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return jsonify({
            'error': 'Internal server error',
            'conversation_id': str(uuid.uuid4()),
            'response': "I'm experiencing technical difficulties. Please try again.",
            'pipeline_used': 'error',
            'language': 'en',
            'response_time': 0.0
        }), 500


# Add static file serving
@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return app.send_static_file(filename)


if __name__ == '__main__':
    # Initialize services on startup
    try:
        logger.info("Initializing chatbot services...")
        
        # Initialize services in the correct order
        nlp_service = NLPService()
        logger.info("✅ NLP service initialized")
        
        retriever_service = RetrieverService()
        retriever_service.initialize()
        logger.info("✅ Retriever service initialized")
        
        matcher_service = MatcherService()
        matcher_service.load_faq_data()
        logger.info("✅ Matcher service initialized")
        
        openai_client = OllamaClient()
        logger.info("✅ Ollama client initialized")
        
        rag_service = RAGService(retriever_service, openai_client)
        logger.info("✅ RAG service initialized")
        
        admin_service = AdminService()
        logger.info("✅ Admin service initialized")
        
        # Update the pipeline with initialized services
        chatbot_pipeline = ChatbotPipeline()
        
        logger.info("All chatbot services initialized successfully")
        
        app.run(host='0.0.0.0', port=5000, debug=Config.DEBUG)
        
    except Exception as e:
        logger.error(f"Failed to initialize chatbot: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise


'''if __name__ == '__main__':
    # Initialize services on startup
    try:
        logger.info("Initializing chatbot services...")
        
        # Initialize vector database
        retriever_service.initialize()
        
        # Load FAQ data
        matcher_service.load_faq_data()
        
        logger.info("Chatbot services initialized successfully")
        
        app.run(host='0.0.0.0', port=5000, debug=Config.DEBUG)
        
    except Exception as e:
        logger.error(f"Failed to initialize chatbot: {str(e)}")
        raise'''
