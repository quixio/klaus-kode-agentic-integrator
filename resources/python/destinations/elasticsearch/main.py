# import Utility modules
import inspect
import os
import json
from datetime import datetime
from typing import Union, Any, Optional

# import vendor-specific modules
from quixstreams import Application
from quixstreams.sinks.community.elasticsearch import ElasticsearchSink

# LOCAL DEV ONLY: load env vars from .env file using load_dotenv('your/file/path.env')
# from dotenv import load_dotenv
# load_dotenv()


# --------------- environment helper functions ---------------
# These handle the transition between the ElasticsearchSink and connector by
# parsing environment variables.

def get_kwargs_defaults() -> dict[str, Any]:
    """
    Gets the default kwargs of ElasticsearchSink so they can be passed in instances
    where the user did not provide an environment variable.
    """
    params = inspect.signature(ElasticsearchSink.__init__).parameters.values()
    return {
        param.name: param.default for param in params if
        param.default is not inspect.Parameter.empty
    }


def _as_bool(value: Union[str, bool]) -> bool:
    """
    Parse boolean-based arg.
    """
    if isinstance(value, bool):
        return value
    return value.lower() == "true"


def _as_int(value: Union[str, int]) -> int:
    """
    Parse integer-based arg.
    """
    if isinstance(value, str):
        return int(value)
    return value


def _as_optional_dict(value: Optional[str]) -> Optional[dict]:
    """
    Parse optional dict arg.
    """
    if value and isinstance(value, str):
        return json.loads(value)
    return value


# --------------- Application Configuration ---------------


# Create our Application - see documentation for description of various settings
app = Application(
    consumer_group=os.getenv("CONSUMER_GROUP_NAME", "quixstreams-elasticsearch-sink"),
    auto_offset_reset="earliest",
    commit_every=int(os.getenv("BUFFER_SIZE", "1000")),
    commit_interval=float(os.getenv("BUFFER_DELAY", "1"))
)

# Use app to specify ingress topic
input_topic = app.topic(os.environ["input"], key_deserializer="str")


# --------------- Sink Configuration ---------------


kwargs_defaults = get_kwargs_defaults()
elasticsearch_sink = ElasticsearchSink(
    # required settings
    url=os.environ["ELASTICSEARCH_URL"],
    index=os.environ["ELASTICSEARCH_INDEX"],
    # optional settings (have defaults)
    # TODO: remove temporary hard-coded id setter
    document_id_setter=lambda row: f"{row.key}-{str(row.timestamp)}{'-' + str(row.value['id']) if row.value.get('id') else ''}",
    mapping=_as_optional_dict(os.getenv("ELASTICSEARCH_MAPPING", kwargs_defaults["mapping"])),
    batch_size=_as_int(os.getenv("ELASTICSEARCH_BATCH_SIZE", kwargs_defaults["batch_size"])),
    max_bulk_retries=_as_int(os.getenv("ELASTICSEARCH_MAX_BULK_RETRIES", kwargs_defaults["max_bulk_retries"])),
    ignore_bulk_upload_errors=_as_bool(os.getenv("ELASTICSEARCH_IGNORE_BULK_UPLOAD_ERRORS", kwargs_defaults["ignore_bulk_upload_errors"])),
    add_message_metadata=_as_bool(os.getenv("ELASTICSEARCH_ADD_MESSAGE_METADATA", kwargs_defaults["add_message_metadata"])),
    add_topic_metadata=_as_bool(os.getenv("ELASTICSEARCH_ADD_TOPIC_METADATA", kwargs_defaults["add_topic_metadata"])),
    **json.loads(os.environ["ELASTICSEARCH_AUTHENTICATION_JSON"]),
)


# --------------- SDF Configuration ---------------

sdf = app.dataframe(input_topic)
# sdf.print() - can use this to view incoming messages
sdf["time"] = sdf.apply(lambda row, key, timestamp, h: datetime.fromtimestamp(timestamp/1000).isoformat(), metadata=True)
sdf.sink(elasticsearch_sink)


# --------------- Run Application ---------------

if __name__ == "__main__":
    app.run(sdf)
