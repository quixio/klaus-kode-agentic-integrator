# import Utility modules
import os

# import vendor-specific modules
from quixstreams import Application
from quixstreams.sinks.core.influxdb3 import InfluxDB3Sink

# for local dev, load env vars from a .env file
from dotenv import load_dotenv
load_dotenv()


tag_keys = keys.split(",") if (keys := os.environ.get("INFLUXDB_TAG_KEYS")) else []
field_keys = keys.split(",") if (keys := os.environ.get("INFLUXDB_FIELD_KEYS")) else []
measurement_name = os.environ.get("INFLUXDB_MEASUREMENT_NAME", "measurement1")
time_setter = col if (col := os.environ.get("TIMESTAMP_COLUMN")) else None

influxdb_v3_sink = InfluxDB3Sink(
    token=os.environ["INFLUXDB_TOKEN"],
    host=os.environ["INFLUXDB_HOST"],
    organization_id=os.environ["INFLUXDB_ORG"],
    tags_keys=tag_keys,
    fields_keys=field_keys,
    time_setter=time_setter,
    database=os.environ["INFLUXDB_DATABASE"],
    measurement=measurement_name,
)


app = Application(
    consumer_group=os.environ.get("CONSUMER_GROUP_NAME", "influxdb-data-writer"),
    auto_offset_reset="earliest",
    commit_every=int(os.environ.get("BUFFER_SIZE", "1000")),
    commit_interval=float(os.environ.get("BUFFER_DELAY", "1")),
)
input_topic = app.topic(os.environ["input"])

sdf = app.dataframe(input_topic)
sdf.sink(influxdb_v3_sink)


if __name__ == "__main__":
    app.run()
