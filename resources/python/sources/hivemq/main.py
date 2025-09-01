from quixstreams import Application
import paho.mqtt.client as paho
from paho import mqtt
from datetime import datetime
import signal
import json
import time
import sys
import os

# Load environment variables (useful when working locally)
from dotenv import load_dotenv
load_dotenv()

def mqtt_protocol_version():
    if os.environ["mqtt_version"] == "3.1":
        print("Using MQTT version 3.1")
        return paho.MQTTv31
    if os.environ["mqtt_version"] == "3.1.1":
        print("Using MQTT version 3.1.1")
        return paho.MQTTv311
    if os.environ["mqtt_version"] == "5":
        print("Using MQTT version 5")
        return paho.MQTTv5
    print("Defaulting to MQTT version 3.1.1")
    return paho.MQTTv311

def configure_authentication(mqtt_client):
    mqtt_username = os.getenv("mqtt_username", "") 
    if mqtt_username != "":
        mqtt_password = os.getenv("mqtt_password", "")
        if mqtt_password == "":
           raise ValueError('mqtt_password must set when mqtt_username is set')
        print("Using username & password authentication")
        mqtt_client.username_pw_set(os.environ["mqtt_username"], os.environ["mqtt_password"])
        return
    print("Using anonymous authentication")


mqtt_topic = os.getenv("mqtt_topic", "")
mqtt_port = os.getenv("mqtt_port", "")
output_topic_name = os.getenv("output", "")

# Validate the config
if output_topic_name == "":
    raise ValueError("output (topic) environment variable is required")
if mqtt_topic == "":
    raise ValueError('mqtt_topic must be supplied')
if not mqtt_port.isnumeric():
    raise ValueError('mqtt_port must be a numeric value')

client_id = os.getenv("Quix__Deployment__Id", "default")
mqtt_client = paho.Client(callback_api_version=paho.CallbackAPIVersion.VERSION2,
                          client_id = client_id, userdata = None, protocol = mqtt_protocol_version())
mqtt_client.tls_set(tls_version = mqtt.client.ssl.PROTOCOL_TLS)  # we'll be using tls
mqtt_client.reconnect_delay_set(5, 60)
configure_authentication(mqtt_client)

# Create a Quix Application, this manages the connection to the Quix platform
app = Application()
# Create the producer, this is used to write data to the output topic
producer = app.get_producer()
# create a topic object for use later on
output_topic = app.topic(output_topic_name, value_serializer="bytes")

# setting callbacks for different events to see if it works, print the message etc.
def on_connect_cb(client: paho.Client, userdata: any, connect_flags: paho.ConnectFlags,
                  reason_code: paho.ReasonCode, properties: paho.Properties):
    if reason_code == 0:
        mqtt_client.subscribe(mqtt_topic, qos = 1)
        print("CONNECTED!") # required for Quix to know this has connected
    else:
        print(f"ERROR! - ({reason_code.value}). {reason_code.getName()}")

# print message, useful for checking if it was successful
def on_message_cb(client: paho.Client, userdata: any, msg: paho.MQTTMessage):
    message_key = str(msg.topic).replace("/", "-")

    print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))

    # publish to the putput topic
    producer.produce(topic=output_topic.name,
                    key=message_key,
                    value=msg.payload)

# print which topic was subscribed to
def on_subscribe_cb(client: paho.Client, userdata: any, mid: int,
                    reason_code_list: list[paho.ReasonCode], properties: paho.Properties):
    print("Subscribed: " + str(mid))
    for reason_code in reason_code_list:
        print(f"\tReason code ({reason_code.value}): {reason_code.getName()}")
    
def on_disconnect_cb(client: paho.Client, userdata: any, disconnect_flags: paho.DisconnectFlags,
                     reason_code: paho.ReasonCode, properties: paho.Properties):
    print(f"DISCONNECTED! Reason code ({reason_code.value}) {reason_code.getName()}!")
    
mqtt_client.on_connect = on_connect_cb
mqtt_client.on_message = on_message_cb
mqtt_client.on_subscribe = on_subscribe_cb
mqtt_client.on_disconnect = on_disconnect_cb

# connect to MQTT Cloud on port 8883 (default for MQTT)
mqtt_client.connect(os.environ["mqtt_server"], int(mqtt_port))

# start the background process to handle MQTT messages
mqtt_client.loop_start()

# Define a handler function that will be called when SIGTERM is received
def handle_sigterm(signum, frame):
    print("SIGTERM received, terminating connection")
    mqtt_client.loop_stop()
    print("Exiting")
    sys.exit(0)

# Register the handler for the SIGTERM signal
signal.signal(signal.SIGTERM, handle_sigterm)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Interrupted by the use, terminating connection")
    mqtt_client.loop_stop() # clean up
    print("Exiting")