"""
Configuration management for hybrid local/cloud deployment modes.
Handles environment-based switching between SQLite/BigQuery, Pub/Sub emulator/GCP, and stub/real APIs.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class DatabaseConfig:
    """Database configuration for local SQLite or cloud BigQuery"""
    url: str
    type: str  # "sqlite" or "bigquery"
    project_id: Optional[str] = None
    dataset_id: Optional[str] = None
    table_name: str = "events"


@dataclass
class PubSubConfig:
    """Pub/Sub configuration for local emulator or GCP"""
    project_id: str
    topic_name: str
    subscription_name: str
    emulator_host: Optional[str] = None
    use_emulator: bool = False


@dataclass
class SatelliteConfig:
    """Satellite validation configuration for stubs or real Google Earth Engine"""
    use_stub: bool
    gee_service_account_path: Optional[str] = None
    similarity_threshold: float = 0.3
    cache_duration_hours: int = 24


class Config:
    """
    Centralized configuration management for hybrid deployment modes.
    
    Environment Variables:
    - MODE: "local" or "cloud" (default: "local")
    - DATABASE_URL: Override default database configuration
    - GCP_PROJECT_ID: Google Cloud Project ID for cloud mode
    - WATSON_API_KEY: IBM Watson Discovery API key for cloud mode
    - GEE_SERVICE_ACCOUNT: Path to Google Earth Engine service account JSON
    """
    
    def __init__(self, mode: Optional[str] = None):
        self.mode = mode or os.getenv("MODE", "local").lower()
        self.project_root = Path(__file__).parent.parent
        self.data_dir = self.project_root / "data"
        self.data_dir.mkdir(exist_ok=True)
        
        # Validate mode
        if self.mode not in ["local", "cloud"]:
            raise ValueError(f"Invalid mode: {self.mode}. Must be 'local' or 'cloud'")
    
    def is_cloud_mode(self) -> bool:
        """Check if running in cloud production mode"""
        return self.mode == "cloud"
    
    def is_local_mode(self) -> bool:
        """Check if running in local development mode"""
        return self.mode == "local"
    
    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration based on deployment mode"""
        if self.is_local_mode():
            db_path = self.data_dir / "misinfo_heatmap.db"
            return DatabaseConfig(
                url=f"sqlite:///{db_path}",
                type="sqlite"
            )
        else:
            project_id = os.getenv("GCP_PROJECT_ID")
            if not project_id:
                raise ValueError("GCP_PROJECT_ID environment variable required for cloud mode")
            
            return DatabaseConfig(
                url="",  # BigQuery doesn't use traditional URLs
                type="bigquery",
                project_id=project_id,
                dataset_id=os.getenv("BIGQUERY_DATASET", "misinfo_heatmap"),
                table_name="events"
            )
    
    def get_pubsub_config(self) -> PubSubConfig:
        """Get Pub/Sub configuration based on deployment mode"""
        if self.is_local_mode():
            return PubSubConfig(
                project_id="local-project",
                topic_name="misinfo-events",
                subscription_name="misinfo-processor",
                emulator_host="localhost:8085",
                use_emulator=True
            )
        else:
            project_id = os.getenv("GCP_PROJECT_ID")
            if not project_id:
                raise ValueError("GCP_PROJECT_ID environment variable required for cloud mode")
            
            return PubSubConfig(
                project_id=project_id,
                topic_name=os.getenv("PUBSUB_TOPIC", "misinfo-events"),
                subscription_name=os.getenv("PUBSUB_SUBSCRIPTION", "misinfo-processor"),
                use_emulator=False
            )
    
    def get_satellite_config(self) -> SatelliteConfig:
        """Get satellite validation configuration based on deployment mode"""
        if self.is_local_mode():
            return SatelliteConfig(
                use_stub=True,
                similarity_threshold=0.3
            )
        else:
            service_account_path = os.getenv("GEE_SERVICE_ACCOUNT")
            if not service_account_path:
                raise ValueError("GEE_SERVICE_ACCOUNT environment variable required for cloud mode")
            
            return SatelliteConfig(
                use_stub=False,
                gee_service_account_path=service_account_path,
                similarity_threshold=float(os.getenv("SATELLITE_THRESHOLD", "0.3"))
            )
    
    def get_watson_config(self) -> Dict[str, Any]:
        """Get IBM Watson Discovery configuration for cloud mode"""
        if self.is_local_mode():
            return {"enabled": False}
        
        api_key = os.getenv("WATSON_API_KEY")
        if not api_key:
            raise ValueError("WATSON_API_KEY environment variable required for cloud mode")
        
        return {
            "enabled": True,
            "api_key": api_key,
            "url": os.getenv("WATSON_URL", "https://api.us-south.discovery.watson.cloud.ibm.com"),
            "version": os.getenv("WATSON_VERSION", "2019-04-30"),
            "environment_id": os.getenv("WATSON_ENVIRONMENT_ID"),
            "collection_id": os.getenv("WATSON_COLLECTION_ID")
        }
    
    def get_api_config(self) -> Dict[str, Any]:
        """Get API server configuration"""
        return {
            "host": os.getenv("API_HOST", "0.0.0.0"),
            "port": int(os.getenv("API_PORT", "8000")),
            "debug": self.is_local_mode(),
            "cors_origins": [
                "http://localhost:3000",
                "http://localhost:8000",
                "http://127.0.0.1:8000"
            ] if self.is_local_mode() else ["*"],
            "static_files_path": self.project_root / "frontend"
        }
    
    def get_nlp_config(self) -> Dict[str, Any]:
        """Get NLP processing configuration"""
        return {
            "model_name": "ai4bharat/indic-bert",  # IndicBERT for Indian languages
            "supported_languages": ["hi", "en", "bn", "te", "ta", "gu", "kn", "ml", "or", "pa"],
            "max_text_length": 512,
            "batch_size": 16 if self.is_local_mode() else 32,
            "cache_dir": str(self.data_dir / "models"),
            "device": "cpu" if self.is_local_mode() else "auto",
            "use_auth_token": True,  # Enable Hugging Face authentication
            "hf_token": os.getenv("HUGGINGFACE_TOKEN")  # Hugging Face token from env
        }
    
    def get_india_boundaries(self) -> Dict[str, float]:
        """Get India geographic boundaries for validation"""
        return {
            "min_lat": 6.0,    # Southern tip (Kanyakumari area)
            "max_lat": 37.0,   # Northern border (Kashmir)
            "min_lon": 68.0,   # Western border (Gujarat)
            "max_lon": 97.0    # Eastern border (Arunachal Pradesh)
        }
    
    def validate_coordinates(self, lat: float, lon: float) -> bool:
        """Validate if coordinates are within India boundaries"""
        boundaries = self.get_india_boundaries()
        return (
            boundaries["min_lat"] <= lat <= boundaries["max_lat"] and
            boundaries["min_lon"] <= lon <= boundaries["max_lon"]
        )
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration based on deployment mode"""
        if self.is_local_mode():
            return {
                "level": "DEBUG",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "handlers": ["console", "file"],
                "file_path": str(self.data_dir / "app.log")
            }
        else:
            return {
                "level": "INFO",
                "format": "json",  # Structured logging for cloud
                "handlers": ["console"],
                "include_trace": True
            }


# Global configuration instance
config = Config()