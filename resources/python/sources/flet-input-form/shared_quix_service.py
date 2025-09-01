import json
import threading
from datetime import datetime
from quixstreams import Application


class SharedQuixService:
    """Singleton Quix service for producer functionality"""
    
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
            
        # Producer components
        self.app = None
        self.producer = None
        self.output_topic = None
        self.output_topic_name = None
        
        # Status tracking
        self.connection_status = "Disconnected"
        self.message_count = 0
        self.last_send_time = None
        
        self._initialized = True
    
    def initialize_producer(self, output_topic_name):
        """Initialize the Quix producer"""
        try:
            self.output_topic_name = output_topic_name
            
            # Initialize Quix Streams application
            self.app = Application()
            self.output_topic = self.app.topic(output_topic_name)
            self.producer = self.app.get_producer()
            
            self.connection_status = "Connected"
            print(f"Producer initialized for topic: {output_topic_name}")
            return True
            
        except Exception as e:
            self.connection_status = f"Error: {str(e)}"
            print(f"Error initializing producer: {e}")
            return False
    
    def send_message(self, message_data):
        """Send a message to the configured output topic.
        
        Args:
            message_data: Data to send (dict or string)
            
        Returns:
            bool: True if message sent successfully
            
        Raises:
            Exception: If producer not initialized or send fails
        """
        try:
            # Ensure message is properly formatted as JSON string
            if isinstance(message_data, dict):
                message_json = json.dumps(message_data)
            else:
                message_json = str(message_data)
            
            # Send message to Kafka topic
            self.producer.produce(
                topic=self.output_topic.name,
                value=message_json
            )
            self.producer.flush()  # Ensure immediate delivery
            
            # Update message tracking statistics
            self.message_count += 1
            self.last_send_time = datetime.now()
            
            print(f"Message sent successfully: {message_json}")
            return True
            
        except Exception as e:
            print(f"Error sending message: {e}")
            raise e
    
    def get_status(self):
        """Get comprehensive status information about the service.
        
        Returns:
            dict: Status information including connection state,
                 message count, topic name, and readiness
        """
        return {
            'status': self.connection_status,
            'message_count': self.message_count,
            'output_topic': self.output_topic_name,
            'last_send_time': self.last_send_time.strftime('%H:%M:%S') if self.last_send_time else None,
            'producer_ready': self.producer is not None
        }
    
    def is_ready(self):
        """Check if the producer is ready to send messages.
        
        Returns:
            bool: True if producer and topic are both initialized
        """
        return self.producer is not None and self.output_topic is not None


# Global shared instance
shared_quix_service = SharedQuixService()