from quixstreams import Application
import time
import os
import json
from setup_logger import logger
from postgres_helper import connect_postgres, create_logical_slot, create_publication_on_table, get_changes

# Load environment variables (useful when working locally)
from dotenv import load_dotenv
load_dotenv()

# Global Variables
PG_SLOT_NAME = "replication_slot"
PG_SCHEMA = os.environ["PG_SCHEMA"]
PG_TABLE = os.environ["PG_TABLE"]
PG_PUBLICATION_NAME = f"pub_{PG_SCHEMA}_{PG_TABLE}"
PG_TABLE_NAME = f"{PG_SCHEMA}.{PG_TABLE}"
WAIT_INTERVAL = 0.1

# Connect to postgres and set up table
try:
    create_logical_slot(PG_SLOT_NAME)
    create_publication_on_table(PG_PUBLICATION_NAME, PG_TABLE_NAME)
    conn = connect_postgres()
    logger.info("CONNECTED!")
except Exception as e:
    logger.info(f"ERROR! - {e}")
    raise

# should the main loop run?
run = True

# Create a Quix Application, this manages the connection to the Quix platform
app = Application()

# Create the producer, this is used to write data to the output topic
producer = app.get_producer()

# Check the output topic is configured
output_topic_name = os.getenv("output", "")
if output_topic_name == "":
    raise ValueError("output_topic environment variable is required")
output_topic = app.topic(output_topic_name)

# get data from postgres and publish it to kafka
# to reduce network traffic, we buffer the messages for 100ms
def main():
    buffer = []
    last_flush_time = time.time()

    while run:
        records = get_changes(conn, PG_SLOT_NAME)
        for record in records:
            changes = json.loads(record[0])
            for change in changes["change"]:
                buffer.append(change)
                
        # Check if 100 milliseconds have passed
        current_time = time.time()
        if (current_time - last_flush_time) >= 0.5 and len(buffer) > 0:
            # If 500ms have passed, produce all buffered messages
            for message in buffer:
                producer.produce(topic=output_topic.name,
                                    key=PG_TABLE_NAME,
                                    value=json.dumps(message))
                print("Message sent to Kafka")
                # Flush the producer to send the messages
                
            # Clear the buffer
            buffer = []
            # Update the last flush time
            last_flush_time = current_time

        time.sleep(WAIT_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Exiting.")
        run = False
    finally:
        conn.close()
        logger.info("Connection to postgres closed")
        logger.info("Exiting")
