import json
import logging
import re
from typing import Dict, List, Optional, Tuple
from rapidfuzz import fuzz, process
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from config import Config

logger = logging.getLogger(__name__)

class MatcherService:
    def __init__(self):
        self.faq_data = []
        self.faq_embeddings = {}
        self.intent_prototypes = {}
        self.intent_embeddings = {}
        self.embedding_model = None
        
        # Rule patterns for quick responses
        self.rule_patterns = {
            'en': {
                r'(office hours|opening hours|timings?)': "Our office hours are Monday to Friday, 9:00 AM to 5:00 PM.",
                r'(contact|phone|number|call)': "You can contact us at +91-XXXXXXXXXX or email support@university.edu",
                r'(emergency|urgent|help)': "For emergencies, please call our 24/7 helpline: +91-XXXXXXXXXX",
                r'(hello|hi|hey|greetings?)': "Hello! How can I help you today?",
                r'(thank you|thanks|appreciate)': "You're welcome! Is there anything else I can help you with?"
            },
            'hi': {
                r'(समय|खुलने का समय|कार्यालय समय)': "हमारे कार्यालय का समय सोमवार से शुक्रवार, सुबह 9:00 बजे से शाम 5:00 बजे तक है।",
                r'(संपर्क|फोन|नंबर)': "आप हमसे +91-XXXXXXXXXX पर संपर्क कर सकते हैं या support@university.edu पर ईमेल कर सकते हैं",
                r'(आपातकाल|तुरंत|मदद)': "आपातकाल के लिए, कृपया हमारी 24/7 हेल्पलाइन पर कॉल करें: +91-XXXXXXXXXX"
            }
        }
        
        self._load_embedding_model()
        self._initialize_intent_prototypes()
    
    def _load_embedding_model(self):
        """Load the multilingual embedding model"""
        try:
            self.embedding_model = SentenceTransformer(Config.EMBEDDING_MODEL)
            logger.info(f"Loaded embedding model: {Config.EMBEDDING_MODEL}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def _initialize_intent_prototypes(self):
        """Initialize intent detection prototypes"""
        self.intent_prototypes = {
            'en': {
                'admissions_fee': [
                    "What is the admission fee?",
                    "How much does it cost to apply?",
                    "Application fee amount",
                    "Cost of admission"
                ],
                'application_deadline': [
                    "When is the application deadline?",
                    "Last date to apply",
                    "Application submission deadline",
                    "Due date for applications"
                ],
                'hostel_enquiry': [
                    "Tell me about hostel facilities",
                    "Accommodation options",
                    "Hostel fee and amenities",
                    "Student housing"
                ],
                'course_information': [
                    "What courses are offered?",
                    "Available programs",
                    "Course curriculum details",
                    "Academic programs"
                ]
            },
            'hi': {
                'admissions_fee': [
                    "प्रवेश शुल्क क्या है?",
                    "आवेदन की लागत कितनी है?",
                    "दाखिले की फीस"
                ],
                'application_deadline': [
                    "आवेदन की अंतिम तिथि कब है?",
                    "आवेदन जमा करने की समय सीमा"
                ]
            }
        }
        
        # Compute embeddings for intent prototypes
        self._compute_intent_embeddings()
    
    def _compute_intent_embeddings(self):
        """Compute embeddings for intent detection"""
        if not self.embedding_model:
            return
        
        for lang, intents in self.intent_prototypes.items():
            self.intent_embeddings[lang] = {}
            for intent, examples in intents.items():
                embeddings = self.embedding_model.encode(examples)
                self.intent_embeddings[lang][intent] = np.mean(embeddings, axis=0)
    
    def load_faq_data(self):
        """Load FAQ data from JSON file"""
        try:
            with open(Config.FAQ_FILE_PATH, 'r', encoding='utf-8') as f:
                self.faq_data = json.load(f)
            
            # Compute embeddings for FAQ entries
            self._compute_faq_embeddings()
            
            logger.info(f"Loaded {len(self.faq_data)} FAQ entries")
        except FileNotFoundError:
            logger.warning(f"FAQ file not found: {Config.FAQ_FILE_PATH}")
            self.faq_data = []
        except Exception as e:
            logger.error(f"Error loading FAQ data: {e}")
            self.faq_data = []
    
    def _compute_faq_embeddings(self):
        """Compute embeddings for FAQ questions"""
        if not self.embedding_model or not self.faq_data:
            return
        
        for lang in Config.SUPPORTED_LANGUAGES:
            self.faq_embeddings[lang] = {}
            questions = []
            faq_ids = []
            
            for faq in self.faq_data:
                if lang in faq['question']:
                    questions.append(faq['question'][lang])
                    faq_ids.append(faq['id'])
            
            if questions:
                embeddings = self.embedding_model.encode(questions)
                for faq_id, embedding in zip(faq_ids, embeddings):
                    self.faq_embeddings[lang][faq_id] = embedding
    
    def check_rules(self, message: str, language: str) -> Optional[str]:
        """Check if message matches any rule-based patterns"""
        patterns = self.rule_patterns.get(language, {})
        
        message_lower = message.lower()
        
        for pattern, response in patterns.items():
            if re.search(pattern, message_lower, re.IGNORECASE):
                return response
        
        return None
    
    
    def match_faq(self, message: str, language: str) -> Dict:
        """
        Match message against FAQ entries using exact and fuzzy matching
        """
        result = {
            'match_type': 'none',
            'answer': None,
            'confidence': 0.0,
            'suggested_question': None,
            'faq_id': None
        }
        
        try:
            if not self.faq_data:
                logger.warning("No FAQ data loaded")
                return result
            
            # Prepare questions for fuzzy matching
            questions = []
            answers = {}
            faq_ids = {}
            
            for faq in self.faq_data:
                if language in faq.get('question', {}):
                    question = faq['question'][language]
                    questions.append(question)
                    answers[question] = faq.get('answer', {}).get(language, faq.get('answer', {}).get('en', ''))
                    faq_ids[question] = faq.get('id', 'unknown')
            
            if not questions:
                logger.warning(f"No questions found for language: {language}")
                return result
            
            logger.info(f"Matching '{message}' against {len(questions)} questions in {language}")
            
            # Check for exact match first
            message_lower = message.lower().strip()
            for question in questions:
                if message_lower == question.lower().strip():
                    result.update({
                        'match_type': 'exact',
                        'answer': answers[question],
                        'confidence': 100.0,
                        'faq_id': faq_ids[question]
                    })
                    logger.info(f"Exact match found: '{message}' -> '{question}'")
                    return result
            
            # Fuzzy matching with proper unpacking
            try:
                best_match = process.extractOne(
                    message,
                    questions,
                    scorer=fuzz.token_set_ratio,
                    score_cutoff=Config.FUZZY_LOW_THRESHOLD
                )
                
                if best_match:
                    # Handle both 2-value and 3-value returns from rapidfuzz
                    if len(best_match) == 3:
                        question, confidence, index = best_match
                    elif len(best_match) == 2:
                        question, confidence = best_match
                    else:
                        logger.error(f"Unexpected rapidfuzz return format: {best_match}")
                        return result
                    
                    logger.info(f"Fuzzy match found: '{message}' -> '{question}' (confidence: {confidence})")
                    
                    if confidence >= Config.FUZZY_HIGH_THRESHOLD:
                        result.update({
                            'match_type': 'high_fuzzy',
                            'answer': answers[question],
                            'confidence': confidence,
                            'faq_id': faq_ids[question]
                        })
                    else:
                        result.update({
                            'match_type': 'low_fuzzy',
                            'answer': answers[question],
                            'confidence': confidence,
                            'suggested_question': question,
                            'faq_id': faq_ids[question]
                        })
                else:
                    logger.info(f"No fuzzy match found for: '{message}' (threshold: {Config.FUZZY_LOW_THRESHOLD})")
            
            except ImportError as e:
                logger.error(f"RapidFuzz not available: {e}")
                # Fall back to simple string matching
                for question in questions:
                    if any(word in question.lower() for word in message.lower().split()):
                        result.update({
                            'match_type': 'low_fuzzy',
                            'answer': answers[question],
                            'confidence': 70.0,
                            'suggested_question': question,
                            'faq_id': faq_ids[question]
                        })
                        break
            
            except Exception as e:
                logger.error(f"Error in fuzzy matching: {e}")
                logger.error(f"best_match value: {best_match}")
                # Don't crash, just return no match
            
            return result
            
        except Exception as e:
            logger.error(f"Critical error in match_faq: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return result


    
    def _get_intent_response(self, intent: str, language: str) -> str:
        """Get response for detected intent"""
        intent_responses = {
            'en': {
                'admissions_fee': "For admission fees, please check our official prospectus or contact the admissions office at admissions@university.edu",
                'application_deadline': "Application deadlines vary by program. Please visit our admissions page for specific dates.",
                'hostel_enquiry': "Our hostels offer comfortable accommodation with modern amenities. Contact student affairs for details.",
                'course_information': "We offer various undergraduate and postgraduate programs. Visit our academics page for detailed information."
            },
            'hi': {
                'admissions_fee': "प्रवेश शुल्क के लिए, कृपया हमारा आधिकारिक प्रॉस्पेक्टस देखें या admissions@university.edu पर प्रवेश कार्यालय से संपर्क करें",
                'application_deadline': "आवेदन की समय सीमा कार्यक्रम के अनुसार अलग होती है। कृपया विशिष्ट तारीखों के लिए हमारे प्रवेश पृष्ठ पर जाएं।"
            }
        }
        
        return intent_responses.get(language, {}).get(intent, "I can help you with that. Please provide more specific information.")
    
    def get_similar_questions(self, message: str, language: str, top_k: int = 3) -> List[Dict]:
        """
        Get similar questions using embedding-based similarity
        """
        if not self.embedding_model or language not in self.faq_embeddings:
            return []
        
        try:
            message_embedding = self.embedding_model.encode([message])[0]
            similarities = []
            
            for faq in self.faq_data:
                if (language in faq['question'] and 
                    faq['id'] in self.faq_embeddings[language]):
                    
                    faq_embedding = self.faq_embeddings[language][faq['id']]
                    similarity = cosine_similarity(
                        [message_embedding], 
                        [faq_embedding]
                    )[0][0]
                    
                    similarities.append({
                        'question': faq['question'][language],
                        'answer': faq['answer'].get(language, faq['answer'].get('en', '')),
                        'similarity': similarity,
                        'faq_id': faq['id']
                    })
            
            # Sort by similarity and return top_k
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            return similarities[:top_k]
            
        except Exception as e:
            logger.error(f"Error getting similar questions: {e}")
            return []
        
    def detect_intent(self, message: str, language: str) -> Dict:
        """
        Detect intent using embedding-based similarity
        """
        result = {
            'intent': None,
            'confidence': 0.0,
            'response': None
        }
        
        if not self.embedding_model or language not in self.intent_embeddings:
            return result
        
        try:
            # Compute message embedding
            message_embedding = self.embedding_model.encode([message])[0]
            
            # Compare with intent prototypes
            best_intent = None
            best_confidence = 0.0
            
            for intent, prototype_embedding in self.intent_embeddings[language].items():
                similarity = cosine_similarity(
                    [message_embedding], 
                    [prototype_embedding]
                )[0][0]
                
                if similarity > best_confidence:
                    best_confidence = similarity
                    best_intent = intent
            
            if best_confidence >= Config.INTENT_LOW_THRESHOLD:
                result.update({
                    'intent': best_intent,
                    'confidence': best_confidence,
                    'response': self._get_intent_response(best_intent, language)
                })
        
        except Exception as e:
            logger.error(f"Error in intent detection: {e}")
        
        return result

    def _get_intent_response(self, intent: str, language: str) -> str:
        """Get response for detected intent"""
        intent_responses = {
            'en': {
                'admissions_fee': "For admission fees, please check our official prospectus or contact the admissions office at admissions@university.edu",
                'application_deadline': "Application deadlines vary by program. Please visit our admissions page for specific dates.",
                'hostel_enquiry': "Our hostels offer comfortable accommodation with modern amenities. Contact student affairs for details.",
                'course_information': "We offer various undergraduate and postgraduate programs. Visit our academics page for detailed information."
            },
            'hi': {
                'admissions_fee': "प्रवेश शुल्क के लिए, कृपया हमारा आधिकारिक प्रॉस्पेक्टस देखें या admissions@university.edu पर प्रवेश कार्यालय से संपर्क करें",
                'application_deadline': "आवेदन की समय सीमा कार्यक्रम के अनुसार अलग होती है। कृपया विशिष्ट तारीखों के लिए हमारे प्रवेश पृष्ठ पर जाएं।"
            }
        }
        
        return intent_responses.get(language, {}).get(intent, "I can help you with that. Please provide more specific information.")

