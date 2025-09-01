# WebSocket Destination

A service that streams data from a Quix input stream to connected WebSocket clients.

## Overview

This service receives data from a Quix input stream and forwards it to all connected WebSocket clients. It acts as a bridge between Quix and any application that can consume WebSocket data.

## Configuration

The service requires the following environment variables:

| Variable | Description |
|----------|-------------|
| `input` | The input topic name to listen to in Quix |
| `WS_USERNAME` | Username for WebSocket authentication (Required: `True`) |
| `WS_PASSWORD` | Password for WebSocket authentication (Required: `True`) |

### Authentication

Authentication is required and is easy to configure. Provide a user name and password in the above environment variables, these will be used to authenticate users.

If deploying to Quix Cloud you will need to create secrets for the username and password.
See the [docs](https://quix.io/docs/deploy/secrets-management.html) for more information on how to do this.

## Connecting

To connect to the websocket server from your client use the url, ip address or server name for the websocket server (including the port) and the message key from the incomming topic.

For example, if your ip address is `127.0.0.1`, your port is `80` and your message key is `DATA001` your connection url would be:

`ws://127.0.0.1:80/DATA001` Connecting to this websocket URL will allow you to receive data for the `DATA001` message key only.

Alternatively to subscribe to data from all message keys use `*`:

`ws://127.0.0.1:80/*` Connecting to this websocket URL will allow you to receive data for all message keys.

NOTE: if deploying on a secure port use `wss://` in place os `ws://` (Quix Cloud uses secure connections)

## Data Format

Data is sent as JSON strings over the WebSocket connection. The format mirrors the structure received from Quix, including timestamp, tag names, and values.

## Running Locally

1. Set up the required environment variables
2. Install dependencies: `pip install -r requirements.txt`
3. Run the service: `python main.py`

## Deploying to Quix

This sample can be deployed directly to your Quix environment.

Create a [Quix](https://portal.platform.quix.io/signup?xlink=github) account or log-in to your existing environment and visit the `Connectors` tab to use this connector.

Clicking `Set up connector` allows you to enter your connection details and runtime parameters.

Then either: 
* click `Test connection & deploy` to deploy the pre-built and configured container into Quix. 

* or click `Customise connector` to inspect or alter the code before deployment.

## Example code

An example of how to connect to this server from a `javascript` client is shown below.

```js
// Example client to connect to the websocket server
const WebSocket = require('websocket').client;
// or use browser WebSocket API: const ws = new WebSocket(url);

// Connection details
const url = "ws://your-server-address"; // Replace with actual address
const username = "your-username"; // Must match WS_USERNAME env variable 
const password = "your-password"; // Must match WS_PASSWORD env variable
const path = "your-topic-name"; // Or use "*" for all messages

// Create connection with basic auth
const ws = new WebSocket();
ws.connect(`${url}/${path}`, null, null, {
  "Authorization": "Basic " + Buffer.from(`${username}:${password}`).toString("base64")
});

// Handle connection events
ws.on('connect', (connection) => {
  console.log('Connected to WebSocket server');
  
  // Handle incoming messages
  connection.on('message', (message) => {
    if (message.type === 'utf8') {
      const data = JSON.parse(message.utf8Data);
      console.log('Received data:', data);
    }
  });
  
  // Handle connection close
  connection.on('close', () => {
    console.log('Connection closed');
  });
});

// Handle connection errors
ws.on('connectFailed', (error) => {
  console.error('Connection failed:', error.toString());
});
```

## Limitations

- The service does not support bidirectional communication - it only sends data from Quix topics to WebSocket clients

## Contribute

Submit forked projects to the Quix [GitHub](https://github.com/quixio/quix-samples) repo. Any new project that we accept will be attributed to you and you'll receive $200 in Quix credit.

## Open Source

This project is open source under the Apache 2.0 license and available in our [GitHub](https://github.com/quixio/quix-samples) repo. Please star us and mention us on social to show your appreciation.

