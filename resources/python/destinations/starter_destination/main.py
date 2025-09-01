# import the Quix Streams modules for interacting with Kafka.
# For general info, see https://quix.io/docs/quix-streams/introduction.html
# For sinks, see https://quix.io/docs/quix-streams/connectors/sinks/index.html
from quixstreams import Application
from quixstreams.sinks import BatchingSink, SinkBatch, SinkBackpressureError

import os
import time

# for local dev, you can load env vars from a .env file
# from dotenv import load_dotenv
# load_dotenv()


class MyDatabaseSink(BatchingSink):
    """
    Sinks are a way of writing data from a Kafka topic to a non-Kafka destination,
    often some sort of database or file.

    This is a custom placeholder Sink which showcases a simple pattern around
    creating your own for a database.

    There are numerous pre-built sinks available to use out of the box; see:
    https://quix.io/docs/quix-streams/connectors/sinks/index.html
    """
    def _write_to_db(self, data):
        """Placeholder for transformations and database write operation"""
        ...

    def write(self, batch: SinkBatch):
        """
        Every Sink requires a .write method.

        Here is where we attempt to write batches of data (multiple consumed messages,
        for the sake of efficiency/speed) to our database.

        Sinks have sanctioned patterns around retrying and handling connections.

        See https://quix.io/docs/quix-streams/connectors/sinks/custom-sinks.html for
        more details.
        """
        attempts_remaining = 3
        data = [item.value for item in batch]
        while attempts_remaining:
            try:
                return self._write_to_db(data)
            except ConnectionError:
                # Maybe we just failed to connect, do a short wait and try again
                # We can't repeat forever; the consumer will eventually time out
                attempts_remaining -= 1
                if attempts_remaining:
                    time.sleep(3)
            except TimeoutError:
                # Maybe the server is busy, do a sanctioned extended pause
                # Always safe to do, but will require re-consuming the data.
                raise SinkBackpressureError(
                    retry_after=30.0,
                    topic=batch.topic,
                    partition=batch.partition,
                )
        raise Exception("Error while writing to database")


def main():
    """ Here we will set up our Application. """

    # Setup necessary objects
    app = Application(
        consumer_group="my_db_destination",
        auto_create_topics=True,
        auto_offset_reset="earliest"
    )
    my_db_sink = MyDatabaseSink()
    input_topic = app.topic(name=os.environ["input"])
    sdf = app.dataframe(topic=input_topic)

    # Do SDF operations/transformations
    sdf = sdf.apply(lambda row: row).print(metadata=True)

    # Finish by calling StreamingDataFrame.sink()
    sdf.sink(my_db_sink)

    # With our pipeline defined, now run the Application
    app.run()


# It is recommended to execute Applications under a conditional main
if __name__ == "__main__":
    main()
