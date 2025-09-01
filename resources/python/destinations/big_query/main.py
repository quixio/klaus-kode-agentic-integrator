import os
from setup_logger import logger

from quixstreams import Application

# for local dev, load env vars from a .env file
from dotenv import load_dotenv
load_dotenv()

from big_query_sink import BigQuerySink

TABLE_NAME = os.environ["TABLE_NAME"]
PROJECT_ID = os.environ["PROJECT_ID"]
DATASET_ID = os.environ["DATASET_ID"]
DATASET_LOCATION = os.environ["DATASET_LOCATION"]
SERVICE_ACCOUNT_JSON = os.environ["SERVICE_ACCOUNT_JSON"]

big_query_sink = BigQuerySink(
    PROJECT_ID, 
    DATASET_ID, 
    DATASET_LOCATION,
    TABLE_NAME, 
    SERVICE_ACCOUNT_JSON,
    logger)

big_query_sink.connect()

app = Application(
    consumer_group=os.environ["CONSUMER_GROUP"], 
    auto_offset_reset = "earliest",
    commit_interval=1,
    commit_every=100)

input_topic = app.topic(os.environ["input"])

sdf = app.dataframe(input_topic)
sdf.sink(big_query_sink)

if __name__ == "__main__":
    app.run(sdf)
