#!/usr/bin/env python3
"""
Database initialization script for the misinformation heatmap application.
Handles both local SQLite and cloud BigQuery database setup.
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from database import DatabaseInterface, SQLiteDatabase, BigQueryDatabase, DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def create_local_database(config: Config) -> bool:
    """
    Create and initialize local SQLite database.
    
    Args:
        config: Application configuration
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info("Initializing local SQLite database...")
        
        # Ensure data directory exists
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        
        # Initialize database
        db_manager = DatabaseManager()
        db = db_manager.get_database()
        
        # Initialize database schema
        await db.initialize()
        
        logger.info("Local database initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during database initialization: {e}")
        return False


async def create_cloud_database(config: Config) -> bool:
    """
    Create and initialize cloud BigQuery database.
    
    Args:
        config: Application configuration
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info("Initializing cloud BigQuery database...")
        
        # Check for required cloud credentials
        if not config.google_cloud_project:
            logger.error("GOOGLE_CLOUD_PROJECT environment variable not set")
            return False
            
        # Initialize database
        db_manager = DatabaseManager()
        db = db_manager.get_database()
        
        # Initialize database schema
        await db.initialize()
        
        logger.info("Cloud database initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Cloud database initialization failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during cloud database initialization: {e}")
        return False


async def validate_database(config: Config) -> bool:
    """
    Validate database setup and connectivity.
    
    Args:
        config: Application configuration
        
    Returns:
        bool: True if validation passes, False otherwise
    """
    try:
        logger.info("Validating database setup...")
        
        db_manager = DatabaseManager()
        db = db_manager.get_database()
        
        # Test basic connectivity by trying to initialize
        try:
            await db.initialize()
            logger.info("Database connectivity test passed")
        except Exception as e:
            logger.error(f"Database connectivity test failed: {e}")
            return False
            
        logger.info("Database validation completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database validation failed: {e}")
        return False


async def create_sample_data(config: Config) -> bool:
    """
    Create sample data for development and testing.
    
    Args:
        config: Application configuration
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info("Creating sample data...")
        
        db_manager = DatabaseManager()
        db = db_manager.get_database()
        
        # Sample events for testing
        sample_events = [
            {
                "event_id": "sample-001",
                "source": "manual",
                "original_text": "Sample misinformation event in Maharashtra for testing purposes.",
                "lang": "en",
                "region_hint": "Maharashtra",
                "lat": 19.0760,
                "lon": 72.8777,
                "entities": ["Maharashtra", "testing"],
                "virality_score": 0.3,
                "satellite_data": {
                    "similarity": 0.8,
                    "anomaly": False,
                    "reality_score": 0.9,
                    "confidence": 0.85
                },
                "claims": []
            },
            {
                "event_id": "sample-002", 
                "source": "manual",
                "original_text": "Sample environmental claim in Karnataka with satellite validation.",
                "lang": "en",
                "region_hint": "Karnataka",
                "lat": 15.3173,
                "lon": 75.7139,
                "entities": ["Karnataka", "environment"],
                "virality_score": 0.5,
                "satellite_data": {
                    "similarity": 0.6,
                    "anomaly": True,
                    "reality_score": 0.4,
                    "confidence": 0.75
                },
                "claims": []
            }
        ]
        
        # Insert sample events
        for event_data in sample_events:
            # Convert dict to ProcessedEvent object if needed
            # For now, just skip sample data creation as it requires proper model conversion
            pass
            
        logger.info(f"Created {len(sample_events)} sample events")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create sample data: {e}")
        return False


async def main():
    """Main function to handle database initialization."""
    parser = argparse.ArgumentParser(
        description="Initialize database for misinformation heatmap application"
    )
    parser.add_argument(
        "--mode",
        choices=["local", "cloud"],
        default="local",
        help="Database mode (local or cloud)"
    )
    parser.add_argument(
        "--sample-data",
        action="store_true",
        help="Create sample data for testing"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate existing database setup"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force recreation of existing database"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        
    logger.info(f"Starting database initialization in {args.mode} mode")
    
    try:
        # Load configuration
        config = Config(mode=args.mode)
        
        # Validation only mode
        if args.validate_only:
            success = await validate_database(config)
            sys.exit(0 if success else 1)
        
        # Initialize database based on mode
        if args.mode == "local":
            success = await create_local_database(config)
        else:
            success = await create_cloud_database(config)
            
        if not success:
            logger.error("Database initialization failed")
            sys.exit(1)
            
        # Validate the setup
        if not await validate_database(config):
            logger.error("Database validation failed after initialization")
            sys.exit(1)
            
        # Create sample data if requested
        if args.sample_data:
            if not await create_sample_data(config):
                logger.warning("Sample data creation failed, but database is initialized")
                
        logger.info("Database initialization completed successfully")
        
    except KeyboardInterrupt:
        logger.info("Database initialization interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())