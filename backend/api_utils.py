"""
API utilities for error handling, response formatting, validation,
and common functionality used across FastAPI endpoints.
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from functools import wraps
import traceback
import time

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Configure logging
logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects"""
    
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class CustomJSONResponse(JSONResponse):
    """Custom JSONResponse that handles datetime serialization"""
    
    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            cls=DateTimeEncoder
        ).encode("utf-8")


class APIError(Exception):
    """Custom API error with structured information"""
    
    def __init__(self, message: str, status_code: int = 500, 
                 error_code: str = None, details: Dict[str, Any] = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or f"API_ERROR_{status_code}"
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(APIError):
    """Validation-specific API error"""
    
    def __init__(self, message: str, field: str = None, value: Any = None):
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["invalid_value"] = str(value)
        
        super().__init__(
            message=message,
            status_code=400,
            error_code="VALIDATION_ERROR",
            details=details
        )


class NotFoundError(APIError):
    """Resource not found error"""
    
    def __init__(self, resource: str, identifier: str = None):
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"
        
        super().__init__(
            message=message,
            status_code=404,
            error_code="NOT_FOUND",
            details={"resource": resource, "identifier": identifier}
        )


class ServiceUnavailableError(APIError):
    """Service unavailable error"""
    
    def __init__(self, service: str, reason: str = None):
        message = f"{service} is currently unavailable"
        if reason:
            message += f": {reason}"
        
        super().__init__(
            message=message,
            status_code=503,
            error_code="SERVICE_UNAVAILABLE",
            details={"service": service, "reason": reason}
        )


class ErrorResponse(BaseModel):
    """Standardized error response format"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    error_code: str = Field(..., description="Machine-readable error code")
    timestamp: datetime = Field(..., description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request identifier for tracking")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class SuccessResponse(BaseModel):
    """Standardized success response format"""
    success: bool = Field(True, description="Success indicator")
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    processing_time_ms: Optional[float] = Field(None, description="Processing time in milliseconds")


def generate_request_id() -> str:
    """Generate a unique request ID for tracking"""
    import uuid
    return str(uuid.uuid4())[:8]


def format_error_response(error: Exception, request_id: str = None) -> JSONResponse:
    """Format an exception into a standardized error response"""
    
    if isinstance(error, APIError):
        # Custom API error
        error_response = ErrorResponse(
            error=error.__class__.__name__,
            message=error.message,
            error_code=error.error_code,
            timestamp=datetime.utcnow(),
            request_id=request_id,
            details=error.details if error.details else None
        )
        return CustomJSONResponse(
            status_code=error.status_code,
            content=error_response.model_dump(exclude_none=True)
        )
    
    elif isinstance(error, HTTPException):
        # FastAPI HTTP exception
        error_response = ErrorResponse(
            error="HTTPException",
            message=error.detail,
            error_code=f"HTTP_{error.status_code}",
            timestamp=datetime.utcnow(),
            request_id=request_id
        )
        return CustomJSONResponse(
            status_code=error.status_code,
            content=error_response.model_dump(exclude_none=True)
        )
    
    else:
        # Unexpected error
        logger.error(f"Unexpected error: {error}", exc_info=True)
        
        error_response = ErrorResponse(
            error="InternalServerError",
            message="An unexpected error occurred",
            error_code="INTERNAL_ERROR",
            timestamp=datetime.utcnow(),
            request_id=request_id,
            details={"error_type": error.__class__.__name__} if logger.isEnabledFor(logging.DEBUG) else None
        )
        return CustomJSONResponse(
            status_code=500,
            content=error_response.model_dump(exclude_none=True)
        )


def format_success_response(message: str, data: Any = None, 
                          processing_time_ms: float = None) -> Dict[str, Any]:
    """Format a successful response"""
    
    # Convert Pydantic models to dict if needed
    if hasattr(data, 'model_dump'):
        data = data.model_dump()
    elif hasattr(data, 'dict'):
        data = data.dict()
    
    response = SuccessResponse(
        message=message,
        data=data,
        processing_time_ms=processing_time_ms
    )
    
    return response.model_dump(exclude_none=True)


def handle_api_errors(func):
    """Decorator to handle API errors and format responses"""
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request_id = generate_request_id()
        start_time = time.time()
        
        try:
            # Add request_id to kwargs if the function accepts it
            import inspect
            sig = inspect.signature(func)
            if 'request_id' in sig.parameters:
                kwargs['request_id'] = request_id
            
            result = await func(*args, **kwargs)
            
            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000
            
            # If result is already a Response, return as-is
            if isinstance(result, Response):
                return result
            
            # If result is a dict with 'success' key, it's already formatted
            if isinstance(result, dict) and 'success' in result:
                return result
            
            # If result is a Pydantic model, return it directly (FastAPI will serialize it)
            if hasattr(result, 'model_dump') or hasattr(result, 'dict'):
                return result
            
            # Otherwise, wrap in success response
            return format_success_response(
                message="Request completed successfully",
                data=result,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            return format_error_response(e, request_id)
    
    return wrapper


def validate_indian_state(state_name: str) -> str:
    """Validate and normalize Indian state name"""
    from models import INDIAN_STATES, normalize_state_name
    
    if not state_name or not state_name.strip():
        raise ValidationError("State name is required", "state", state_name)
    
    normalized = normalize_state_name(state_name)
    
    if normalized.lower() not in INDIAN_STATES:
        raise ValidationError(
            f"Invalid Indian state: {state_name}. Must be a valid Indian state or union territory.",
            "state",
            state_name
        )
    
    return normalized


def validate_time_range(hours_back: int, min_hours: int = 1, max_hours: int = 168) -> int:
    """Validate time range parameter"""
    
    if not isinstance(hours_back, int):
        raise ValidationError("Hours must be an integer", "hours_back", hours_back)
    
    if hours_back < min_hours:
        raise ValidationError(
            f"Hours must be at least {min_hours}",
            "hours_back",
            hours_back
        )
    
    if hours_back > max_hours:
        raise ValidationError(
            f"Hours cannot exceed {max_hours} ({max_hours//24} days)",
            "hours_back", 
            hours_back
        )
    
    return hours_back


def validate_limit(limit: int, min_limit: int = 1, max_limit: int = 1000) -> int:
    """Validate limit parameter"""
    
    if not isinstance(limit, int):
        raise ValidationError("Limit must be an integer", "limit", limit)
    
    if limit < min_limit:
        raise ValidationError(f"Limit must be at least {min_limit}", "limit", limit)
    
    if limit > max_limit:
        raise ValidationError(f"Limit cannot exceed {max_limit}", "limit", limit)
    
    return limit


def sanitize_text_input(text: str, max_length: int = 5000) -> str:
    """Sanitize and validate text input"""
    
    if not text or not text.strip():
        raise ValidationError("Text content is required", "text", text)
    
    # Remove excessive whitespace
    sanitized = ' '.join(text.split())
    
    if len(sanitized) > max_length:
        raise ValidationError(
            f"Text exceeds maximum length of {max_length} characters",
            "text",
            f"{len(sanitized)} characters"
        )
    
    if len(sanitized) < 10:
        raise ValidationError(
            "Text must be at least 10 characters long",
            "text",
            f"{len(sanitized)} characters"
        )
    
    return sanitized


def check_service_availability(service_name: str, is_available: bool, 
                             reason: str = None):
    """Check if a service is available and raise error if not"""
    
    if not is_available:
        raise ServiceUnavailableError(service_name, reason)


def paginate_results(items: List[Any], page: int = 1, page_size: int = 50) -> Dict[str, Any]:
    """Paginate a list of items"""
    
    if page < 1:
        raise ValidationError("Page number must be at least 1", "page", page)
    
    if page_size < 1 or page_size > 200:
        raise ValidationError("Page size must be between 1 and 200", "page_size", page_size)
    
    total_items = len(items)
    total_pages = (total_items + page_size - 1) // page_size
    
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    paginated_items = items[start_idx:end_idx]
    
    return {
        "items": paginated_items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }


def format_processing_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Format processing metadata for API responses"""
    
    # Remove sensitive or internal information
    safe_metadata = {}
    
    safe_keys = [
        "processing_time_ms", "language_detected", "entities_count",
        "claims_count", "satellite_validated", "confidence_score",
        "reality_score", "virality_score", "source_type"
    ]
    
    for key in safe_keys:
        if key in metadata:
            safe_metadata[key] = metadata[key]
    
    return safe_metadata


def create_api_documentation_examples():
    """Create example responses for API documentation"""
    
    return {
        "heatmap_response_example": {
            "states": {
                "Maharashtra": {
                    "event_count": 15,
                    "intensity": 0.75,
                    "avg_virality_score": 0.68,
                    "avg_reality_score": 0.32,
                    "misinformation_risk": 0.46,
                    "dominant_category": "health",
                    "recent_claims": [
                        "Vaccine causes serious side effects in Mumbai hospitals",
                        "Government hiding COVID-19 data from Maharashtra"
                    ],
                    "satellite_validated_count": 8,
                    "last_updated": "2023-06-15T14:30:00Z"
                }
            },
            "total_events": 127,
            "last_updated": "2023-06-15T14:30:00Z",
            "time_range": {
                "start": "2023-06-14T14:30:00Z",
                "end": "2023-06-15T14:30:00Z"
            }
        },
        
        "region_response_example": {
            "state": "Maharashtra",
            "events": [
                {
                    "event_id": "evt_123456",
                    "text": "Breaking: Vaccine side effects reported in Mumbai...",
                    "timestamp": "2023-06-15T12:00:00Z",
                    "source": "news",
                    "virality_score": 0.72,
                    "reality_score": 0.28,
                    "entities": ["vaccine", "Mumbai", "side effects"],
                    "claims_count": 2,
                    "satellite_validated": True,
                    "primary_claim": {
                        "text": "Vaccine causes serious side effects",
                        "category": "health",
                        "confidence": 0.85
                    }
                }
            ],
            "summary": {
                "average_virality_score": 0.68,
                "average_reality_score": 0.32,
                "misinformation_risk": 0.46,
                "events_by_source": {"news": 8, "social": 7},
                "claims_by_category": {"health": 12, "politics": 3}
            },
            "total_count": 15
        },
        
        "error_response_example": {
            "error": "ValidationError",
            "message": "Invalid Indian state: California",
            "error_code": "VALIDATION_ERROR",
            "timestamp": "2023-06-15T14:30:00Z",
            "request_id": "req_abc123",
            "details": {
                "field": "state",
                "invalid_value": "California"
            }
        }
    }


# Rate limiting utilities
class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self.requests = {}
        self.limits = {
            "default": {"requests": 100, "window": 3600},  # 100 requests per hour
            "heatmap": {"requests": 60, "window": 3600},   # 60 requests per hour
            "ingest": {"requests": 10, "window": 3600}     # 10 requests per hour
        }
    
    def is_allowed(self, client_id: str, endpoint_type: str = "default") -> bool:
        """Check if request is allowed under rate limits"""
        
        now = time.time()
        limit_config = self.limits.get(endpoint_type, self.limits["default"])
        
        # Clean old entries
        if client_id in self.requests:
            self.requests[client_id] = [
                req_time for req_time in self.requests[client_id]
                if now - req_time < limit_config["window"]
            ]
        else:
            self.requests[client_id] = []
        
        # Check limit
        if len(self.requests[client_id]) >= limit_config["requests"]:
            return False
        
        # Add current request
        self.requests[client_id].append(now)
        return True


# Global rate limiter instance
rate_limiter = RateLimiter()