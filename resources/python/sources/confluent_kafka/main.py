from quixstreams.app import Application
from quixstreams.kafka.producer import Producer
from datetime import datetime
import json
import os

# for local dev, load env vars from a .env file
from dotenv import load_dotenv
load_dotenv()

# SASL configuration
sasl_config = {
    'sasl.mechanism': os.getenv("kafka_sasl_mechanism", "SCRAM-SHA-256"),
    'security.protocol': 'SASL_SSL',
    'sasl.username': os.getenv("kafka_key", ""),
    'sasl.password': os.getenv("kafka_secret", ""),
    'ssl.ca.location': os.getenv("kafka_ca_location", "")
}
broker_address = os.getenv("kafka_broker_address", "")
input_topic_name = os.getenv("kafka_topic", "")
output_topic_name = os.getenv("output", "")

if sasl_config["sasl.username"] == "" or sasl_config["sasl.password"] == "":
    print("Please provide kafka_key and kafka_secret")
    exit(1)

if broker_address == "":
    print("Please provide kafka_broker_address")
    exit(1)

if input_topic_name == "" or output_topic_name == "":
    print("Please provide input and output topics")
    exit(1)

# this 'application' will consume data from Confluent Kafka
app = Application(broker_address=broker_address, consumer_group="kafka-connector-consumer-group", 
                    auto_offset_reset="earliest", consumer_extra_config=sasl_config)
# this topic is the Confluent Kafka topic
input_topic = app.topic(input_topic_name)

# This 'application' and producer will publish data to a Quix topic
producer_app = Application()
producer = producer_app.get_producer()
# this is the Quix topic
output_topic = producer_app.topic(output_topic_name)

# let the platform know were connected. If deploying a connector from the library, it will nav to the home page.
print("CONNECTED!")

# Create a StreamingDataFrame instance for consuming data from Confluent Kafka
sdf = app.dataframe(input_topic)

# handle each message by publishing it to the output topic (in Quix)
# if you want to do any transformation you can do that here too
def handle_message(message):
    # Convert the message dictionary to a JSON string
    message_json = json.dumps(message)

    # Encode the JSON string to bytes
    message_bytes = message_json.encode('utf-8')
    
    # publish message to Quix Kafka
    producer.produce(key=f"data-from-confluent-kafka-topic-{input_topic_name}",
                     value=message_bytes,
                     topic=output_topic.name)

sdf = sdf.update(handle_message)

if __name__ == "__main__":
    print("Starting application")
    app.run(sdf)
