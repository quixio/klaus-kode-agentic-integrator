# import the Quix Streams modules for interacting with Kafka.
# For general info, see https://quix.io/docs/quix-streams/introduction.html
# For sinks, see https://quix.io/docs/quix-streams/connectors/sinks/index.html
from quixstreams import Application
from quixstreams.sinks import BatchingSink, SinkBatch, SinkBackpressureError

import os
import time
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# ClickHouse connection
try:
    import clickhouse_connect
except ImportError:
    raise ImportError("clickhouse-connect is required. Install with: pip install clickhouse-connect")

# for local dev, you can load env vars from a .env file
# from dotenv import load_dotenv
# load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ClickHouseWikipediaSink(BatchingSink):
    """
    Custom sink for writing Wikipedia page edit metadata to ClickHouse database.
    Handles connection management, table creation, and batch writing.
    """
    
    def __init__(self, on_client_connect_success=None, on_client_connect_failure=None):
        super().__init__(
            on_client_connect_success=on_client_connect_success,
            on_client_connect_failure=on_client_connect_failure
        )
        
        # ClickHouse connection parameters
        self.host = os.environ['CLICKHOUSE_HOST']
        try:
            self.port = int(os.environ.get('CLICKHOUSE_PORT', '8123'))
        except ValueError:
            self.port = 8123
        self.database = os.environ['CLICKHOUSE_DATABASE']
        self.username = os.environ.get('CLICKHOUSE_USERNAME', 'default')
        self.password = os.environ.get('CLICKHOUSE_PASSWORD', '')
        self.table_name = os.environ.get('CLICKHOUSE_TABLE', 'wikipedia_page_edits')
        
        self._client = None
        self._table_created = False
        
        logger.info(f"ClickHouse Sink initialized - Host: {self.host}:{self.port}, DB: {self.database}, Table: {self.table_name}")
    
    def _get_client(self):
        """Get or create ClickHouse client"""
        if self._client is None:
            try:
                self._client = clickhouse_connect.get_client(
                    host=self.host,
                    port=self.port,
                    database=self.database,
                    username=self.username,
                    password=self.password
                )
                logger.info(f"Successfully connected to ClickHouse at {self.host}:{self.port}")
            except Exception as e:
                logger.error(f"Failed to connect to ClickHouse: {e}")
                raise ConnectionError(f"ClickHouse connection failed: {e}")
        return self._client
    
    def _ensure_table_exists(self):
        """Create the table if it doesn't exist and print its schema"""
        if self._table_created:
            logger.info(f"Table {self.table_name} already verified, skipping schema display")
            return
            
        client = self._get_client()
        
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            page_title String,
            user String,
            change_type String,
            server String,
            namespace Int32,
            timestamp DateTime,
            comment String,
            length_change String,
            revision_id String,
            bot UInt8,
            minor UInt8,
            event_id Int64,
            message_datetime DateTime,
            partition_num Int32,
            offset_num Int64
        ) ENGINE = MergeTree()
        ORDER BY (timestamp, page_title)
        SETTINGS index_granularity = 8192
        """
        
        try:
            client.command(create_table_sql)
            logger.info(f"Table {self.table_name} created or already exists")
            
            # Get and print table schema information
            schema_result = client.query(f"DESCRIBE TABLE {self.table_name}")
            schema_rows = schema_result.result_rows
            
            logger.info(f"Table {self.table_name} verified with {len(schema_rows)} columns")
            
            # Print detailed schema information
            print(f"\n{'='*70}")
            print(f"🗄️  TARGET TABLE SCHEMA VERIFICATION")
            print(f"{'='*70}")
            print(f"📊 Database: {self.database}")
            print(f"🌐 Host: {self.host}:{self.port}")
            print(f"📋 Table: {self.table_name}")
            print(f"📈 Total Columns: {len(schema_rows)}")
            print(f"{'='*70}")
            
            # Print column details in a formatted table
            print(f"{'Column Name':<20} {'Type':<15} {'Default':<15} {'Comment'}")
            print(f"{'-'*20} {'-'*15} {'-'*15} {'-'*20}")
            
            for row in schema_rows:
                column_name = row[0]
                column_type = row[1]
                default_type = row[2] if len(row) > 2 else ''
                comment = row[3] if len(row) > 3 else ''
                
                print(f"{column_name:<20} {column_type:<15} {default_type:<15} {comment}")
            
            print(f"{'='*70}")
            
            # Also get table engine and ordering information
            try:
                table_info = client.query(f"SHOW CREATE TABLE {self.table_name}")
                create_statement = table_info.result_rows[0][0] if table_info.result_rows else "N/A"
                
                # Extract engine and order by information
                if "ENGINE = MergeTree()" in create_statement:
                    print(f"🔧 Engine: MergeTree")
                
                if "ORDER BY" in create_statement:
                    order_start = create_statement.find("ORDER BY")
                    order_section = create_statement[order_start:order_start+100].split('\n')[0]
                    print(f"📑 Order By: {order_section}")
                    
            except Exception as e:
                logger.warning(f"Could not retrieve additional table info: {e}")
            
            print(f"{'='*70}")
            print(f"✅ TABLE SCHEMA VERIFIED - Ready to receive Wikipedia page edit data!")
            print(f"{'='*70}\n")
            
            self._table_created = True
            
        except Exception as e:
            logger.error(f"Failed to create table: {e}")
            raise
    
    def _parse_message(self, item) -> Optional[Dict[str, Any]]:
        """Parse a single message from the batch"""
        try:
            # Debug: Show raw message structure
            logger.info(f"Raw message: {item}")
            
            # Get the message data - it should be a dict with the schema structure
            message_data = item.value
            
            # Debug: Show message structure and available keys
            logger.info(f"Message keys available: {list(message_data.keys()) if isinstance(message_data, dict) else 'Not a dict'}")
            logger.info(f"Message data sample: {str(message_data)[:200]}...")
            
            # Ensure we have a dictionary
            if not isinstance(message_data, dict):
                logger.warning(f"Message data is not a dictionary: {type(message_data)}")
                return None
            
            # Check if we have the Wikipedia edit data directly available (already parsed)
            # or if it's still in a nested 'value' field as JSON string
            if 'page_title' in message_data:
                # Data is already parsed and available at the top level
                wikipedia_data = message_data
                logger.info(f"Wikipedia data found at top level with keys: {list(wikipedia_data.keys())}")
            elif 'value' in message_data:
                # Data is nested in 'value' field as JSON string (original expected format)
                wikipedia_json_str = message_data.get('value')
                try:
                    wikipedia_data = json.loads(wikipedia_json_str)
                    logger.info(f"Parsed Wikipedia data from 'value' field with keys: {list(wikipedia_data.keys())}")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse value field as JSON: {e}")
                    return None
            else:
                logger.warning(f"No Wikipedia data found. Available keys: {list(message_data.keys())}")
                return None
            
            # Convert epoch timestamp to datetime
            timestamp_epoch = wikipedia_data.get('timestamp', 0)
            timestamp_dt = datetime.fromtimestamp(timestamp_epoch) if timestamp_epoch else datetime.now()
            
            # Parse message datetime - check both the outer message structure and direct field
            message_datetime_str = message_data.get('dateTime', '') or wikipedia_data.get('dateTime', '')
            try:
                if message_datetime_str:
                    message_datetime_dt = datetime.fromisoformat(message_datetime_str.replace('Z', '+00:00'))
                else:
                    message_datetime_dt = datetime.now()
            except ValueError:
                message_datetime_dt = datetime.now()
            
            # Prepare record for ClickHouse using the Wikipedia data schema
            record = {
                'page_title': str(wikipedia_data.get('page_title', '')),
                'user': str(wikipedia_data.get('user', '')),
                'change_type': str(wikipedia_data.get('change_type', '')),
                'server': str(wikipedia_data.get('server', '')),
                'namespace': int(wikipedia_data.get('namespace', 0)),
                'timestamp': timestamp_dt,
                'comment': str(wikipedia_data.get('comment', '')),
                'length_change': str(wikipedia_data.get('length_change', '')),
                'revision_id': str(wikipedia_data.get('revision_id', 'unknown')),
                'bot': 1 if wikipedia_data.get('bot', False) else 0,
                'minor': 1 if wikipedia_data.get('minor', False) else 0,
                'event_id': int(wikipedia_data.get('event_id', 0)),
                'message_datetime': message_datetime_dt,
                'partition_num': message_data.get('partition', 0) or wikipedia_data.get('partition', 0),
                'offset_num': message_data.get('offset', 0) or wikipedia_data.get('offset', 0)
            }
            
            logger.info(f"Successfully parsed record for page: {record['page_title']}")
            return record
            
        except Exception as e:
            logger.error(f"Error parsing message: {e}")
            logger.error(f"Message content: {item}")
            return None
    
    def _write_to_clickhouse(self, records):
        """Write batch of records to ClickHouse"""
        if not records:
            logger.warning("No valid records to write")
            return
            
        client = self._get_client()
        self._ensure_table_exists()
        
        try:
            # Convert list of dictionaries to columnar format expected by ClickHouse
            column_order = [
                'page_title', 'user', 'change_type', 'server', 'namespace', 'timestamp',
                'comment', 'length_change', 'revision_id', 'bot', 'minor', 'event_id',
                'message_datetime', 'partition_num', 'offset_num'
            ]
            
            # Convert records to tuples in the correct column order
            rows_data = []
            for record in records:
                row = tuple(record[col] for col in column_order)
                rows_data.append(row)
            
            logger.info(f"Prepared {len(rows_data)} rows for insertion to table {self.table_name}")
            logger.info(f"Sample row data: {rows_data[0] if rows_data else 'No data'}")
            
            # Insert records using the columnar data
            client.insert(self.table_name, rows_data, column_names=column_order)
            
            logger.info(f"Successfully wrote {len(records)} records to ClickHouse table {self.table_name}")
            
            # Verify the write by querying the table count and showing sample data
            result = client.query(f"SELECT COUNT(*) as count FROM {self.table_name}")
            total_count = result.result_rows[0][0]
            logger.info(f"Table {self.table_name} now contains {total_count} total records")
            
            # Show sample of latest records to verify data is being written correctly
            sample_result = client.query(f"SELECT page_title, user, change_type, timestamp FROM {self.table_name} ORDER BY timestamp DESC LIMIT 3")
            logger.info(f"Sample of latest records: {sample_result.result_rows}")
            
            # Evidence of successful sinking
            logger.info(f"✅ SINK SUCCESS: {len(records)} records successfully written to ClickHouse table '{self.table_name}'")
            
        except Exception as e:
            logger.error(f"Failed to write to ClickHouse: {e}")
            logger.error(f"Error details - Records count: {len(records) if records else 0}")
            if records:
                logger.error(f"Sample record structure: {list(records[0].keys()) if records[0] else 'Empty record'}")
            raise

    def write(self, batch: SinkBatch):
        """
        Write batch of messages to ClickHouse.
        Implements retry logic and error handling as per Quix Streams patterns.
        """
        attempts_remaining = 3
        
        # Parse all messages in the batch
        records = []
        batch_count = 0
        try:
            for item in batch:
                batch_count += 1
                record = self._parse_message(item)
                if record:
                    records.append(record)
        except Exception as e:
            logger.error(f"Error iterating through batch: {e}")
            raise
        
        logger.info(f"Processing batch with {len(records)} valid records from {batch_count} messages")
        
        while attempts_remaining > 0:
            try:
                return self._write_to_clickhouse(records)
            except ConnectionError as e:
                # Maybe we just failed to connect, do a short wait and try again
                logger.warning(f"Connection error, retrying... Attempts remaining: {attempts_remaining - 1}")
                attempts_remaining -= 1
                if attempts_remaining > 0:
                    time.sleep(3)
                else:
                    raise Exception(f"Connection failed after all retries: {e}")
            except TimeoutError as e:
                # Maybe the server is busy, do a sanctioned extended pause
                logger.warning(f"Timeout error, requesting backpressure: {e}")
                raise SinkBackpressureError(
                    retry_after=30.0,
                    topic=batch.topic,
                    partition=batch.partition,
                )
            except Exception as e:
                logger.error(f"Unexpected error writing to ClickHouse: {e}")
                attempts_remaining -= 1
                if attempts_remaining > 0:
                    time.sleep(3)
                else:
                    raise Exception(f"Failed to write to ClickHouse after all retries: {e}")
        
        raise Exception("Failed to write to ClickHouse after all retry attempts")


def main():
    """ Setup and run the ClickHouse sink application for Wikipedia data. """
    try:
        logger.info("Starting ClickHouse Wikipedia Sink Application")
        
        # Verify required environment variables
        required_vars = ["input", "CLICKHOUSE_HOST", "CLICKHOUSE_DATABASE"]
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        if missing_vars:
            logger.error(f"Missing required environment variables: {missing_vars}")
            raise ValueError(f"Missing environment variables: {missing_vars}")

        # Create ClickHouse sink and initialize connection + table schema BEFORE Kafka setup
        logger.info("Initializing ClickHouse connection and table schema...")
        clickhouse_sink = ClickHouseWikipediaSink()
        
        # Force table creation and schema display before Kafka connection
        # This ensures the schema is shown even if there are no messages
        try:
            client = clickhouse_sink._get_client()
            clickhouse_sink._ensure_table_exists()
            logger.info("ClickHouse table verified and schema displayed successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ClickHouse table: {e}")
            raise
        
        logger.info("Now setting up Kafka connection and message processing...")
        
        # Setup necessary objects
        app = Application(
            consumer_group="clickhouse_wikipedia_sinkV2",
            auto_create_topics=True,
            auto_offset_reset="earliest"
        )
        
        # Define input topic - expecting JSON messages
        input_topic = app.topic(name=os.environ["input"], value_deserializer="json")
        sdf = app.dataframe(topic=input_topic)

        # Add debugging and processing
        sdf = sdf.apply(lambda row: row)
        sdf = sdf.print(metadata=True)  # Print messages for debugging

        # Sink to ClickHouse
        sdf.sink(clickhouse_sink)

        logger.info("Pipeline configured, starting to process messages...")
        logger.info("Note: Table schema has already been verified and displayed above.")
        
        # Run the application with limited message count for testing
        app.run()
        
    except Exception as e:
        logger.error(f"Application failed with error: {e}")
        raise


# It is recommended to execute Applications under a conditional main
if __name__ == "__main__":
    main()