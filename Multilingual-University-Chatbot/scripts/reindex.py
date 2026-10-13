#!/usr/bin/env python3
"""
Standalone script to reindex documents
"""
import sys
import os
import logging

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.admin import AdminService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Run document reindexing"""
    try:
        logger.info("Starting document reindexing...")
        
        admin_service = AdminService()
        result = admin_service.reindex_documents()
        
        if result['success']:
            logger.info("✅ Reindexing completed successfully")
            print("Reindexing completed successfully!")
        else:
            logger.error(f"❌ Reindexing failed: {result['message']}")
            print(f"Reindexing failed: {result['message']}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error during reindexing: {e}")
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
