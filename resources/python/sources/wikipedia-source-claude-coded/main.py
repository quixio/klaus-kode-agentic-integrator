"""
Wikipedia Change Event Stream Source

This application reads from the Wikipedia Change Event Stream API
and writes page edit metadata to a Kafka topic using Quix Streams.
"""

import json
import os
import time
import logging
from datetime import datetime
from typing import Dict, Any

from requests_sse import EventSource
from quixstreams import Application
from quixstreams.sources import Source

# for local dev, load env vars from a .env file
# from dotenv import load_dotenv
# load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WikipediaChangeEventSource(Source):
    """
    A Quix Streams Source that reads from Wikipedia's Change Event Stream API
    and publishes page edit metadata to a Kafka topic.
    
    This source connects to the Wikipedia EventStreams API, filters for events
    from English Wikipedia (or the configured target wiki), and extracts key
    metadata fields from each change event. Category edit pages (pages with 
    titles starting with "Category:") and user pages (pages with titles starting 
    with "User:") are automatically excluded from processing.
    """

    def __init__(self, stream_url: str, target_wiki: str, max_events: int = 100, **kwargs):
        """
        Initialize the Wikipedia Change Event Source
        
        Args:
            stream_url: Wikipedia EventStreams API URL
            target_wiki: Target wiki to filter events (e.g., en.wikipedia.org) 
            max_events: Maximum number of events to process (for testing)
        """
        super().__init__(**kwargs)
        self.stream_url = stream_url
        self.target_wiki = target_wiki
        self.max_events = max_events
        self.events_processed = 0
        self.category_pages_skipped = 0
        self.user_pages_skipped = 0
        
    def _extract_metadata(self, change: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract key metadata fields from a Wikipedia change event
        
        Args:
            change: Raw change event from Wikipedia EventStreams
            
        Returns:
            Dictionary containing extracted metadata
        """
        # Extract timestamp and convert to Unix timestamp if needed
        timestamp_str = change.get('timestamp', '')
        try:
            if 'T' in timestamp_str and 'Z' in timestamp_str:
                # ISO format timestamp - convert to Unix timestamp
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                timestamp = int(dt.timestamp())
            else:
                # Assume it's already a Unix timestamp or number
                timestamp = int(float(timestamp_str)) if timestamp_str else int(time.time())
        except (ValueError, TypeError):
            # Fallback to current time if parsing fails
            timestamp = int(time.time())
            
        # Extract and format metadata according to the schema
        metadata = {
            "page_title": change.get('title', 'Unknown'),
            "user": change.get('user', 'Anonymous'), 
            "change_type": change.get('type', 'unknown'),
            "server": change.get('server_name', 'unknown'),
            "namespace": change.get('namespace', 0),
            "timestamp": timestamp,
            "comment": change.get('comment', '')[:500] if change.get('comment') else ''  # Limit comment length
        }
        
        # Calculate length change
        length_old = change.get('length', {}).get('old', 0)
        length_new = change.get('length', {}).get('new', 0)
        length_change = length_new - length_old if isinstance(length_new, int) and isinstance(length_old, int) else 0
        metadata["length_change"] = f"{length_change:+d} characters"
        
        # Add revision ID
        revision_id = change.get('revision', {}).get('new', 'unknown')
        metadata["revision_id"] = str(revision_id)
        
        # Add additional useful fields
        metadata["bot"] = change.get('bot', False)
        metadata["minor"] = change.get('minor', False)
        
        # Add original event ID if available for tracking
        if change.get('id'):
            metadata["event_id"] = change.get('id')
            
        return metadata

    def run(self):
        """
        Main source execution loop.
        
        Connects to Wikipedia EventStreams API and processes change events,
        filtering for the target wiki and extracting metadata.
        """
        logger.info(f"Starting Wikipedia Change Event Stream Source")
        logger.info(f"Stream URL: {self.stream_url}")
        logger.info(f"Target Wiki: {self.target_wiki}")
        logger.info(f"Max Events: {self.max_events}")
        logger.info(f"Category Page Filtering: ENABLED (will exclude pages starting with 'Category:')")
        logger.info(f"User Page Filtering: ENABLED (will exclude pages starting with 'User:')")
        
        # Wikipedia requires a proper User-Agent header to avoid 403 errors
        headers = {
            'User-Agent': 'QuixWikipediaSource/1.0 (Quix Cloud Platform; quix.io; support@quix.io) requests-sse/2.0.1',
            'Accept': 'text/event-stream'
        }
        
        retry_count = 0
        max_retries = 5
        
        while self.running and self.events_processed < self.max_events:
            try:
                logger.info(f"Connecting to Wikipedia EventStreams...")
                
                with EventSource(self.stream_url, headers=headers) as stream:
                    logger.info(f"✓ Successfully connected to Wikipedia EventStreams!")
                    logger.info(f"✓ Listening for events from {self.target_wiki}...")
                    retry_count = 0  # Reset retry count on successful connection
                    
                    for event in stream:
                        if not self.running or self.events_processed >= self.max_events:
                            break
                            
                        if event.type == 'message':
                            try:
                                # Parse the JSON event data
                                change = json.loads(event.data)
                                
                                # Debug: Print raw message structure for first few events
                                if self.events_processed < 3:
                                    logger.info(f"Raw event structure: {json.dumps(change, indent=2)[:500]}...")
                                
                                # Skip canary events (test events from Wikipedia)
                                if change.get('meta', {}).get('domain') == 'canary':
                                    continue
                                
                                # Filter for target wiki (English Wikipedia by default)
                                if change.get('server_name') == self.target_wiki:
                                    
                                    # Extract metadata
                                    metadata = self._extract_metadata(change)
                                    
                                    # Skip category edit pages (e.g., "Category:Start-Class biography articles")
                                    page_title = metadata.get("page_title", "")
                                    if page_title.startswith("Category:"):
                                        self.category_pages_skipped += 1
                                        logger.info(f"Skipping category page: {page_title}")
                                        continue
                                    
                                    # Skip user pages (e.g., "User:Smashedbandit/sandbox")
                                    if page_title.startswith("User:"):
                                        self.user_pages_skipped += 1
                                        logger.info(f"Skipping user page: {page_title}")
                                        continue
                                    
                                    # Serialize and produce the event
                                    event_serialized = self.serialize(
                                        key=metadata.get("page_title", "unknown"),
                                        value=metadata
                                    )
                                    
                                    self.produce(
                                        key=event_serialized.key, 
                                        value=event_serialized.value
                                    )
                                    
                                    self.events_processed += 1
                                    
                                    logger.info(f"Processed event #{self.events_processed}: {metadata['page_title']} by {metadata['user']}")
                                    
                                    # Check if we've reached the maximum number of events
                                    if self.events_processed >= self.max_events:
                                        logger.info(f"Reached maximum events limit ({self.max_events}). Stopping source.")
                                        break
                                        
                            except json.JSONDecodeError as e:
                                logger.warning(f"Failed to parse JSON event: {e}")
                                continue
                            except KeyError as e:
                                logger.warning(f"Missing expected field in event: {e}")
                                continue
                            except Exception as e:
                                logger.error(f"Error processing event: {e}")
                                continue
                                
                        elif event.type == 'error':
                            logger.error(f"Received error event from stream: {event.data}")
                            
            except ConnectionError as e:
                retry_count += 1
                logger.error(f"Connection failed (attempt {retry_count}/{max_retries}): {e}")
                
                if retry_count >= max_retries:
                    logger.error("Max retries reached. Stopping source.")
                    break
                    
                # Exponential backoff
                wait_time = min(60, 2 ** retry_count)
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                
            except Exception as e:
                error_str = str(e).lower()
                if "403" in error_str or "forbidden" in error_str:
                    logger.error(f"Access denied (403 Forbidden): {e}")
                    logger.error("This might be due to missing/invalid User-Agent header or IP blocking")
                    break
                else:
                    logger.error(f"Unexpected error: {e}")
                    retry_count += 1
                    
                    if retry_count >= max_retries:
                        logger.error("Max retries reached due to errors. Stopping source.")
                        break
                        
                    wait_time = min(60, 2 ** retry_count)
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    
        logger.info(f"Wikipedia Change Event Stream Source finished. Processed {self.events_processed} events, skipped {self.category_pages_skipped} category pages, {self.user_pages_skipped} user pages.")


def main():
    """Main entry point for the Wikipedia source application"""
    
    logger.info("Starting Wikipedia Change Event Stream Source Application")
    
    # Get configuration from environment variables
    stream_url = os.environ.get('WIKIPEDIA_STREAM_URL', 'https://stream.wikimedia.org/v2/stream/recentchange')
    target_wiki = os.environ.get('TARGET_WIKI', 'en.wikipedia.org')
    output_topic = os.environ.get('output', 'wikipedia-data')
    
    # Limit to 100 events for initial testing
    max_events = int(os.environ.get('MAX_EVENTS', '100'))
    
    logger.info(f"Configuration:")
    logger.info(f"  Stream URL: {stream_url}")
    logger.info(f"  Target Wiki: {target_wiki}")
    logger.info(f"  Output Topic: {output_topic}")
    logger.info(f"  Max Events: {max_events}")
    
    try:
        # Setup Quix Streams Application
        app = Application(consumer_group="wikipedia-source", auto_create_topics=True)
        
        # Create the Wikipedia source
        wikipedia_source = WikipediaChangeEventSource(
            name="wikipedia-change-event-source",
            stream_url=stream_url,
            target_wiki=target_wiki,
            max_events=max_events
        )
        
        # Create output topic  
        topic = app.topic(name=output_topic)
        
        # Setup dataframe for additional processing and debugging
        sdf = app.dataframe(source=wikipedia_source)
        
        # Add debugging output to see messages being processed
        sdf.print(metadata=True)
        
        # Output to the topic
        sdf.to_topic(topic=topic)
        
        logger.info("Starting Wikipedia Event Stream processing...")
        
        # Run the application
        app.run()
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error in application: {e}")
        raise


# Sources require execution under a conditional main
if __name__ == "__main__":
    main()