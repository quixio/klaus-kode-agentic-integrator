import logging
import time
import asyncio
import json

from asyncua import Client, ua
from quixstreams.models.topics import Topic
from quixstreams.sources.base import Source

logger = logging.getLogger('quixstreams')


class OpcUaSource(Source):
    def __init__(
        self,
        name: str,
        opc_url: str,
        opc_namespace: str,
        parameters: str,
        ignore_processing_errors: bool = False,
    ) -> None:  

        self.opc_url = opc_url
        self.opc_namespace = opc_namespace
        self.parameters = parameters
        self.ignore_processing_errors = ignore_processing_errors

        self.tracked_values = {}

        super().__init__(name=name, shutdown_timeout=10)

    def run(self):
        asyncio.run(self.run_async())

    async def run_async(self):
        # Connect to the Netatmo Smart Heating API
        logger.info('Connecting to UPC UA server')

        async with Client(url=self.opc_url) as client:
            namespace_array_node = client.get_node("i=2255")  # NodeId for NamespaceArray
            namespace_array = await namespace_array_node.read_value()
            target_namespace_index = 0
            
            # determine namespace index
            if self.opc_namespace in namespace_array:
                target_namespace_index = namespace_array.index(self.opc_namespace)

            # Get the Objects node
            objects_node = client.nodes.objects
            # Get all child nodes of the Objects node
            objects = await objects_node.get_children()
            
            # Iterate over each object node
            for obj in objects:
                
                # Get the object's browse name
                browse_name = await obj.read_browse_name()
                children = await obj.get_children()
                
                for child in children:
                    child_browse_name = await child.read_browse_name()
                    child_name = child_browse_name.Name
                    try:
                        param_string = f"/Objects/{target_namespace_index}:{browse_name.Name}/{target_namespace_index}:{child_browse_name.Name}"
                        if child_name in self.parameters:
                            myvar = await client.nodes.root.get_child(param_string)
                            self.tracked_values[param_string] = myvar
                    except Exception as e:
                        logger.error(f"{e}; shutting down source...")
                        return

            # subscribing to a variable node
            subscriptions = {}
            handles = {}
            for val in self.tracked_values:
                # Get the node for the current value
                myvar = await client.nodes.root.get_child(val)

                # Create a handler and subscription for each node
                handler = SubHandler(self)
                sub = await client.create_subscription(10, handler)

                # Subscribe to data changes for the node
                handle = await sub.subscribe_data_change(myvar)

                # Store the subscription and handle
                subscriptions[val] = sub
                handles[val] = handle

                # Optional: Sleep to stagger subscriptions
                await asyncio.sleep(0.1)

            # keep working while 'run' flag is True
            logger.info("Subscriptions complete; now handling OPC events...")
            while self.running:
                await asyncio.sleep(1)

            # unsubscribe handlers on exit
            for val in self.tracked_values:
                sub = subscriptions[val]
                handle = handles[val]
                await sub.unsubscribe(handle)
                await sub.delete()

    def default_topic(self) -> Topic:
        return Topic(
            name=self.name,
            key_serializer="string",
            key_deserializer="string",
            value_deserializer="json",
            value_serializer="json",
        )


class SubHandler:

    def __init__(self, opcua_source: OpcUaSource):
        self._source = opcua_source

    async def datachange_notification(self, node, val, data):
        try:
            parent = await node.get_parent()
            machine_browse_name = await parent.read_browse_name()
            machine_name = machine_browse_name.Name

            parameter_browse_name = await node.read_browse_name()
            parameter_name = parameter_browse_name.Name

            logger.debug(f"Data change event for node {machine_name}: {val}")

            # Extract the DataValue from the data parameter
            data_value = data.monitored_item.Value

            # Extract the source timestamp
            server_timestamp = data_value.ServerTimestamp

            if server_timestamp is not None:
                server_timestamp_nanoseconds = int(server_timestamp.timestamp() * 1e9)
            else:
                server_timestamp_nanoseconds = None

            # Extract the variant type
            variant_type = data_value.Value.VariantType

            json_obj = {
                'srv_ts': server_timestamp_nanoseconds,
                'connector_ts': time.time_ns(),
                'type': variant_type.name,
                'val': val,
                'param': parameter_name,
                'machine': machine_name
            }
            json_str = json.dumps(json_obj)
            json_bytes = json_str.encode('utf-8')

            # publish the data to the topic
            self._source.produce(
                key=f'{self._source.opc_namespace}/{machine_name}',
                value=json_bytes,
            )
        except Exception as e:
            if not self._source.ignore_processing_errors:
                logger.error(f"{e}; shutting down source...")
                self._source.stop()

    def event_notification(self, event):
        logger.debug(f"New event: {event}")

    def status_change_notification(self, status):
        logger.info(f"Subscription status changed: {status}")
        if status != ua.StatusCode(ua.StatusCodes.Good):
            logger.error(f"Server shutdown or connection lost. Shutting down...")
            self._source.stop()
