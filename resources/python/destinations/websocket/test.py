import asyncio
import websockets
import base64

async def connect():
    # NOTE: If using the URL from the websocket server deployed in Quix Cloud, replace the https:// protocol with wss://
    uri = "YOUR WEBSOCKET URL"
    username = "admin" # set to your username
    password = "admin" # set to your password
    
    # Encode credentials
    credentials = f"{username}:{password}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    
    # Define headers
    headers = {
        "Authorization": f"Basic {encoded_credentials}"
    }
    
    try:
        async with websockets.connect(uri, extra_headers=headers) as websocket:
            print("Connected to the WebSocket server")
            
            while True:
                response = await websocket.recv()
                print(f"Received from server: {response}")

    except Exception as e:
        print(f"An error occurred while connecting: {e}")

# Run the connect function
asyncio.get_event_loop().run_until_complete(connect())