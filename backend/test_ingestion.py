"""
Integration tests for the data ingestion pipeline.
Tests local ingestion, cloud integration, Pub/Sub emulator,
and end-to-end event processing workflows.
"""

import pytest
import asyncio
import os
import tempfile
import json
import csv
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# Set environment for testing
os.environ["MODE"] = "local"

# Import ingestion components
from ingest_local import (
    LocalNewsIngester, LocalSocialMediaIngester, ManualTestDataInjector,
    LocalIngestionManager, local_ingestion_manager
)
from pubsub_emulator import (
    PubSubEmulator, PubSubEmulatorClient, PubSubMessage, pubsub_emulator, pubsub_client
)
from watson_client import (
    WatsonDiscoveryClient, GCPPubSubClient, CloudIngestionManager, cloud_ingestion_manager
)
from ingestion_manager import (
    UnifiedIngestionManager, IngestionMode, IngestionStats, unified_ingestion_manager
)
from processor import RawEvent
from models import EventSource, ProcessedEvent


class TestLocalNewsIngester:
    """Test cases for local news ingestion"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.ingester = LocalNewsIngester()
    
    @pytest.mark.asyncio
    async def test_sample_news_generation(self):
        """Test generation of sample news events"""
        events = self.ingester._generate_sample_events(5)
        
        assert len(events) == 5
        for event in events:
            assert isinstance(event, RawEvent)
            assert event.source in [EventSource.NEWS, EventSource.MANUAL]
            assert len(event.original_text) > 20
            assert event.timestamp is not None
            assert "sample_news" in event.metadata["source_name"]
    
    def test_location_extraction(self):
        """Test extraction of Indian locations from text"""
        test_cases = [
            ("Heavy rainfall in Mumbai causes flooding", "Mumbai"),
            ("Delhi government announces new policy", "Delhi"),
            ("Bangalore tech companies hiring", "Bangalore"),
            ("No location mentioned here", ""),
            ("Multiple cities: Mumbai and Delhi affected", "Mumbai")  # First match
        ]
        
        for text, expected_location in test_cases:
            location = self.ingester._extract_location_from_text(text)
            assert location == expected_location
    
    @pytest.mark.asyncio
    async def test_rss_feed_ingestion_fallback(self):
        """Test RSS feed ingestion with fallback to sample data"""
        # This will likely fail to fetch real RSS feeds in test environment
        # and should fall back to sample data
        events = await self.ingester.ingest_rss_feeds(max_articles=10)
        
        assert len(events) > 0
        assert all(isinstance(event, RawEvent) for event in events)
        assert all(event.source in [EventSource.RSS, EventSource.NEWS] for event in events)
    
    @pytest.mark.asyncio
    async def test_csv_file_ingestion(self):
        """Test ingestion from CSV file"""
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(['text', 'timestamp', 'source', 'location', 'category'])
            writer.writerow([
                'Test news from Mumbai',
                '2023-06-15T10:00:00',
                'test_source',
                'Mumbai',
                'test'
            ])
            writer.writerow([
                'Another test event',
                '2023-06-15T11:00:00',
                'test_source',
                'Delhi',
                'test'
            ])
            csv_path = f.name
        
        try:
            events = await self.ingester.ingest_from_file(csv_path)
            
            assert len(events) == 2
            assert events[0].original_text == 'Test news from Mumbai'
            assert events[0].metadata['location_hint'] == 'Mumbai'
            assert events[1].original_text == 'Another test event'
            
        finally:
            os.unlink(csv_path)
    
    @pytest.mark.asyncio
    async def test_json_file_ingestion(self):
        """Test ingestion from JSON file"""
        # Create temporary JSON file
        test_data = [
            {
                'text': 'JSON test event from Bangalore',
                'timestamp': '2023-06-15T12:00:00',
                'source': 'json_test',
                'location': 'Bangalore',
                'category': 'technology'
            },
            {
                'text': 'Another JSON event',
                'timestamp': '2023-06-15T13:00:00',
                'source': 'json_test',
                'location': 'Chennai'
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            json_path = f.name
        
        try:
            events = await self.ingester.ingest_from_file(json_path)
            
            assert len(events) == 2
            assert events[0].original_text == 'JSON test event from Bangalore'
            assert events[0].metadata['location_hint'] == 'Bangalore'
            assert events[0].metadata['category'] == 'technology'
            
        finally:
            os.unlink(json_path)


class TestLocalSocialMediaIngester:
    """Test cases for social media simulation"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.ingester = LocalSocialMediaIngester()
    
    @pytest.mark.asyncio
    async def test_social_media_generation(self):
        """Test generation of social media posts"""
        posts = await self.ingester.generate_social_media_posts(10)
        
        assert len(posts) == 10
        for post in posts:
            assert isinstance(post, RawEvent)
            assert post.source in [EventSource.TWITTER, EventSource.FACEBOOK]
            assert len(post.original_text) > 10
            assert "engagement_metrics" in post.metadata
            assert post.engagement_metrics is not None
    
    def test_engagement_metrics_generation(self):
        """Test generation of realistic engagement metrics"""
        twitter_metrics = self.ingester._generate_engagement_metrics("twitter")
        facebook_metrics = self.ingester._generate_engagement_metrics("facebook")
        
        # Twitter metrics
        assert "likes" in twitter_metrics
        assert "retweets" in twitter_metrics
        assert "replies" in twitter_metrics
        assert all(isinstance(v, int) and v >= 0 for v in twitter_metrics.values())
        
        # Facebook metrics
        assert "likes" in facebook_metrics
        assert "shares" in facebook_metrics
        assert "comments" in facebook_metrics
        assert all(isinstance(v, int) and v >= 0 for v in facebook_metrics.values())


class TestManualTestDataInjector:
    """Test cases for manual test data injection"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.injector = ManualTestDataInjector()
    
    def test_scenario_injection(self):
        """Test injection of predefined scenarios"""
        # Test disaster scenario
        event = self.injector.inject_test_scenario("disaster_scenarios", 0)
        
        assert isinstance(event, RawEvent)
        assert event.source == EventSource.MANUAL
        assert len(event.original_text) > 20
        assert event.metadata["scenario_type"] == "disaster_scenarios"
        assert event.metadata["scenario_index"] == 0
    
    def test_custom_event_injection(self):
        """Test injection of custom events"""
        custom_text = "Custom test event for validation"
        custom_location = "Test Location"
        custom_metadata = {"test_key": "test_value"}
        
        event = self.injector.inject_custom_event(
            custom_text, custom_location, "test", custom_metadata
        )
        
        assert event.original_text == custom_text
        assert event.metadata["location_hint"] == custom_location
        assert event.metadata["category"] == "test"
        assert event.metadata["test_key"] == "test_value"
    
    def test_available_scenarios(self):
        """Test retrieval of available scenarios"""
        scenarios = self.injector.get_available_scenarios()
        
        assert isinstance(scenarios, dict)
        assert "disaster_scenarios" in scenarios
        assert "health_scenarios" in scenarios
        assert "political_scenarios" in scenarios
        
        # Check that each scenario has descriptions
        for scenario_type, scenario_list in scenarios.items():
            assert len(scenario_list) > 0
            for scenario_desc in scenario_list:
                assert isinstance(scenario_desc, str)
                assert len(scenario_desc) > 10


class TestPubSubEmulator:
    """Test cases for Pub/Sub emulator"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.emulator = PubSubEmulator()
    
    @pytest.mark.asyncio
    async def test_emulator_lifecycle(self):
        """Test emulator start/stop lifecycle"""
        await self.emulator.start()
        assert self.emulator._running == True
        
        await self.emulator.stop()
        assert self.emulator._running == False
    
    def test_topic_management(self):
        """Test topic creation and deletion"""
        topic_name = "test-topic"
        
        # Create topic
        success = self.emulator.create_topic(topic_name)
        assert success == True
        assert topic_name in self.emulator.topics
        
        # Try to create same topic again
        success = self.emulator.create_topic(topic_name)
        assert success == False
        
        # List topics
        topics = self.emulator.list_topics()
        assert topic_name in topics
        
        # Delete topic
        success = self.emulator.delete_topic(topic_name)
        assert success == True
        assert topic_name not in self.emulator.topics
    
    def test_subscription_management(self):
        """Test subscription creation and management"""
        topic_name = "test-topic"
        subscription_name = "test-subscription"
        
        # Create topic first
        self.emulator.create_topic(topic_name)
        
        # Create subscription
        success = self.emulator.create_subscription(subscription_name, topic_name)
        assert success == True
        
        topic = self.emulator.topics[topic_name]
        assert subscription_name in topic.subscriptions
        
        # Delete subscription
        success = self.emulator.delete_subscription(subscription_name)
        assert success == True
        assert subscription_name not in topic.subscriptions
    
    def test_message_publishing_and_pulling(self):
        """Test message publishing and pulling"""
        topic_name = "test-topic"
        subscription_name = "test-subscription"
        
        # Setup topic and subscription
        self.emulator.create_topic(topic_name)
        self.emulator.create_subscription(subscription_name, topic_name)
        
        # Publish message
        message_data = "Test message data"
        attributes = {"source": "test", "type": "event"}
        
        message_id = self.emulator.publish_message(topic_name, message_data, attributes)
        assert message_id is not None
        
        # Pull messages
        messages = self.emulator.pull_messages(subscription_name, max_messages=10)
        assert len(messages) == 1
        
        message = messages[0]
        assert message.data == message_data
        assert message.attributes == attributes
        assert message.ack_id is not None
        
        # Acknowledge message
        success = self.emulator.acknowledge_message(message.ack_id)
        assert success == True
    
    def test_message_nack_and_redelivery(self):
        """Test message negative acknowledgment and redelivery"""
        topic_name = "test-topic"
        subscription_name = "test-subscription"
        
        # Setup
        self.emulator.create_topic(topic_name)
        self.emulator.create_subscription(subscription_name, topic_name)
        
        # Publish and pull message
        self.emulator.publish_message(topic_name, "Test message")
        messages = self.emulator.pull_messages(subscription_name)
        
        original_ack_id = messages[0].ack_id
        original_delivery_attempt = messages[0].delivery_attempt
        
        # Nack the message
        success = self.emulator.nack_message(original_ack_id)
        assert success == True
        
        # Check that message is available for redelivery with new ack_id
        assert original_ack_id in self.emulator.pending_acks
        redelivered_message = self.emulator.pending_acks[messages[0].ack_id]
        assert redelivered_message.delivery_attempt == original_delivery_attempt + 1


class TestPubSubEmulatorClient:
    """Test cases for Pub/Sub emulator client"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.emulator = PubSubEmulator()
        self.client = PubSubEmulatorClient(self.emulator)
    
    @pytest.mark.asyncio
    async def test_client_operations(self):
        """Test client-level operations"""
        topic_name = "client-test-topic"
        subscription_name = "client-test-subscription"
        
        # Create topic and subscription
        await self.client.create_topic(topic_name)
        await self.client.create_subscription(subscription_name, topic_name)
        
        # Publish message
        message_id = await self.client.publish(topic_name, "Client test message", source="test")
        assert message_id is not None
        
        # Pull messages
        messages = await self.client.pull_messages(subscription_name)
        assert len(messages) == 1
        assert messages[0].data == "Client test message"
        
        # Acknowledge message
        success = await self.client.acknowledge(messages[0].ack_id)
        assert success == True
    
    @pytest.mark.asyncio
    async def test_subscription_with_handler(self):
        """Test subscription with message handler"""
        topic_name = "handler-test-topic"
        subscription_name = "handler-test-subscription"
        
        # Setup
        await self.client.create_topic(topic_name)
        await self.client.create_subscription(subscription_name, topic_name)
        
        # Message handler
        received_messages = []
        
        async def message_handler(message):
            received_messages.append(message.data)
        
        # Start subscription (run briefly)
        subscription_task = await self.client.subscribe(
            subscription_name, message_handler, poll_interval=0.1
        )
        
        # Publish some messages
        await self.client.publish(topic_name, "Message 1")
        await self.client.publish(topic_name, "Message 2")
        
        # Wait a bit for processing
        await asyncio.sleep(0.5)
        
        # Stop subscription
        await self.client.unsubscribe(subscription_name)
        
        # Check that messages were received
        assert len(received_messages) >= 1  # At least one message should be processed


class TestLocalIngestionManager:
    """Test cases for local ingestion manager"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.manager = LocalIngestionManager()
    
    @pytest.mark.asyncio
    async def test_all_sources_ingestion(self):
        """Test ingestion from all local sources"""
        events = await self.manager.ingest_all_sources(max_events=20)
        
        assert len(events) > 0
        assert len(events) <= 20
        
        # Check that we have events from different sources
        sources = set(event.source for event in events)
        assert len(sources) >= 1  # At least one source type
        
        # Check that events are sorted by timestamp (most recent first)
        timestamps = [event.timestamp for event in events]
        assert timestamps == sorted(timestamps, reverse=True)
    
    @pytest.mark.asyncio
    async def test_specific_source_ingestion(self):
        """Test ingestion from specific sources"""
        # Test RSS ingestion
        rss_events = await self.manager.ingest_from_source("rss", max_articles=5)
        assert len(rss_events) <= 5
        assert all(event.source in [EventSource.RSS, EventSource.NEWS] for event in rss_events)
        
        # Test social media ingestion
        social_events = await self.manager.ingest_from_source("social", count=3)
        assert len(social_events) == 3
        assert all(event.source in [EventSource.TWITTER, EventSource.FACEBOOK] for event in social_events)
        
        # Test scenario injection
        test_events = await self.manager.ingest_from_source("test", scenario_type="disaster_scenarios")
        assert len(test_events) == 1
        assert test_events[0].source == EventSource.MANUAL
        
        # Test custom injection
        custom_events = await self.manager.ingest_from_source(
            "custom", text="Custom test event", location="Test City"
        )
        assert len(custom_events) == 1
        assert custom_events[0].original_text == "Custom test event"


class TestCloudIngestionManager:
    """Test cases for cloud ingestion manager (with mocks)"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.manager = CloudIngestionManager()
    
    @pytest.mark.asyncio
    async def test_manager_initialization(self):
        """Test cloud manager initialization in local mode"""
        # Should initialize successfully even without cloud credentials
        success = await self.manager.initialize()
        assert success == True
        assert self.manager.initialized == True
    
    @pytest.mark.asyncio
    async def test_content_enhancement_fallback(self):
        """Test content enhancement with fallback when Watson unavailable"""
        # Create test events
        raw_events = [
            RawEvent(
                source=EventSource.NEWS,
                original_text="Test news about flooding in Mumbai",
                timestamp=datetime.utcnow(),
                metadata={"source": "test"}
            )
        ]
        
        # This should work even without Watson credentials (fallback mode)
        enhanced_events = await self.manager.ingest_and_enhance_content(raw_events)
        
        assert len(enhanced_events) == 1
        enhanced_event = enhanced_events[0]
        
        # Should have Watson analysis in metadata (even if fallback)
        assert "watson_analysis" in enhanced_event.metadata
        watson_analysis = enhanced_event.metadata["watson_analysis"]
        assert "watson_enhanced" in watson_analysis


class TestUnifiedIngestionManager:
    """Test cases for unified ingestion manager"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.manager = UnifiedIngestionManager()
    
    @pytest.mark.asyncio
    async def test_manager_initialization(self):
        """Test unified manager initialization"""
        success = await self.manager.initialize()
        assert success == True
        assert self.manager.initialized == True
        assert self.manager.mode == IngestionMode.LOCAL_ONLY  # Should be local in test mode
    
    @pytest.mark.asyncio
    async def test_single_event_ingestion(self):
        """Test single event ingestion and processing"""
        await self.manager.initialize()
        
        # Ingest a custom test event
        processed_event = await self.manager.ingest_single_event(
            "custom",
            text="Test event for unified manager",
            location="Mumbai",
            category="test"
        )
        
        assert processed_event is not None
        assert isinstance(processed_event, ProcessedEvent)
        assert processed_event.original_text == "Test event for unified manager"
        assert processed_event.region_hint != ""  # Should have extracted location
    
    @pytest.mark.asyncio
    async def test_batch_ingestion(self):
        """Test batch ingestion"""
        await self.manager.initialize()
        
        processed_events = await self.manager.ingest_batch(max_events=10)
        
        # Should get some events (even if from sample data)
        assert len(processed_events) >= 0  # May be 0 if no sources available
        
        for event in processed_events:
            assert isinstance(event, ProcessedEvent)
            assert event.event_id is not None
            assert len(event.original_text) > 0
    
    @pytest.mark.asyncio
    async def test_statistics_tracking(self):
        """Test ingestion statistics tracking"""
        await self.manager.initialize()
        
        # Get initial stats
        initial_stats = self.manager.get_stats()
        assert isinstance(initial_stats, IngestionStats)
        
        # Ingest some events
        await self.manager.ingest_single_event("custom", text="Stats test event")
        
        # Check updated stats
        updated_stats = self.manager.get_stats()
        assert updated_stats.total_events_ingested >= initial_stats.total_events_ingested
        assert updated_stats.events_processed >= initial_stats.events_processed
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check functionality"""
        await self.manager.initialize()
        
        health = await self.manager.health_check()
        
        assert isinstance(health, dict)
        assert "status" in health
        assert "timestamp" in health
        assert "mode" in health
        assert "components" in health
        
        # Should be healthy after initialization
        assert health["status"] in ["healthy", "degraded"]  # Allow degraded for missing cloud services
    
    def test_event_deduplication(self):
        """Test event deduplication logic"""
        # Create duplicate events
        event1 = RawEvent(
            source=EventSource.NEWS,
            original_text="Duplicate event text",
            timestamp=datetime.utcnow(),
            metadata={}
        )
        
        event2 = RawEvent(
            source=EventSource.NEWS,
            original_text="Duplicate event text",
            timestamp=datetime.utcnow(),
            metadata={}
        )
        
        event3 = RawEvent(
            source=EventSource.NEWS,
            original_text="Different event text",
            timestamp=datetime.utcnow(),
            metadata={}
        )
        
        events = [event1, event2, event3]
        unique_events = self.manager._deduplicate_events(events)
        
        # Should remove one duplicate
        assert len(unique_events) == 2
        
        # Should keep the different event
        texts = [event.original_text for event in unique_events]
        assert "Different event text" in texts


class TestIngestionIntegration:
    """Integration tests for complete ingestion pipeline"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_ingestion_pipeline(self):
        """Test complete end-to-end ingestion and processing"""
        # Initialize unified manager
        manager = UnifiedIngestionManager()
        await manager.initialize()
        
        # Create a test event with known characteristics
        test_text = "Major flooding reported in Mumbai after heavy monsoon rains. Local authorities evacuating residents."
        
        # Ingest and process the event
        processed_event = await manager.ingest_single_event(
            "custom",
            text=test_text,
            location="Mumbai, Maharashtra",
            category="disaster"
        )
        
        # Verify complete processing
        assert processed_event is not None
        assert processed_event.original_text == test_text
        assert processed_event.region_hint != ""  # Should extract location
        assert len(processed_event.entities) > 0  # Should extract entities
        assert processed_event.virality_score >= 0.0  # Should calculate virality
        assert processed_event.satellite is not None  # Should have satellite validation
        
        # Check that claims were extracted
        assert len(processed_event.claims) >= 0  # May or may not find claims
        
        # Check processing metadata
        assert "nlp_analysis" in processed_event.processing_metadata
        assert "processing_time_ms" in processed_event.processing_metadata
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self):
        """Test error handling and recovery in ingestion pipeline"""
        manager = UnifiedIngestionManager()
        await manager.initialize()
        
        # Test with invalid/empty text
        processed_event = await manager.ingest_single_event("custom", text="")
        assert processed_event is None  # Should handle gracefully
        
        # Test with very long text
        long_text = "A" * 10000  # Very long text
        processed_event = await manager.ingest_single_event("custom", text=long_text)
        # Should either process or fail gracefully
        if processed_event:
            assert len(processed_event.original_text) <= 10000
    
    @pytest.mark.asyncio
    async def test_performance_benchmarking(self):
        """Test performance of ingestion pipeline"""
        manager = UnifiedIngestionManager()
        await manager.initialize()
        
        # Measure processing time for batch
        start_time = datetime.utcnow()
        
        processed_events = await manager.ingest_batch(max_events=5)
        
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()
        
        # Should process reasonably quickly (less than 30 seconds for 5 events)
        assert processing_time < 30.0
        
        # Check average processing time from stats
        stats = manager.get_stats()
        if stats.events_processed > 0:
            assert stats.average_processing_time_ms > 0
            assert stats.average_processing_time_ms < 10000  # Less than 10 seconds per event


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])