from quixstreams import Application, context
import paho.mqtt.client as paho
from paho import mqtt
import json
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

mqtt_port = os.environ["mqtt_port"]
# Validate the config
if not mqtt_port.isnumeric():
    raise ValueError('mqtt_port must be a numeric value')

client_id = os.getenv("Quix__Deployment__Id", "default")
mqtt_client = paho.Client(callback_api_version=paho.CallbackAPIVersion.VERSION2,
                          client_id = client_id, userdata = None, protocol = mqtt_protocol_version())
mqtt_client.tls_set(tls_version = mqtt.client.ssl.PROTOCOL_TLS)  # we'll be using tls
mqtt_client.reconnect_delay_set(5, 60)
configure_authentication(mqtt_client)

# Create a Quix platform-specific application instead
app = Application(consumer_group="mqtt_consumer_group", auto_offset_reset='earliest')
# initialize the topic, this will combine the topic name with the environment details to produce a valid topic identifier
input_topic = app.topic(os.environ["input"])

# setting callbacks for different events to see if it works, print the message etc.
def on_connect_cb(client: paho.Client, userdata: any, connect_flags: paho.ConnectFlags,
                  reason_code: paho.ReasonCode, properties: paho.Properties):
    if reason_code == 0:
        print("CONNECTED!") # required for Quix to know this has connected
    else:
        print(f"ERROR! - ({reason_code.value}). {reason_code.getName()}")

def on_disconnect_cb(client: paho.Client, userdata: any, disconnect_flags: paho.DisconnectFlags,
                     reason_code: paho.ReasonCode, properties: paho.Properties):
    print(f"DISCONNECTED! Reason code ({reason_code.value}) {reason_code.getName()}!")
    
mqtt_client.on_connect = on_connect_cb
mqtt_client.on_disconnect = on_disconnect_cb

mqtt_topic_root = os.environ["mqtt_topic_root"]

# connect to MQTT Cloud on port 8883 (default for MQTT)
mqtt_client.connect(os.environ["mqtt_server"], int(mqtt_port))

# Hook up to termination signal (for docker image) and CTRL-C
print("Listening to streams. Press CTRL-C to exit.")

sdf = app.dataframe(input_topic)

def publish_to_mqtt(data, key, timestamp, headers):
    json_data = json.dumps(data)
    message_key_string = key.decode('utf-8')  # Convert to string using utf-8 encoding
    # publish to MQTT
    mqtt_client.publish(mqtt_topic_root + "/" + message_key_string, payload = json_data, qos = 1)

sdf = sdf.apply(publish_to_mqtt, metadata=True)


# start the background process to handle MQTT messages
mqtt_client.loop_start()

print("Starting application")
# run the data processing pipeline
app.run(sdf)

# stop handling MQTT messages
mqtt_client.loop_stop()
print("Exiting")