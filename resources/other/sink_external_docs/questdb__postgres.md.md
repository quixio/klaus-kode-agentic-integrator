### Postgres sink to use as a reference for questdb

The following code contains a quix sink template that is written for PostGres, but can be useful for connecting to Postgres too since they questdb supports the postgres operations.


```python

import os
from quixstreams import Application
from quixstreams.sinks.community.postgresql import (
    PostgreSQLSink,
    PrimaryKeySetter,
    TableName,
)
# Load environment variables from a .env file for local development
from dotenv import load_dotenv
load_dotenv()


def _as_bool(env_var: str, default="false") -> bool:
    return os.environ.get(env_var, default).lower() == "true"


def _as_iterable(env_var) -> list[str]:
    return keys.split(",") if (keys := os.environ.get(env_var)) else []


# Potential Callables - can manually edit these to instead use your own callables.
# --Required--
table_name: TableName = os.getenv("POSTGRES_TABLE", "default_table")
# --Optional--
primary_key_columns: PrimaryKeySetter = _as_iterable("POSTGRES_PRIMARY_KEY_COLUMNS")


# Initialize PostgreSQL Sink
postgres_sink = PostgreSQLSink(
    host=os.environ["POSTGRES_HOST"],
    port=int(os.environ["POSTGRES_PORT"]),
    dbname=os.environ["POSTGRES_DBNAME"],
    user=os.environ["POSTGRES_USER"],
    password=os.environ["POSTGRES_PASSWORD"],
    table_name=table_name,
    schema_name=os.getenv("POSTGRES_SCHEMA", "public"),
    schema_auto_update=_as_bool("POSTGRES_SCHEMA_AUTO_UPDATE", "true"),
    primary_key_columns=primary_key_columns,
    upsert_on_primary_key=_as_bool("POSTGRES_UPSERT_ON_PRIMARY_KEY"),
)

# Initialize the application
app = Application(
    consumer_group=os.environ["CONSUMER_GROUP_NAME"],
    auto_offset_reset="earliest",
    commit_interval=float(os.environ.get("BATCH_TIMEOUT", "1")),
    commit_every=int(os.environ.get("BATCH_SIZE", "1000"))
)

# Define the input topic
input_topic = app.topic(os.environ["input"], key_deserializer="string")

# Process and sink data
sdf = app.dataframe(input_topic)
sdf.sink(postgres_sink)

if __name__ == "__main__":
    app.run(sdf)

```