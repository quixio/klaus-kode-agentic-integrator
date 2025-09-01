import os
import datetime
import json
from flask import Flask, request, Response, redirect
from flasgger import Swagger
from waitress import serve
import time

from flask_cors import CORS

from setup_logging import get_logger
from quixstreams import Application

# for local dev, load env vars from a .env file
from dotenv import load_dotenv
load_dotenv()

service_url = os.environ["Quix__Deployment__Network__PublicUrl"]

quix_app = Application()
topic = quix_app.topic(os.environ["output"])
producer = quix_app.get_producer()

logger = get_logger()

app = Flask(__name__)

# Enable CORS for all routes and origins by default
CORS(app)

app.config['SWAGGER'] = {
    'title': 'HTTP API Source',
    'description': 'Test your HTTP API with this Swagger interface. Send data and see it arrive in Quix.',
    'uiversion': 3
}

swagger = Swagger(app)

@app.route("/", methods=['GET'])
def redirect_to_swagger():
    return redirect("/apidocs/")

@app.route("/data/", methods=['POST'])
def post_data_without_key():
    """
    Post data without key
    ---
    parameters:
      - in: body
        name: body
        schema:
          type: object
          properties:
            some_value:
              type: string
    responses:
      200:
        description: Data received successfully
    """
    data = request.json
    logger.debug(f"{data}")

    producer.produce(topic.name, json.dumps(data))

    # Return a normal 200 response; CORS headers are added automatically by Flask-CORS 
    return Response(status=200)

@app.route("/data/<key>", methods=['POST'])
def post_data_with_key(key: str):
    """
    Post data with a key
    ---
    parameters:
      - in: path
        name: key
        type: string
        required: true
      - in: body
        name: body
        schema:
          type: object
          properties:
            some_value:
              type: string
    responses:
      200:
        description: Data received successfully
    """
    data = request.json
    logger.debug(f"{data}")

    producer.produce(topic.name, json.dumps(data), key.encode())

    return Response(status=200)

if __name__ == '__main__':
    print("=" * 60)
    print(" " * 20 + "CURL EXAMPLE")
    print("=" * 60)
    print(
        f"""
curl -L -X POST \\
    -H 'Content-Type: application/json' \\
    -d '{{"key": "value"}}' \\
    {service_url}/data
    """
    )
    print("=" * 60)

    serve(app, host="0.0.0.0", port=80)