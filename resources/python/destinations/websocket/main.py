import asyncio
import os
import websockets
from quixstreams import Application
from dotenv import load_dotenv
import json
import base64
load_dotenv()


class WebsocketSource:

    def __init__(self) -> None:
        app = Application(
            consumer_group="web-sockets-server-v100",
            auto_offset_reset="latest",
            loglevel="INFO",
        )
        self._topic = app.topic(name=os.environ["input"])

        self._consumer = app.get_consumer()
        self._consumer.subscribe([self._topic.name])

        # Holds all client connections partitioned by page.
        self.websocket_connections = {}

        # Instead of directly creating a task in the constructor,
        # we'll start the task from outside to avoid issues with incomplete initialization.

    async def consume_messages(self):
        while True:
            message = self._consumer.poll(1)
            if message is not None:
                value = json.loads(bytes.decode(message.value()))
                key = bytes.decode(message.key())

                # Check if the key or '*' is in the websocket_connections
                if key in self.websocket_connections or '*' in self.websocket_connections:

                    # Send to clients connected with the specific key
                    if key in self.websocket_connections:
                        for client in self.websocket_connections[key]:
                            try:
                                await client.send(json.dumps(value))
                            except:
                                print("Connection already closed.")
                    
                    # Send to clients connected with the wildcard '*'
                    if '*' in self.websocket_connections:
                        for client in self.websocket_connections['*']:
                            try:
                                await client.send(json.dumps(value))
                            except:
                                print("Connection already closed.")

                    # uncomment for debugging
                    # print(value)
                    # print(f"Send to {key} {str(len(self.websocket_connections[key]))} times.")

                # give the other process a chance to handle some data
                await asyncio.sleep(0.001)
            else:
                await asyncio.sleep(1)

    async def handle_websocket(self, websocket):
        path = websocket.request.path.lstrip('/')
        print("========================================")
        print(f"Client connected to socket. Path={path}")
        print("========================================")

        if not self.authenticate(websocket):
            print("Unauthorized incomming connection")
            await websocket.close(code=1008, reason="Unauthorized")
            return
        else:
            print("Incomming connection authorized")

        if path not in self.websocket_connections:
            self.websocket_connections[path] = []

        self.websocket_connections[path].append(websocket)

        try:
            print("Keep the connection open and wait for messages if needed")
            await websocket.wait_closed()
        except websockets.exceptions.ConnectionClosedOK:
            print(f"Client {path} disconnected normally.")
        except websockets.exceptions.ConnectionClosed as e:
            print(f"Client {path} disconnected with error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
        finally:
            print("Removing client from connection list")
            if path in self.websocket_connections:
                self.websocket_connections[path].remove(websocket)  # Use `del` to remove items from a dictionary

    def authenticate(self, websocket):
        auth_header = websocket.request.headers.get('Authorization')
        if auth_header is None or not auth_header.startswith('Basic '):
            return False

        encoded_credentials = auth_header.split(' ')[1]
        decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
        username, password = decoded_credentials.split(':')

        # Replace with your actual username and password
        return username == os.environ["WS_USERNAME"] and password == os.environ["WS_PASSWORD"]

    async def start_websocket_server(self):
        host = "0.0.0.0"
        port = 80
        print(f"Starting WebSocket server on {host}:{port}")
        print("Listening for websocket connections..")
        server = await websockets.serve(self.handle_websocket, host, port)
        await server.wait_closed()


async def main():
    client = WebsocketSource()
    # Start consuming messages as a separate task
    asyncio.create_task(client.consume_messages())
    await client.start_websocket_server()


# Run the application with exception handling
try:
    asyncio.run(main())
except Exception as e:
    print(f"An error occurred: {e}")