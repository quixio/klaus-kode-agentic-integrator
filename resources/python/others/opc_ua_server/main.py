import asyncio
import logging
from datetime import datetime
import time
import math
from asyncua import ua, uamethod, Server


_logger = logging.getLogger(__name__)

# output min and max
MIN_VALUE = 80
MAX_VALUE = 100


def scale_sin_to_range(min_value, max_value):
    # Get the current sine value
    sine_value = math.sin(time.time())
    # Scale it to the range [80, 100]
    scaled_value = ((sine_value + 1) / 2) * (max_value - min_value) + min_value
    return scaled_value


class SubHandler:
    """
    Subscription Handler. To receive events from server for a subscription
    """

    def datachange_notification(self, node, val, data):
        _logger.warning("Python: New data change event %s %s", node, val)

    def event_notification(self, event):
        _logger.warning("Python: New event %s", event)


# method to be exposed through server
def func(parent, variant):
    ret = False
    if variant.Value % 2 == 0:
        ret = True
    return [ua.Variant(ret, ua.VariantType.Boolean)]


# method to be exposed through server
# uses a decorator to automatically convert to and from variants
@uamethod
def multiply(parent, x, y):
    _logger.warning("multiply method call with parameters: %s %s", x, y)
    return x * y


async def main():
    server = Server()
    await server.init()

    server.set_endpoint("opc.tcp://0.0.0.0:4840/freeopcua/server/")
    server.set_server_name("FreeOpcUa Example Server")
    # set all possible endpoint policies for clients to connect through
    server.set_security_policy(
        [
            ua.SecurityPolicyType.NoSecurity,
            ua.SecurityPolicyType.Basic256Sha256_SignAndEncrypt,
            ua.SecurityPolicyType.Basic256Sha256_Sign,
        ]
    )

    # setup our own namespace
    uri = "http://quix.freeopcua.io"
    idx = await server.register_namespace(uri)

    # create a new node type we can instantiate in our address space
    dev = await server.nodes.base_object_type.add_object_type(idx, "MyDevice")
    await (await dev.add_variable(idx, "sensor1", 1.0)).set_modelling_rule(True)
    await (await dev.add_property(idx, "device_id", "0340")).set_modelling_rule(True)
    ctrl = await dev.add_object(idx, "controller")
    await ctrl.set_modelling_rule(True)
    await (await ctrl.add_property(idx, "state", "Idle")).set_modelling_rule(True)

    # instanciate one instance of our device
    mydevice = await server.nodes.objects.add_object(idx, "Device0001", dev)
    mydevice_var = await mydevice.get_child(
        [f"{idx}:controller", f"{idx}:state"]
    )  # get proxy to our device state variable
    
    # create directly some objects and variables
    printer = await server.nodes.objects.add_object(idx, "3D_PRINTER_1")
    probe1 = await printer.add_variable(idx, "THERMO_PROBE_1", 99.8)
    probe2 = await printer.add_variable(idx, "THERMO_PROBE_2", 0.1)
    
    # Set to be writable by clients
    await probe1.set_writable()
    await probe2.set_writable()
    
    # creating a default event object
    # The event object automatically will have members for all events properties
    # you probably want to create a custom event type, see other examples
    myevgen = await server.get_event_generator()
    myevgen.event.Severity = 300

    # starting!
    async with server:
        print("Available loggers are: ", logging.Logger.manager.loggerDict.keys())
        await mydevice_var.write_value("Running")
        await myevgen.trigger(message="This is BaseEvent")

        # Send an initial value / this could be the current value or a default.
        await server.write_attribute_value(probe1.nodeid, ua.DataValue(99.8, ServerTimestamp=datetime.utcnow()))
        await server.write_attribute_value(probe2.nodeid, ua.DataValue(0.9, ServerTimestamp=datetime.utcnow()))
        await asyncio.sleep(0.1)

        while True:
            # Update probe1 with a scaled sine value
            scaled_value_1 = scale_sin_to_range(MIN_VALUE, MAX_VALUE)
            await server.write_attribute_value(probe1.nodeid, ua.DataValue(scaled_value_1, ServerTimestamp=datetime.utcnow()))

            # Update probe2 with a different scaled sine value or another logic
            scaled_value_2 = scale_sin_to_range(MIN_VALUE*2, MAX_VALUE*2)  # or another logic
            await server.write_attribute_value(probe2.nodeid, ua.DataValue(scaled_value_2, ServerTimestamp=datetime.utcnow()))

            await asyncio.sleep(0.2)
            

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())