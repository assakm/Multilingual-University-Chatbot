import re
import unicodedata
import logging
from typing import Optional, List, Dict
import spacy
from langdetect import detect, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

# Set seed for consistent language detection
DetectorFactory.seed = 0

logger = logging.getLogger(__name__)

class NLPService:
    def __init__(self):
        self.supported_languages = ['en', 'hi', 'ta', 'te']
        self.language_patterns = {
            'hi': re.compile(r'[\u0900-\u097F]'),  # Devanagari script
            'ta': re.compile(r'[\u0B80-\u0BFF]'),  # Tamil script
            'te': re.compile(r'[\u0C00-\u0C7F]'),  # Telugu script
            'en': re.compile(r'[a-zA-Z]')          # Latin script
        }
        
        # Initialize NLTK data
        try:
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
        except Exception as e:
            logger.warning(f"Failed to download NLTK data: {e}")
        
        # Load spaCy model for English
        try:
            self.nlp_en = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("English spaCy model not found. Install with: python -m spacy download en_core_web_sm")
            self.nlp_en = None
    
    def detect_language(self, text: str) -> str:
        """
        Detect language of input text with fallback to script-based detection
        """
        if not text or not text.strip():
            return 'en'  # Default to English
        
        # First try langdetect
        try:
            detected = detect(text)
            if detected in self.supported_languages:
                return detected
        except (LangDetectException, Exception) as e:
            logger.debug(f"langdetect failed: {e}")
        
        # Fallback to script-based detection
        return self._detect_by_script(text)
    
    def _detect_by_script(self, text: str) -> str:
        """
        Detect language based on Unicode script ranges
        """
        script_counts = {lang: len(pattern.findall(text)) 
                        for lang, pattern in self.language_patterns.items()}
        
        # Return language with highest character count
        max_lang = max(script_counts, key=script_counts.get)
        if script_counts[max_lang] > 0:
            return max_lang
        
        return 'en'  # Default fallback
    
    def normalize_text(self, text: str, language: str = 'en') -> str:
        """
        Normalize text based on language-specific rules
        """
        if not text:
            return ""
        
        # Unicode normalization
        text = unicodedata.normalize('NFC', text)
        
        # Basic cleaning
        text = text.strip()
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        
        # Language-specific normalization
        if language == 'hi':
            text = self._normalize_hindi(text)
        elif language == 'ta':
            text = self._normalize_tamil(text)
        elif language == 'te':
            text = self._normalize_telugu(text)
        else:
            text = text.lower()
        
        return text
    
    def _normalize_hindi(self, text: str) -> str:
        """Normalize Hindi text"""
        # Remove diacritical marks that are often inconsistent
        text = re.sub(r'[\u093C]', '', text)  # Remove nukta
        text = re.sub(r'[\u0901-\u0902]', '', text)  # Remove some diacritics
        return text
    
    def _normalize_tamil(self, text: str) -> str:
        """Normalize Tamil text"""
        # Basic Tamil normalization
        return text
    
    def _normalize_telugu(self, text: str) -> str:
        """Normalize Telugu text"""
        # Basic Telugu normalization
        return text
    
    def tokenize(self, text: str, language: str = 'en') -> List[str]:
        """
        Tokenize text based on language
        """
        if not text:
            return []
        
        if language == 'en' and self.nlp_en:
            doc = self.nlp_en(text)
            return [token.text for token in doc if not token.is_space]
        else:
            # Fallback to NLTK tokenization
            try:
                return word_tokenize(text)
            except Exception as e:
                logger.warning(f"Tokenization failed: {e}")
                return text.split()
    
    def extract_keywords(self, text: str, language: str = 'en', max_keywords: int = 10) -> List[str]:
        """
        Extract keywords from text
        """
        if not text:
            return []
        
        if language == 'en' and self.nlp_en:
            doc = self.nlp_en(text)
            keywords = []
            
            for token in doc:
                if (token.pos_ in ['NOUN', 'ADJ', 'VERB'] and 
                    not token.is_stop and 
                    not token.is_punct and 
                    len(token.text) > 2):
                    keywords.append(token.lemma_.lower())
            
            return list(set(keywords))[:max_keywords]
        else:
            # Simple keyword extraction for other languages
            tokens = self.tokenize(text, language)
            return [token.lower() for token in tokens if len(token) > 2][:max_keywords]
    
    def is_question(self, text: str, language: str = 'en') -> bool:
        """
        Determine if text is a question
        """
        question_indicators = {
            'en': ['what', 'when', 'where', 'why', 'how', 'who', 'which', 'do', 'does', 'did', 'can', 'could', 'will', 'would', 'is', 'are'],
            'hi': ['क्या', 'कैसे', 'कब', 'कहाँ', 'कौन', 'क्यों', 'कितना', 'कैसा'],
            'ta': ['என்ன', 'எப்படி', 'எப்போது', 'எங்கே', 'ஏன்', 'யார்', 'எது'],
            'te': ['ఏమి', 'ఎలా', 'ఎప్పుడు', 'ఎక్కడ', 'ఎందుకు', 'ఎవరు', 'ఏది']
        }
        
        # Check for question mark
        if '?' in text:
            return True
        
        # Check for question words
        indicators = question_indicators.get(language, question_indicators['en'])
        text_lower = text.lower()
        
        return any(indicator in text_lower for indicator in indicators)
    
    def get_sentiment(self, text: str) -> str:
        """
        Basic sentiment analysis (positive, negative, neutral)
        """
        if not text:
            return 'neutral'
        
        # Simple keyword-based sentiment
        positive_words = ['good', 'great', 'excellent', 'amazing', 'wonderful', 'perfect', 'love', 'like']
        negative_words = ['bad', 'terrible', 'awful', 'hate', 'dislike', 'worst', 'horrible', 'disappointing']
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'
