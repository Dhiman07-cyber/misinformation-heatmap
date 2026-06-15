from abc import ABC, abstractmethod
from typing import List, Dict

class DataIngestor(ABC):
    """
    Abstract base class for all data ingestors (RSS, Twitter, Telegram, etc.).
    """
    
    @abstractmethod
    async def fetch_data(self) -> List[Dict]:
        """
        Fetch data from the source.
        Must return a list of dictionaries, where each dictionary represents an event.
        Expected keys in each dictionary:
        - source: string (e.g., 'Times of India', 'Twitter', 'Telegram')
        - title: string
        - content: string
        - url: string (optional)
        - timestamp: datetime
        - reliability: float (optional, default will be assigned if missing)
        """
        pass
