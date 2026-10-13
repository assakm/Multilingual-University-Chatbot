import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    OPENAI_TEMPERATURE = float(os.getenv('OPENAI_TEMPERATURE', '0.1'))
    OPENAI_MAX_TOKENS = int(os.getenv('OPENAI_MAX_TOKENS', '400'))
    OPENAI_TIMEOUT = int(os.getenv('OPENAI_TIMEOUT', '10'))
    OPENAI_MAX_RETRIES = int(os.getenv('OPENAI_MAX_RETRIES', '3'))
    
    # Embedding Configuration
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2')
    EMBEDDING_DIMENSION = int(os.getenv('EMBEDDING_DIMENSION', '768'))
    
    # Vector Database Configuration
    VECTOR_DB_PATH = os.getenv('VECTOR_DB_PATH', './data/vector_db')
    VECTOR_DB_COLLECTION = os.getenv('VECTOR_DB_COLLECTION', 'university_docs')
    
    # Chunking Configuration
    CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '500'))
    CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', '50'))
    
    # Similarity Thresholds
    FUZZY_HIGH_THRESHOLD = float(os.getenv('FUZZY_HIGH_THRESHOLD', '85.0'))
    FUZZY_LOW_THRESHOLD = float(os.getenv('FUZZY_LOW_THRESHOLD', '60.0'))
    INTENT_HIGH_THRESHOLD = float(os.getenv('INTENT_HIGH_THRESHOLD', '0.75'))
    INTENT_LOW_THRESHOLD = float(os.getenv('INTENT_LOW_THRESHOLD', '0.6'))
    RETRIEVAL_THRESHOLD = float(os.getenv('RETRIEVAL_THRESHOLD', '0.65'))
    
    # RAG Configuration
    TOP_K_RETRIEVAL = int(os.getenv('TOP_K_RETRIEVAL', '5'))
    MAX_CONTEXT_LENGTH = int(os.getenv('MAX_CONTEXT_LENGTH', '2000'))
    
    # Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///chatbot.db')
    
    # Security & Rate Limiting
    MAX_INPUT_LENGTH = int(os.getenv('MAX_INPUT_LENGTH', '500'))
    RATE_LIMIT_PER_USER = int(os.getenv('RATE_LIMIT_PER_USER', '60'))
    
    # FAQ Configuration
    FAQ_FILE_PATH = os.getenv('FAQ_FILE_PATH', './data/faq.json')
    SUPPORTED_LANGUAGES = ['en', 'hi', 'ta', 'te']
    DEFAULT_LANGUAGE = os.getenv('DEFAULT_LANGUAGE', 'en')
    
    # Circuit Breaker Configuration
    CIRCUIT_BREAKER_FAILURE_THRESHOLD = int(os.getenv('CIRCUIT_BREAKER_FAILURE_THRESHOLD', '5'))
    CIRCUIT_BREAKER_TIMEOUT = int(os.getenv('CIRCUIT_BREAKER_TIMEOUT', '300'))
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_CONVERSATIONS = os.getenv('LOG_CONVERSATIONS', 'true').lower() == 'true'
    
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

    # Add at the end of config.py
    # Ollama Configuration
    USE_OLLAMA = os.getenv('USE_OLLAMA', 'true').lower() == 'true'
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.2:3b')
    OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')

