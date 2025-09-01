import os
from flask import Flask, request, Response, redirect
from flasgger import Swagger
from waitress import serve

from setup_logging import get_logger

# for local dev, load env vars from a .env file
from dotenv import load_dotenv
load_dotenv()

logger = get_logger()

app = Flask(__name__)

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

    # do something with your data here.
    # to see how to publish data to a Quix topic, see this connector:
    # https://github.com/quixio/quix-samples/tree/main/python/sources/http_source

    response = Response(status=200)
    response.headers.add('Access-Control-Allow-Origin', '*')

    return response


if __name__ == '__main__':

    service_url = os.environ["Quix__Deployment__Network__PublicUrl"]

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
