import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import asyncio
import websockets
import json
import time
import base64

# NOTE: Assume data looks something like:
# {"temperature_c": 54, "cpu_usage_percent": 51, "timestamp": 1737612795.0035408}


def stop():
    st.session_state.is_connected = False


def start():
    st.session_state.is_connected = True


# Streamlit Dashboard

st.title("WebSocket Live Data Viewer")

# Setting up this way allows us to return to login screen after Stop button
if "is_connected" not in st.session_state:
    st.session_state["is_connected"] = False

# Authentication and options
if not st.session_state.is_connected:
    st.text_input("Websocket base URL", type="default", key="wss_root_url", value="ws://localhost:80")
    st.text_input("Websocket Username", type="default", key="wss_username", value="")
    st.text_input("Websocket Password", type="password", key="wss_password", value="")
    st.text_input("Stream Keys", type="default", key="stream_key", value="*")
    st.text_input("Columns", type="default", key="columns", value="*")
    st.text_input("Max data points", type="default", key="max_points", value=10000)
    st.button("Start!", on_click=start)
else:
    # WARNING: closing a tab without hitting this button will cause the below loop
    # to remain running until the main streamlit app is fully shutdown!
    st.button("Stop", on_click=stop)

    # Endless loop with the websocket connection
    # We never re-run the entire streamlit dashboard anymore, only components
    # of it dynamically update
    # Hitting the stop button will exit this loop
    async def websocket_handler():
        # some placeholders for later in-place additions
        status_placeholder = st.empty()
        plot_placeholder = st.empty()

        # establish variables from session cache
        columns = "*" if st.session_state.columns == "*" else st.session_state.columns.split(",")
        max_points = int(st.session_state.max_points)

        # Initialize variables/objects
        last_redraw = 0
        all_data = pd.DataFrame()
        # plotly figure (we fill it with data over time)
        fig = go.Figure()
        fig.update_layout(
            title=f"Latest {max_points} Events Stream",
            xaxis_title="Timestamp",
            yaxis_title="Column Values",
            legend_title="Column Names",
        )

        # Setup websocket connection
        auth_token = base64.b64encode(f"{st.session_state.wss_username}:{st.session_state.wss_password}".encode()).decode()
        headers = [("Authorization", f"Basic {auth_token}")]

        url = f"{st.session_state.wss_root_url}/{st.session_state.stream_key}"
        status_placeholder.write(f"Connecting to WebSocket {url}...")

        # Connect to WebSocket
        async with websockets.connect(url, additional_headers=headers) as ws:
            status_placeholder.write("Connected!")

            while st.session_state.is_connected:
                data = await ws.recv()
                data = json.loads(data)

                # Extract timestamp for index, filter columns if needed
                timestamp = data.pop("timestamp")
                data = data if columns == "*" else {k: data[k] for k in columns}
                record = pd.DataFrame(data, index=[pd.to_datetime(timestamp, unit="ms")])

                # append new record, remove oldest records if max is reached
                if all_data.empty:
                    all_data = record
                else:
                    all_data = pd.concat([all_data, record]).sort_index().iloc[-max_points:]

                # Redraw plot no sooner than 250ms since last drawn
                if (current_time := time.time()) - last_redraw >= 0.25:
                    fig.data = []
                    fig.add_traces([
                        go.Scatter(
                            x=all_data.index,
                            y=all_data[column],
                            mode='lines',
                            name=column
                        ) for column in all_data.columns
                    ])

                    plot_placeholder.plotly_chart(
                        fig,
                        use_container_width=True,
                        key=current_time
                    )
                    last_redraw = current_time
        print(f"Websocket closed")

    asyncio.run(websocket_handler())