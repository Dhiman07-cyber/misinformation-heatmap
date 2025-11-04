"""
FastAPI backend application for the Real-time Misinformation Heatmap system.
Provides REST API endpoints for heatmap data, regional details, test data injection,
and system health monitoring with CORS support for frontend integration.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

# FastAPI imports
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query, Path as PathParam, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

# Pydantic models
from pydantic import BaseModel, Field, validator
from typing_extensions import Annotated

# Local imports
from config import config
from models import (
    ProcessedEvent, EventSource, LanguageCode, ClaimCategory,
    EventCreateRequest, HeatmapResponse, RegionResponse, HealthCheckResponse,
    INDIAN_STATES, validate_indian_state, normalize_state_name
)
from database import database
from ingestion_manager import unified_ingestion_manager
from processor import RawEvent
from heatmap_aggregator import heatmap_aggregator
from api_utils import (
    handle_api_errors, format_error_response, format_success_response,
    validate_indian_state as validate_state, validate_time_range, validate_limit,
    sanitize_text_input, check_service_availability, APIError, ValidationError,
    NotFoundError, ServiceUnavailableError, rate_limiter
)

# Import new data ingestion service
from data_ingestion_service import get_ingestion_service, initialize_ingestion_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Real-time Misinformation Heatmap API",
    description="API for real-time misinformation detection and visualization across India",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
api_config = config.get_api_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=api_config["cors_origins"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Global state
app_state = {
    "initialized": False,
    "startup_time": None,
    "ingestion_running": False
}


# Pydantic models for API requests/responses
class TestEventRequest(BaseModel):
    """Request model for test event injection"""
    text: str = Field(..., min_length=10, max_length=5000, description="Event text content")
    source: EventSource = Field(default=EventSource.MANUAL, description="Event source type")
    location: Optional[str] = Field(None, description="Location hint (Indian state/city)")
    category: Optional[str] = Field(None, description="Event category")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    @validator('location')
    def validate_location(cls, v):
        if v and not any(loc.lower() in v.lower() for loc in INDIAN_STATES.keys()):
            logger.warning(f"Location '{v}' not recognized as Indian location")
        return v


class HeatmapDataResponse(BaseModel):
    """Response model for heatmap data"""
    states: Dict[str, Dict[str, Any]] = Field(..., description="State-wise misinformation data")
    total_events: int = Field(..., description="Total number of events")
    last_updated: datetime = Field(..., description="Last update timestamp")
    time_range: Dict[str, str] = Field(..., description="Time range of data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class RegionDetailResponse(BaseModel):
    """Response model for region details"""
    state: str = Field(..., description="State name")
    events: List[Dict[str, Any]] = Field(..., description="Recent events in the region")
    summary: Dict[str, Any] = Field(..., description="Regional summary statistics")
    total_count: int = Field(..., description="Total event count")
    time_range: Dict[str, str] = Field(..., description="Time range of data")


class SystemStatsResponse(BaseModel):
    """Response model for system statistics"""
    ingestion_stats: Dict[str, Any] = Field(..., description="Ingestion pipeline statistics")
    database_stats: Dict[str, Any] = Field(..., description="Database statistics")
    processing_stats: Dict[str, Any] = Field(..., description="Processing pipeline statistics")
    system_health: Dict[str, Any] = Field(..., description="System health information")


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize application components on startup"""
    try:
        logger.info("Starting Real-time Misinformation Heatmap API...")
        
        # Initialize database
        db_success = await database.initialize()
        if not db_success:
            logger.error("Failed to initialize database")
            return
        
        # Initialize ingestion manager
        ingestion_success = await unified_ingestion_manager.initialize()
        if not ingestion_success:
            logger.error("Failed to initialize ingestion manager")
            return
        
        # Mount static files for frontend
        static_path = api_config.get("static_files_path")
        if static_path and Path(static_path).exists():
            app.mount("/static", StaticFiles(directory=static_path), name="static")
            logger.info(f"Mounted static files from {static_path}")
        
        app_state["initialized"] = True
        app_state["startup_time"] = datetime.utcnow()
        
        logger.info("API startup completed successfully")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        app_state["initialized"] = False


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    try:
        logger.info("Shutting down API...")
        
        # Stop ingestion if running
        if app_state.get("ingestion_running"):
            await unified_ingestion_manager.stop_continuous_ingestion()
        
        app_state["initialized"] = False
        logger.info("API shutdown completed")
        
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


# Dependency functions
async def get_database():
    """Dependency to get database instance"""
    if not app_state["initialized"]:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return database


async def get_ingestion_manager():
    """Dependency to get ingestion manager instance"""
    if not app_state["initialized"]:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return unified_ingestion_manager


# Core API endpoints
@app.get("/", response_class=FileResponse)
async def serve_frontend():
    """Serve the frontend application"""
    static_path = api_config.get("static_files_path")
    if static_path:
        index_file = Path(static_path) / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
    
    return JSONResponse({
        "message": "Real-time Misinformation Heatmap API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running" if app_state["initialized"] else "initializing"
    })


@app.get("/api/info")
async def get_api_info():
    """Get API information and status"""
    return JSONResponse({
        "message": "Real-time Misinformation Heatmap API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "status": "running" if app_state["initialized"] else "initializing",
        "mode": config.mode,
        "startup_time": app_state["startup_time"].isoformat() if app_state["startup_time"] else None
    })


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """System health check endpoint"""
    try:
        # Get component health status from existing manager
        health_data = await unified_ingestion_manager.health_check()
        
        # Get data source health from new ingestion service
        try:
            ingestion_service = get_ingestion_service(config)
            data_source_health = await ingestion_service.health_check()
            
            # Add data source information to health data
            health_data["data_sources"] = {
                "status": data_source_health.get("status", "unknown"),
                "total_sources": len(data_source_health.get("sources", {})),
                "healthy_sources": len([
                    s for s in data_source_health.get("sources", {}).values() 
                    if s.get("status") == "healthy"
                ]),
                "ingestion_stats": data_source_health.get("statistics", {})
            }
        except Exception as e:
            logger.warning(f"Could not get data source health: {e}")
            health_data["data_sources"] = {"status": "unknown", "error": str(e)}
        
        # Add API-specific health info
        health_data.update({
            "api_status": "healthy" if app_state["initialized"] else "initializing",
            "startup_time": app_state["startup_time"].isoformat() if app_state["startup_time"] else None,
            "ingestion_running": app_state.get("ingestion_running", False)
        })
        
        return HealthCheckResponse(
            status=health_data.get("status", "unknown"),
            mode=health_data.get("mode", "unknown"),
            timestamp=datetime.utcnow(),
            components=health_data.get("components", {})
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthCheckResponse(
            status="unhealthy",
            mode="unknown",
            timestamp=datetime.utcnow(),
            components={"error": str(e)}
        )


@app.get("/heatmap", response_model=HeatmapDataResponse)
@handle_api_errors
async def get_heatmap_data(
    request: Request,
    hours_back: int = Query(24, ge=1, le=168, description="Hours of data to include (1-168)"),
    use_cache: bool = Query(True, description="Whether to use cached data"),
    db: database = Depends(get_database)
):
    """
    Get aggregated heatmap data for all Indian states.
    Returns misinformation intensity, event counts, and reality scores by state.
    """
    # Rate limiting
    client_id = request.client.host
    if not rate_limiter.is_allowed(client_id, "heatmap"):
        raise APIError("Rate limit exceeded", 429, "RATE_LIMIT_EXCEEDED")
    
    # Validate parameters
    hours_back = validate_time_range(hours_back)
    
    logger.info(f"Fetching heatmap data for last {hours_back} hours")
    
    # Check service availability
    check_service_availability("Database", True)  # Assume available if no exception
    
    # Get heatmap data using aggregator
    heatmap_data = await heatmap_aggregator.generate_heatmap_data(hours_back, use_cache)
    
    if not heatmap_data:
        logger.warning("No heatmap data available")
        heatmap_data = {}
    
    # Calculate time range
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours_back)
    
    # Count total events
    total_events = sum(state_data.get("event_count", 0) for state_data in heatmap_data.values())
    
    # Add metadata
    metadata = {
        "data_freshness": "real-time" if not use_cache else "cached",
        "coverage": f"{len(heatmap_data)} states",
        "processing_mode": config.mode,
        "cache_used": use_cache
    }
    
    return HeatmapDataResponse(
        states=heatmap_data,
        total_events=total_events,
        last_updated=end_time,
        time_range={
            "start": start_time.isoformat(),
            "end": end_time.isoformat()
        },
        metadata=metadata
    )


@app.get("/region/{state}", response_model=RegionDetailResponse)
@handle_api_errors
async def get_region_details(
    request: Request,
    state: str = PathParam(..., description="Indian state name"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of events to return"),
    hours_back: int = Query(24, ge=1, le=168, description="Hours of data to include"),
    db: database = Depends(get_database)
):
    """
    Get detailed information for a specific Indian state/region.
    Returns recent events, claims, and regional statistics.
    """
    # Rate limiting
    client_id = request.client.host
    if not rate_limiter.is_allowed(client_id, "default"):
        raise APIError("Rate limit exceeded", 429, "RATE_LIMIT_EXCEEDED")
    
    # Validate parameters
    normalized_state = validate_state(state)
    limit = validate_limit(limit, max_limit=200)
    hours_back = validate_time_range(hours_back)
    
    logger.info(f"Fetching region details for {normalized_state}")
    
    # Get events for the region
    events = await db.get_events_by_region(normalized_state, limit)
    
    if not events:
        # Return empty response for states with no data
        return RegionDetailResponse(
            state=normalized_state,
            events=[],
            summary={
                "average_virality_score": 0.0,
                "average_reality_score": 0.5,
                "misinformation_risk": 0.0,
                "events_by_source": {},
                "claims_by_category": {},
                "satellite_validated_count": 0
            },
            total_count=0,
            time_range={
                "start": (datetime.utcnow() - timedelta(hours=hours_back)).isoformat(),
                "end": datetime.utcnow().isoformat()
            }
        )
    
    # Filter by time range
    cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
    recent_events = [
        event for event in events 
        if event.timestamp >= cutoff_time
    ]
    
    # Convert events to API format
    event_data = []
    for event in recent_events:
        event_dict = {
            "event_id": event.event_id,
            "text": event.original_text[:200] + "..." if len(event.original_text) > 200 else event.original_text,
            "timestamp": event.timestamp.isoformat(),
            "source": event.source.value,
            "virality_score": event.virality_score,
            "reality_score": event.get_reality_score(),
            "entities": event.entities[:5],  # Limit entities
            "claims_count": len(event.claims),
            "satellite_validated": event.satellite is not None and event.satellite.confidence > 0.5
        }
        
        # Add primary claim if available
        primary_claim = event.get_primary_claim()
        if primary_claim:
            event_dict["primary_claim"] = {
                "text": primary_claim.text[:100] + "..." if len(primary_claim.text) > 100 else primary_claim.text,
                "category": primary_claim.category.value,
                "confidence": primary_claim.confidence
            }
        
        event_data.append(event_dict)
    
    # Calculate summary statistics
    if recent_events:
        avg_virality = sum(event.virality_score for event in recent_events) / len(recent_events)
        avg_reality = sum(event.get_reality_score() for event in recent_events) / len(recent_events)
        
        # Count by source
        source_counts = {}
        for event in recent_events:
            source = event.source.value
            source_counts[source] = source_counts.get(source, 0) + 1
        
        # Count by category
        category_counts = {}
        for event in recent_events:
            for claim in event.claims:
                category = claim.category.value
                category_counts[category] = category_counts.get(category, 0) + 1
    else:
        avg_virality = 0.0
        avg_reality = 0.5
        source_counts = {}
        category_counts = {}
    
    summary = {
        "average_virality_score": round(avg_virality, 3),
        "average_reality_score": round(avg_reality, 3),
        "misinformation_risk": round(avg_virality * (1 - avg_reality), 3),
        "events_by_source": source_counts,
        "claims_by_category": category_counts,
        "satellite_validated_count": sum(1 for event in recent_events if event.satellite and event.satellite.confidence > 0.5)
    }
    
    # Time range
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours_back)
        
    return RegionDetailResponse(
        state=normalized_state,
        events=event_data,
        summary=summary,
        total_count=len(recent_events),
        time_range={
            "start": start_time.isoformat(),
            "end": end_time.isoformat()
        }
    )


@app.post("/ingest/test")
@handle_api_errors
async def ingest_test_data(
    request_obj: Request,
    request: TestEventRequest,
    background_tasks: BackgroundTasks,
    ingestion_manager = Depends(get_ingestion_manager)
):
    """
    Inject test data for development and testing purposes.
    Processes the event through the complete pipeline.
    """
    # Rate limiting for ingestion endpoint
    client_id = request_obj.client.host
    if not rate_limiter.is_allowed(client_id, "ingest"):
        raise APIError("Rate limit exceeded for test ingestion", 429, "RATE_LIMIT_EXCEEDED")
    
    # Validate and sanitize input
    sanitized_text = sanitize_text_input(request.text)
    
    logger.info(f"Ingesting test event: {sanitized_text[:50]}...")
    
    # Check service availability
    check_service_availability("Ingestion Manager", ingestion_manager.initialized)
    
    # Create and process the test event
    processed_event = await ingestion_manager.ingest_single_event(
        "custom",
        text=sanitized_text,
        location=request.location or "",
        category=request.category or "",
        metadata=request.metadata or {}
    )
    
    if not processed_event:
        raise APIError("Failed to process test event", 500, "PROCESSING_FAILED")
    
    # Return processing results
    response_data = {
        "event_id": processed_event.event_id,
        "status": "processed",
        "processing_results": {
            "language_detected": processed_event.lang.value,
            "region_extracted": processed_event.region_hint,
            "entities_found": len(processed_event.entities),
            "claims_extracted": len(processed_event.claims),
            "virality_score": round(processed_event.virality_score, 3),
            "reality_score": round(processed_event.get_reality_score(), 3),
            "satellite_validated": processed_event.satellite is not None and processed_event.satellite.confidence > 0.5
        },
        "timestamp": processed_event.timestamp.isoformat()
    }
    
    # Add primary claim info if available
    primary_claim = processed_event.get_primary_claim()
    if primary_claim:
        response_data["processing_results"]["primary_claim"] = {
            "text": primary_claim.text[:200] + "..." if len(primary_claim.text) > 200 else primary_claim.text,
            "category": primary_claim.category.value,
            "confidence": round(primary_claim.confidence, 3)
        }
    
    return JSONResponse(content=response_data, status_code=201)


@app.get("/stats", response_model=SystemStatsResponse)
async def get_system_stats(
    ingestion_manager = Depends(get_ingestion_manager),
    db: database = Depends(get_database)
):
    """
    Get comprehensive system statistics including ingestion, processing, and database metrics.
    """
    try:
        # Get ingestion statistics
        ingestion_stats = ingestion_manager.get_stats()
        
        # Get database statistics
        db_stats = await db.get_stats()
        
        # Get system health
        health_info = await ingestion_manager.health_check()
        
        # Compile processing stats
        processing_stats = {
            "average_processing_time_ms": ingestion_stats.average_processing_time_ms,
            "processing_errors": ingestion_stats.processing_errors,
            "events_processed": ingestion_stats.events_processed,
            "events_stored": ingestion_stats.events_stored,
            "last_ingestion": ingestion_stats.last_ingestion_time.isoformat() if ingestion_stats.last_ingestion_time else None
        }
        
        return SystemStatsResponse(
            ingestion_stats=ingestion_stats.__dict__,
            database_stats=db_stats,
            processing_stats=processing_stats,
            system_health=health_info
        )
        
    except Exception as e:
        logger.error(f"Failed to get system stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve system statistics: {str(e)}")


# Administrative endpoints
@app.post("/admin/ingestion/start")
async def start_continuous_ingestion(
    background_tasks: BackgroundTasks,
    interval_seconds: int = Query(300, ge=60, le=3600, description="Ingestion interval in seconds"),
    ingestion_manager = Depends(get_ingestion_manager)
):
    """Start continuous data ingestion (admin only)"""
    try:
        if app_state.get("ingestion_running"):
            return {"status": "already_running", "message": "Continuous ingestion is already active"}
        
        # Start ingestion in background
        background_tasks.add_task(
            unified_ingestion_manager.start_continuous_ingestion,
            interval_seconds
        )
        
        app_state["ingestion_running"] = True
        
        return {
            "status": "started",
            "message": f"Continuous ingestion started with {interval_seconds}s interval",
            "interval_seconds": interval_seconds
        }
        
    except Exception as e:
        logger.error(f"Failed to start ingestion: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start ingestion: {str(e)}")


@app.post("/admin/ingestion/stop")
async def stop_continuous_ingestion(
    ingestion_manager = Depends(get_ingestion_manager)
):
    """Stop continuous data ingestion (admin only)"""
    try:
        if not app_state.get("ingestion_running"):
            return {"status": "not_running", "message": "Continuous ingestion is not active"}
        
        await ingestion_manager.stop_continuous_ingestion()
        app_state["ingestion_running"] = False
        
        return {"status": "stopped", "message": "Continuous ingestion stopped"}
        
    except Exception as e:
        logger.error(f"Failed to stop ingestion: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop ingestion: {str(e)}")


@app.get("/admin/reset-stats")
async def reset_statistics(
    ingestion_manager = Depends(get_ingestion_manager)
):
    """Reset ingestion and processing statistics (admin only)"""
    try:
        ingestion_manager.reset_stats()
        return {"status": "reset", "message": "Statistics have been reset"}
        
    except Exception as e:
        logger.error(f"Failed to reset stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset statistics: {str(e)}")


# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Real-time Misinformation Heatmap API",
        version="1.0.0",
        description="API for real-time misinformation detection and visualization across India",
        routes=app.routes,
    )
    
    # Add custom info
    openapi_schema["info"]["contact"] = {
        "name": "Misinformation Heatmap Team",
        "email": "contact@misinfo-heatmap.com"
    }
    
    openapi_schema["info"]["license"] = {
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested resource was not found",
            "path": str(request.url.path)
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# ============================================================================
# DATA SOURCE MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/api/data-sources", 
         summary="Get all data sources",
         description="Retrieve information about all configured data sources")
@handle_api_errors
async def get_data_sources():
    """Get all configured data sources with their status."""
    try:
        ingestion_service = get_ingestion_service(config)
        
        # Get source status
        source_status = ingestion_service.get_source_status()
        
        # Get configuration stats
        config_stats = ingestion_service.config_manager.get_config_stats()
        
        return format_success_response({
            "sources": source_status,
            "statistics": config_stats,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get data sources: {e}")
        raise ServiceUnavailableError("Failed to retrieve data sources")


@app.get("/api/data-sources/{source_id}",
         summary="Get specific data source",
         description="Retrieve detailed information about a specific data source")
@handle_api_errors
async def get_data_source(source_id: str = PathParam(..., description="Data source identifier")):
    """Get detailed information about a specific data source."""
    try:
        ingestion_service = get_ingestion_service(config)
        
        # Get source configuration
        source_config = ingestion_service.config_manager.get_source_config(source_id)
        if not source_config:
            raise NotFoundError(f"Data source not found: {source_id}")
        
        # Get source status
        source_status = ingestion_service.get_source_status()
        current_status = source_status.get(source_id, {})
        
        return format_success_response({
            "source_id": source_id,
            "configuration": source_config.to_dict(),
            "status": current_status,
            "timestamp": datetime.now().isoformat()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get data source {source_id}: {e}")
        raise ServiceUnavailableError(f"Failed to retrieve data source: {source_id}")


@app.post("/api/data-sources/{source_id}/enable",
          summary="Enable data source",
          description="Enable a specific data source for ingestion")
@handle_api_errors
async def enable_data_source(source_id: str = PathParam(..., description="Data source identifier")):
    """Enable a data source."""
    try:
        ingestion_service = get_ingestion_service(config)
        
        success = ingestion_service.enable_source(source_id)
        if not success:
            raise NotFoundError(f"Data source not found: {source_id}")
        
        return format_success_response({
            "message": f"Data source {source_id} enabled successfully",
            "source_id": source_id,
            "enabled": True,
            "timestamp": datetime.now().isoformat()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to enable data source {source_id}: {e}")
        raise ServiceUnavailableError(f"Failed to enable data source: {source_id}")


@app.post("/api/data-sources/{source_id}/disable",
          summary="Disable data source", 
          description="Disable a specific data source from ingestion")
@handle_api_errors
async def disable_data_source(source_id: str = PathParam(..., description="Data source identifier")):
    """Disable a data source."""
    try:
        ingestion_service = get_ingestion_service(config)
        
        success = ingestion_service.disable_source(source_id)
        if not success:
            raise NotFoundError(f"Data source not found: {source_id}")
        
        return format_success_response({
            "message": f"Data source {source_id} disabled successfully",
            "source_id": source_id,
            "enabled": False,
            "timestamp": datetime.now().isoformat()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disable data source {source_id}: {e}")
        raise ServiceUnavailableError(f"Failed to disable data source: {source_id}")


@app.post("/api/data-sources/fetch-all",
          summary="Manual fetch from all sources",
          description="Manually trigger data fetching from all enabled sources")
@handle_api_errors
async def manual_fetch_all_sources():
    """Manually trigger fetch from all enabled data sources."""
    try:
        ingestion_service = get_ingestion_service(config)
        
        # Trigger manual fetch
        results = await ingestion_service.manual_fetch_all_sources()
        
        # Calculate statistics
        total_events = sum(len(events) for events in results.values())
        source_counts = {source_id: len(events) for source_id, events in results.items()}
        
        return format_success_response({
            "message": "Manual fetch completed successfully",
            "total_events": total_events,
            "source_counts": source_counts,
            "sources_fetched": len(results),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Manual fetch failed: {e}")
        raise ServiceUnavailableError("Manual fetch operation failed")


@app.post("/api/data-sources/{source_id}/fetch",
          summary="Manual fetch from specific source",
          description="Manually trigger data fetching from a specific source")
@handle_api_errors
async def manual_fetch_source(source_id: str = PathParam(..., description="Data source identifier")):
    """Manually trigger fetch from a specific data source."""
    try:
        ingestion_service = get_ingestion_service(config)
        
        # Trigger manual fetch for specific source
        events = await ingestion_service.fetch_from_source(source_id)
        
        return format_success_response({
            "message": f"Manual fetch from {source_id} completed successfully",
            "source_id": source_id,
            "events_fetched": len(events),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Manual fetch from {source_id} failed: {e}")
        raise ServiceUnavailableError(f"Manual fetch from {source_id} failed")


@app.get("/api/data-sources/health",
         summary="Data sources health check",
         description="Check health status of all data sources")
@handle_api_errors
async def data_sources_health_check():
    """Perform health check on all data sources."""
    try:
        ingestion_service = get_ingestion_service(config)
        
        # Perform health check
        health_status = await ingestion_service.health_check()
        
        return format_success_response(health_status)
        
    except Exception as e:
        logger.error(f"Data sources health check failed: {e}")
        raise ServiceUnavailableError("Health check operation failed")


@app.post("/api/data-sources/reload-config",
          summary="Reload data sources configuration",
          description="Reload data sources configuration from file")
@handle_api_errors
async def reload_data_sources_config():
    """Reload data sources configuration."""
    try:
        ingestion_service = get_ingestion_service(config)
        
        success = await ingestion_service.reload_configuration()
        if not success:
            raise ServiceUnavailableError("Failed to reload configuration")
        
        # Get updated stats
        config_stats = ingestion_service.config_manager.get_config_stats()
        
        return format_success_response({
            "message": "Configuration reloaded successfully",
            "statistics": config_stats,
            "timestamp": datetime.now().isoformat()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Configuration reload failed: {e}")
        raise ServiceUnavailableError("Configuration reload operation failed")


@app.get("/api/data-sources/statistics",
         summary="Get data sources statistics",
         description="Get comprehensive statistics about data sources and ingestion")
@handle_api_errors
async def get_data_sources_statistics():
    """Get comprehensive data sources statistics."""
    try:
        ingestion_service = get_ingestion_service(config)
        
        # Get service statistics
        service_stats = ingestion_service.get_service_stats()
        
        return format_success_response({
            "statistics": service_stats,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get data sources statistics: {e}")
        raise ServiceUnavailableError("Failed to retrieve statistics")


# ============================================================================
# STARTUP AND INITIALIZATION
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    try:
        logger.info("Starting up misinformation heatmap API...")
        
        # Initialize data ingestion service
        ingestion_service = await initialize_ingestion_service(config)
        
        # Start continuous ingestion if enabled
        ingestion_config = config.get_ingestion_config()
        if ingestion_config.get("auto_start", True):
            await ingestion_service.start_continuous_ingestion()
            app_state["ingestion_running"] = True
            logger.info("Started continuous data ingestion")
        
        app_state["initialized"] = True
        app_state["startup_time"] = datetime.now()
        
        logger.info("API startup completed successfully")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    try:
        logger.info("Shutting down misinformation heatmap API...")
        
        # Stop data ingestion service
        if app_state.get("ingestion_running"):
            ingestion_service = get_ingestion_service(config)
            await ingestion_service.stop_continuous_ingestion()
            logger.info("Stopped continuous data ingestion")
        
        logger.info("API shutdown completed")
        
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


if __name__ == "__main__":
    import uvicorn
    
    # Run the application
    uvicorn.run(
        "api:app",
        host=api_config["host"],
        port=api_config["port"],
        reload=api_config.get("debug", False),
        log_level="info"
    )