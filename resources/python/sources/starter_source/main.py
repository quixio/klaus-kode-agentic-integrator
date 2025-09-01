# import the Quix Streams modules for interacting with Kafka.
# For general info, see https://quix.io/docs/quix-streams/introduction.html
# For sources, see https://quix.io/docs/quix-streams/connectors/sources/index.html
from quixstreams import Application
from quixstreams.sources import Source

import os

# for local dev, you can load env vars from a .env file
# from dotenv import load_dotenv
# load_dotenv()


class MemoryUsageGenerator(Source):
    """
    A Quix Streams Source enables Applications to read data from something other
    than Kafka and publish it to a desired Kafka topic.

    You provide a Source to an Application, which will handle the Source's lifecycle.

    In this case, we have built a new Source that reads from a static set of
    already loaded json data representing a server's memory usage over time.

    There are numerous pre-built sources available to use out of the box; see:
    https://quix.io/docs/quix-streams/connectors/sources/index.html
    """

    memory_allocation_data = [
        {"m": "mem", "host": "host1", "used_percent": 64.56, "time": 1577836800000000000},
        {"m": "mem", "host": "host2", "used_percent": 71.89, "time": 1577836801000000000},
        {"m": "mem", "host": "host1", "used_percent": 63.27, "time": 1577836803000000000},
        {"m": "mem", "host": "host2", "used_percent": 73.45, "time": 1577836804000000000},
        {"m": "mem", "host": "host1", "used_percent": 62.98, "time": 1577836806000000000},
        {"m": "mem", "host": "host2", "used_percent": 74.33, "time": 1577836808000000000},
        {"m": "mem", "host": "host1", "used_percent": 65.21, "time": 1577836810000000000},
    ]

    def run(self):
        """
        Each Source must have a `run` method.

        It will include the logic behind your source, contained within a
        "while self.running" block for exiting when its parent Application stops.

        There a few methods on a Source available for producing to Kafka, like
        `self.serialize` and `self.produce`.
        """
        data = iter(self.memory_allocation_data)
        # either break when the app is stopped, or data is exhausted
        while self.running:
            try:
                event = next(data)
                event_serialized = self.serialize(key=event["host"], value=event)
                self.produce(key=event_serialized.key, value=event_serialized.value)
                print("Source produced event successfully!")
            except StopIteration:
                print("Source finished producing messages.")
                return


def main():
    """ Here we will set up our Application. """

    # Setup necessary objects
    app = Application(consumer_group="data_producer", auto_create_topics=True)
    memory_usage_source = MemoryUsageGenerator(name="memory-usage-producer")
    output_topic = app.topic(name=os.environ["output"])

    # --- Setup Source ---
    # OPTION 1: no additional processing with a StreamingDataFrame
    # Generally the recommended approach; no additional operations needed!
    app.add_source(source=memory_usage_source, topic=output_topic)

    # OPTION 2: additional processing with a StreamingDataFrame
    # Useful for consolidating additional data cleanup into 1 Application.
    # In this case, do NOT use `app.add_source()`.
    # sdf = app.dataframe(source=source)
    # <sdf operations here>
    # sdf.to_topic(topic=output_topic) # you must do this to output your data!

    # With our pipeline defined, now run the Application
    app.run()


#  Sources require execution under a conditional main
if __name__ == "__main__":
    main()
