"""
Core data models for the Real-time Misinformation Heatmap system.
Defines ProcessedEvent, SatelliteResult, Claim, and related data structures
with validation and JSON serialization support.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from enum import Enum
import json
import uuid
from pydantic import BaseModel, Field, validator, root_validator
from config import config


class EventSource(str, Enum):
    """Enumeration of supported event sources"""
    NEWS = "news"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    MANUAL = "manual"
    RSS = "rss"


class LanguageCode(str, Enum):
    """Supported Indian language codes"""
    HINDI = "hi"
    ENGLISH = "en"
    BENGALI = "bn"
    TELUGU = "te"
    TAMIL = "ta"
    GUJARATI = "gu"
    KANNADA = "kn"
    MALAYALAM = "ml"
    ORIYA = "or"
    PUNJABI = "pa"
    MARATHI = "mr"
    ASSAMESE = "as"


class ClaimCategory(str, Enum):
    """Categories of misinformation claims"""
    HEALTH = "health"
    POLITICS = "politics"
    DISASTER = "disaster"
    ENVIRONMENT = "environment"
    TECHNOLOGY = "technology"
    SOCIAL = "social"
    ECONOMIC = "economic"
    RELIGIOUS = "religious"
    OTHER = "other"


@dataclass
class Claim:
    """
    Individual claim extracted from text content.
    Represents a specific assertion that can be fact-checked.
    """
    claim_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""
    category: ClaimCategory = ClaimCategory.OTHER
    confidence: float = 0.0  # 0.0 - 1.0, confidence in claim extraction
    entities: List[str] = field(default_factory=list)
    geographic_entities: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate claim data after initialization"""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")
        
        if not self.text.strip():
            raise ValueError("Claim text cannot be empty")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert claim to dictionary for JSON serialization"""
        return {
            "claim_id": self.claim_id,
            "text": self.text,
            "category": self.category.value,
            "confidence": self.confidence,
            "entities": self.entities,
            "geographic_entities": self.geographic_entities,
            "keywords": self.keywords
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Claim':
        """Create claim from dictionary"""
        return cls(
            claim_id=data.get("claim_id", str(uuid.uuid4())),
            text=data["text"],
            category=ClaimCategory(data.get("category", "other")),
            confidence=data.get("confidence", 0.0),
            entities=data.get("entities", []),
            geographic_entities=data.get("geographic_entities", []),
            keywords=data.get("keywords", [])
        )


@dataclass
class SatelliteResult:
    """
    Results from satellite imagery validation using Google Earth Engine.
    Contains similarity scores, anomaly detection, and reality assessment.
    """
    similarity: float = 0.0  # 0.0 - 1.0, similarity to historical baseline
    anomaly: bool = False  # True if significant change detected
    reality_score: float = 0.0  # 0.0 - 1.0, likelihood of being factually accurate
    confidence: float = 0.0  # 0.0 - 1.0, confidence in satellite analysis
    baseline_date: str = ""  # ISO date of baseline imagery
    analysis_metadata: Dict[str, Any] = field(default_factory=dict)
    processing_time_ms: int = 0
    error_message: Optional[str] = None
    
    def __post_init__(self):
        """Validate satellite result data"""
        for score_field in ['similarity', 'reality_score', 'confidence']:
            score = getattr(self, score_field)
            if not 0.0 <= score <= 1.0:
                raise ValueError(f"{score_field} must be between 0.0 and 1.0, got {score}")
        
        # Determine anomaly based on similarity threshold
        if self.similarity < config.get_satellite_config().similarity_threshold:
            self.anomaly = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert satellite result to dictionary for JSON serialization"""
        return {
            "similarity": self.similarity,
            "anomaly": self.anomaly,
            "reality_score": self.reality_score,
            "confidence": self.confidence,
            "baseline_date": self.baseline_date,
            "analysis_metadata": self.analysis_metadata,
            "processing_time_ms": self.processing_time_ms,
            "error_message": self.error_message
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SatelliteResult':
        """Create satellite result from dictionary"""
        return cls(
            similarity=data.get("similarity", 0.0),
            anomaly=data.get("anomaly", False),
            reality_score=data.get("reality_score", 0.0),
            confidence=data.get("confidence", 0.0),
            baseline_date=data.get("baseline_date", ""),
            analysis_metadata=data.get("analysis_metadata", {}),
            processing_time_ms=data.get("processing_time_ms", 0),
            error_message=data.get("error_message")
        )
    
    @classmethod
    def create_stub(cls, lat: float, lon: float) -> 'SatelliteResult':
        """Create realistic stub satellite result for local development"""
        import random
        
        # Generate realistic but random similarity score
        similarity = random.uniform(0.1, 0.9)
        
        # Calculate reality score based on similarity (inverse relationship for misinformation)
        reality_score = max(0.1, 1.0 - similarity + random.uniform(-0.2, 0.2))
        reality_score = min(1.0, reality_score)
        
        return cls(
            similarity=similarity,
            anomaly=similarity < 0.3,
            reality_score=reality_score,
            confidence=random.uniform(0.6, 0.9),
            baseline_date="2023-01-01",
            analysis_metadata={
                "stub_mode": True,
                "coordinates": [lat, lon],
                "imagery_source": "stub_landsat8"
            },
            processing_time_ms=random.randint(100, 500)
        )


@dataclass
class ProcessedEvent:
    """
    Main event model representing a processed misinformation event.
    Contains all analysis results including NLP, satellite validation, and scoring.
    """
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: EventSource = EventSource.MANUAL
    original_text: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    lang: LanguageCode = LanguageCode.ENGLISH
    region_hint: str = ""  # Indian state name
    lat: float = 0.0
    lon: float = 0.0
    entities: List[str] = field(default_factory=list)
    virality_score: float = 0.0  # 0.0 - 1.0
    satellite: Optional[SatelliteResult] = None
    claims: List[Claim] = field(default_factory=list)
    processing_metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Validate processed event data"""
        if not self.original_text.strip():
            raise ValueError("Original text cannot be empty")
        
        if not 0.0 <= self.virality_score <= 1.0:
            raise ValueError(f"Virality score must be between 0.0 and 1.0, got {self.virality_score}")
        
        # Validate coordinates are within India boundaries
        if self.lat != 0.0 or self.lon != 0.0:
            if not config.validate_coordinates(self.lat, self.lon):
                raise ValueError(f"Coordinates ({self.lat}, {self.lon}) are outside India boundaries")
        
        # Ensure satellite result exists
        if self.satellite is None:
            self.satellite = SatelliteResult()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert processed event to dictionary for JSON serialization"""
        return {
            "event_id": self.event_id,
            "source": self.source.value,
            "original_text": self.original_text,
            "timestamp": self.timestamp.isoformat(),
            "lang": self.lang.value,
            "region_hint": self.region_hint,
            "lat": self.lat,
            "lon": self.lon,
            "entities": self.entities,
            "virality_score": self.virality_score,
            "satellite": self.satellite.to_dict() if self.satellite else None,
            "claims": [claim.to_dict() for claim in self.claims],
            "processing_metadata": self.processing_metadata,
            "created_at": self.created_at.isoformat()
        }
    
    def to_json(self) -> str:
        """Convert processed event to JSON string"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessedEvent':
        """Create processed event from dictionary"""
        # Parse datetime fields
        timestamp = datetime.fromisoformat(data["timestamp"]) if isinstance(data["timestamp"], str) else data["timestamp"]
        created_at = datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else data.get("created_at", datetime.utcnow())
        
        # Parse satellite result
        satellite = None
        if data.get("satellite"):
            satellite = SatelliteResult.from_dict(data["satellite"])
        
        # Parse claims
        claims = []
        for claim_data in data.get("claims", []):
            claims.append(Claim.from_dict(claim_data))
        
        return cls(
            event_id=data.get("event_id", str(uuid.uuid4())),
            source=EventSource(data["source"]),
            original_text=data["original_text"],
            timestamp=timestamp,
            lang=LanguageCode(data.get("lang", "en")),
            region_hint=data.get("region_hint", ""),
            lat=data.get("lat", 0.0),
            lon=data.get("lon", 0.0),
            entities=data.get("entities", []),
            virality_score=data.get("virality_score", 0.0),
            satellite=satellite,
            claims=claims,
            processing_metadata=data.get("processing_metadata", {}),
            created_at=created_at
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ProcessedEvent':
        """Create processed event from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def get_primary_claim(self) -> Optional[Claim]:
        """Get the claim with highest confidence score"""
        if not self.claims:
            return None
        return max(self.claims, key=lambda c: c.confidence)
    
    def get_reality_score(self) -> float:
        """Get overall reality score combining satellite and claim analysis"""
        if self.satellite and self.satellite.reality_score > 0:
            return self.satellite.reality_score
        
        # Fallback to claim-based scoring if no satellite data
        if self.claims:
            primary_claim = self.get_primary_claim()
            if primary_claim:
                # Higher confidence in claim extraction suggests lower reality (more likely misinformation)
                return max(0.1, 1.0 - primary_claim.confidence)
        
        return 0.5  # Neutral score if no analysis available


# Pydantic models for API request/response validation
class EventCreateRequest(BaseModel):
    """Request model for creating new events via API"""
    source: EventSource
    original_text: str = Field(..., min_length=1, max_length=5000)
    lang: Optional[LanguageCode] = LanguageCode.ENGLISH
    region_hint: Optional[str] = None
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lon: Optional[float] = Field(None, ge=-180, le=180)
    
    @validator('lat', 'lon')
    def validate_coordinates(cls, v, values):
        """Validate coordinates are within India if provided"""
        if v is not None:
            lat = values.get('lat') if 'lat' in values else v
            lon = values.get('lon') if 'lon' in values else v
            
            if lat is not None and lon is not None:
                if not config.validate_coordinates(lat, lon):
                    raise ValueError(f"Coordinates ({lat}, {lon}) are outside India boundaries")
        return v


class HeatmapResponse(BaseModel):
    """Response model for heatmap API endpoint"""
    states: Dict[str, Dict[str, Any]]  # state_name -> {intensity, count, avg_reality_score}
    total_events: int
    last_updated: datetime
    time_range: Dict[str, str]  # start_time, end_time


class RegionResponse(BaseModel):
    """Response model for region details API endpoint"""
    state: str
    events: List[Dict[str, Any]]  # Processed events for the region
    summary: Dict[str, Any]  # Aggregated statistics
    total_count: int


class HealthCheckResponse(BaseModel):
    """Response model for health check endpoint"""
    status: str
    mode: str  # "local" or "cloud"
    timestamp: datetime
    version: str = "1.0.0"
    components: Dict[str, str]  # component -> status


# Indian states mapping for validation and processing
INDIAN_STATES = {
    "andhra pradesh": {"code": "AP", "capital": "Amaravati"},
    "arunachal pradesh": {"code": "AR", "capital": "Itanagar"},
    "assam": {"code": "AS", "capital": "Dispur"},
    "bihar": {"code": "BR", "capital": "Patna"},
    "chhattisgarh": {"code": "CG", "capital": "Raipur"},
    "goa": {"code": "GA", "capital": "Panaji"},
    "gujarat": {"code": "GJ", "capital": "Gandhinagar"},
    "haryana": {"code": "HR", "capital": "Chandigarh"},
    "himachal pradesh": {"code": "HP", "capital": "Shimla"},
    "jharkhand": {"code": "JH", "capital": "Ranchi"},
    "karnataka": {"code": "KA", "capital": "Bengaluru"},
    "kerala": {"code": "KL", "capital": "Thiruvananthapuram"},
    "madhya pradesh": {"code": "MP", "capital": "Bhopal"},
    "maharashtra": {"code": "MH", "capital": "Mumbai"},
    "manipur": {"code": "MN", "capital": "Imphal"},
    "meghalaya": {"code": "ML", "capital": "Shillong"},
    "mizoram": {"code": "MZ", "capital": "Aizawl"},
    "nagaland": {"code": "NL", "capital": "Kohima"},
    "odisha": {"code": "OR", "capital": "Bhubaneswar"},
    "punjab": {"code": "PB", "capital": "Chandigarh"},
    "rajasthan": {"code": "RJ", "capital": "Jaipur"},
    "sikkim": {"code": "SK", "capital": "Gangtok"},
    "tamil nadu": {"code": "TN", "capital": "Chennai"},
    "telangana": {"code": "TG", "capital": "Hyderabad"},
    "tripura": {"code": "TR", "capital": "Agartala"},
    "uttar pradesh": {"code": "UP", "capital": "Lucknow"},
    "uttarakhand": {"code": "UK", "capital": "Dehradun"},
    "west bengal": {"code": "WB", "capital": "Kolkata"},
    # Union Territories
    "delhi": {"code": "DL", "capital": "New Delhi"},
    "jammu and kashmir": {"code": "JK", "capital": "Srinagar"},
    "ladakh": {"code": "LA", "capital": "Leh"},
    "andaman and nicobar islands": {"code": "AN", "capital": "Port Blair"},
    "chandigarh": {"code": "CH", "capital": "Chandigarh"},
    "dadra and nagar haveli and daman and diu": {"code": "DN", "capital": "Daman"},
    "lakshadweep": {"code": "LD", "capital": "Kavaratti"},
    "puducherry": {"code": "PY", "capital": "Puducherry"}
}


def validate_indian_state(state_name: str) -> bool:
    """Validate if the given state name is a valid Indian state/UT"""
    return state_name.lower() in INDIAN_STATES


def normalize_state_name(state_name: str) -> str:
    """Normalize state name to standard format"""
    normalized = state_name.lower().strip()
    if normalized in INDIAN_STATES:
        return normalized.title()
    return state_name  # Return original if not found