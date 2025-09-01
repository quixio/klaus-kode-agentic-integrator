from quixstreams import Application
from quixstreams.sinks.community.iceberg import IcebergSink, AWSIcebergConfig
import os

from dotenv import load_dotenv
load_dotenv()

app = Application(consumer_group="destination-v1", 
                  auto_offset_reset = "earliest",
                  commit_interval=5)

input_topic = app.topic(os.environ["input"])

iceberg_sink = IcebergSink(
    data_catalog_spec="aws_glue",
    table_name=os.environ["table_name"],
    config=AWSIcebergConfig(
        aws_s3_uri=os.environ["AWS_S3_URI"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_region=os.environ["AWS_REGION"]))

sdf = app.dataframe(input_topic)
sdf.sink(iceberg_sink)

if __name__ == "__main__":
    app.run(sdf)