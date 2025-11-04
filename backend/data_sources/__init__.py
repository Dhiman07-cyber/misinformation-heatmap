"""
Data Sources Package - Modular Data Ingestion Framework
Provides extensible plugin-based architecture for ingesting data from various sources.
"""

from .registry import DataSourceRegistry
from .base.base_connector import BaseDataConnector, RawEvent
from .coordinator import IngestionCoordinator

__all__ = [
    'DataSourceRegistry',
    'BaseDataConnector', 
    'RawEvent',
    'IngestionCoordinator'
]