from quixstreams import Application
from flask import Flask, request
from datetime import datetime
from waitress import serve
import os
import json
import hmac
import hashlib

# Load environment variables (useful when working locally)
from dotenv import load_dotenv
load_dotenv()

# Create a Quix Application, this manages the connection to the Quix platform
quix_app = Application()

# Create the producer, this is used to write data to the output topic
producer = quix_app.get_producer()

# Check the output topic is configured
output_topic_name = os.getenv("output", "")
if output_topic_name == "":
    raise ValueError("output_topic environment variable is required")
output_topic = quix_app.topic(output_topic_name)

# create the flask app
flask_app = Flask("Segment Webhook")

# this is unauthenticated, anyone could post anything to you!
@flask_app.route("/webhook", methods=['POST'])
def webhook():
    
    # get the shared secret from environment variables
    secret = os.environ["shared_secret"]
    # convert to a byte array
    secret_bytes = bytearray(secret, "utf-8")

    # get the signature from the headers
    header_sig = request.headers['x-signature']

    # compute a hash-based message authentication code (HMAC)
    hex_digest = hmac.new(secret_bytes, request.get_data(), hashlib.sha1).hexdigest()

    # compare the HMAC to the header signature provided by Segment
    if(header_sig != hex_digest):
        # if they don't match its no bueno
        return "ERROR!", 401
    
    # if they do then publish to the topic
    producer.produce(topic=output_topic.name,
                     key=str(request.json["type"]),
                     value=json.dumps(request.json))

    return "OK", 200


print("CONNECTED!")

# you can use flas_app.run for dev, but its not secure, stable or particularly efficient

# use waitress instead for production
serve(flask_app, host='0.0.0.0', port = 80)