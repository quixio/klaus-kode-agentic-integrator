import json
import threading
import uuid
from collections import deque
from datetime import datetime, timedelta
from quixstreams import Application
from dotenv import load_dotenv

load_dotenv("waveform/.env")


class SharedQuixService:
    """Singleton Quix service shared between all app instances"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.data_callbacks = set()  # Set of data callback functions
        self.status_callbacks = set()  # Set of status callback functions
        self.consumer_thread = None
        self.running = False
        self.msg_counter = 0
        self.connection_status = "Disconnected"
        self.topic_name = None
        
        # Shared data buffer
        self.series_data = {}  # {series_name: deque of (timestamp, value)}
        self.max_age_seconds = 60
        self.max_age = timedelta(seconds=self.max_age_seconds)
        self.last_update_time = None
        
        self._initialized = True
    
    def set_topic(self, topic_name):
        """Set the topic name for the service"""
        self.topic_name = topic_name
    
    def add_data_callback(self, callback):
        """Add a data callback function"""
        with self._lock:
            self.data_callbacks.add(callback)
    
    def remove_data_callback(self, callback):
        """Remove a data callback function"""
        with self._lock:
            self.data_callbacks.discard(callback)
    
    def add_status_callback(self, callback):
        """Add a status callback function"""
        with self._lock:
            self.status_callbacks.add(callback)
    
    def remove_status_callback(self, callback):
        """Remove a status callback function"""
        with self._lock:
            self.status_callbacks.discard(callback)
    
    def start(self):
        """Start the Kafka consumer in a background thread"""
        if not self.running and self.topic_name:
            self.running = True
            self.consumer_thread = threading.Thread(target=self._kafka_consumer_thread, daemon=True)
            self.consumer_thread.start()
    
    def stop(self):
        """Stop the Kafka consumer"""
        self.running = False
        if self.consumer_thread:
            self.consumer_thread.join(timeout=2)
    
    def get_status(self):
        """Get current connection status and message count"""
        return {
            'status': self.connection_status,
            'message_count': self.msg_counter,
            'running': self.running,
            'topic': self.topic_name,
            'series_count': len(self.series_data),
            'total_points': sum(len(data) for data in self.series_data.values())
        }
    
    def add_data_point(self, series_name, timestamp, value):
        """Add a data point to the shared buffer"""
        with self._lock:
            if series_name not in self.series_data:
                self.series_data[series_name] = deque()
            
            self.series_data[series_name].append((timestamp, value))
            self._cleanup_old_data(series_name)
            self.last_update_time = datetime.now()
    
    def get_series_data(self, series_name):
        """Get data for a specific series, sorted by timestamp"""
        with self._lock:
            if series_name in self.series_data:
                data_list = list(self.series_data[series_name])
                return sorted(data_list, key=lambda x: x[0])  # Sort by timestamp (first element)
            return []
    
    def get_all_series_names(self):
        """Get all available series names"""
        with self._lock:
            return list(self.series_data.keys())
    
    def clear_data(self, series_name=None):
        """Clear data for a specific series or all series"""
        with self._lock:
            if series_name is None:
                self.series_data.clear()
            elif series_name in self.series_data:
                self.series_data[series_name].clear()
    
    def _cleanup_old_data(self, series_name):
        """Remove data points older than max_age relative to latest data point"""
        if series_name not in self.series_data:
            return
            
        data_deque = self.series_data[series_name]
        if not data_deque:
            return
            
        # Use the latest data point timestamp as reference
        latest_timestamp = data_deque[-1][0]  # Last item timestamp
        cutoff_timestamp = latest_timestamp - (self.max_age_seconds * 1000)  # Convert seconds to milliseconds
        
        while data_deque and data_deque[0][0] < cutoff_timestamp:
            data_deque.popleft()
    
    def _notify_data_callbacks(self, data, timestamp, counter):
        """Notify all data callbacks"""
        for callback in self.data_callbacks.copy():  # Copy to avoid modification during iteration
            try:
                callback(data, timestamp, counter)
            except Exception as e:
                print(f"Error in data callback: {e}")
    
    def _notify_status_callbacks(self, status, color):
        """Notify all status callbacks"""
        self.connection_status = status
        for callback in self.status_callbacks.copy():  # Copy to avoid modification during iteration
            try:
                callback(status, color)
            except Exception as e:
                print(f"Error in status callback: {e}")
    
    def _kafka_consumer_thread(self):
        """Background thread to consume Kafka messages"""
        try:
            # Initialize Quix Streams application
            app = Application(
                consumer_group=str(uuid.uuid4()),
                auto_offset_reset="latest",
            )
            
            # Create input topic using the provided topic name
            input_topic = app.topic(self.topic_name)
            consumer = app.get_consumer()
            consumer.subscribe([input_topic.name])
            print(self.topic_name)
            # Update connection status
            self._notify_status_callbacks("Connected", "GREEN")
            
            while self.running:
                # Poll for new messages
                message = consumer.poll(timeout=1.0)
                if message is not None:
                    self.msg_counter += 1
                    
                    # Process each message
                    try:
                        row = json.loads(message.value())
                        current_time = message.timestamp()[1]
                        
                        # Store data in shared buffer
                        for field_name, value in row.items():
                            try:
                                # Convert to float if possible
                                numeric_value = float(value)
                                self.add_data_point(field_name, current_time, numeric_value)
                            except (ValueError, TypeError):
                                # Skip non-numeric fields
                                continue
                        
                        # Notify all data callbacks
                        self._notify_data_callbacks(row, current_time, self.msg_counter)
                        
                    except Exception as e:
                        print(f"Error processing message: {e}")
                        
        except Exception as e:
            print(f"Error in Kafka consumer: {e}")
            self._notify_status_callbacks(f"Error: {str(e)}", "RED")


# Global shared instance
shared_quix_service = SharedQuixService()