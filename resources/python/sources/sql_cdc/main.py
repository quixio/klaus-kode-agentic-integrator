from quixstreams import Application
import time
from datetime import datetime
import os
import pyodbc
import sqlite3
import json
import helper_functions

# Load environment variables (useful when working locally)
from dotenv import load_dotenv
load_dotenv()

last_modified_storage_key = "LAST_MODIFIED"

config = helper_functions.load_config()
database_name = config['database']
table_name = config["table_name"]

# Create a Quix Application, this manages the connection to the Quix platform
app = Application()

# Create the producer, this is used to write data to the output topic
producer = app.get_producer()

# Check the output topic is configured
output_topic_name = os.getenv("output", "")
if output_topic_name == "":
    raise ValueError("output_topic environment variable is required")
output_topic = app.topic(output_topic_name)

# Initialize SQLite DB and connect
# this will be used for state storage of the last timestamp read from the SQL server db
sqlite_db_path = './sqlite_state_storage.db'
conn_sqlite = sqlite3.connect(sqlite_db_path)
cursor_sqlite = conn_sqlite.cursor()

# Create table to store the last_modified timestamp
cursor_sqlite.execute('''
    CREATE TABLE IF NOT EXISTS state_storage (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
''')
conn_sqlite.commit()


print("connecting...")
conn = pyodbc.connect(f"Driver={config['driver']};Server={config['server']};UID={config['user_id']};PWD={config['password']};Database={config['database']};TrustServerCertificate=yes;")
print("CONNECTED!")

poll_for_data = True 

offset = None
# Check if the last_modified key exists in SQLite DB
cursor_sqlite.execute('SELECT value FROM state_storage WHERE key = ?', (last_modified_storage_key,))
row = cursor_sqlite.fetchone()
if row is not None:
    offset = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
else:
    # Set the initial offset value if not present in SQLite DB
    if config["use_utc"]:
        offset = datetime.utcnow()
    else:
        offset = datetime.now()
    offset = offset - config["time_delta"]
    offset = offset.strftime("%Y-%m-%d %H:%M:%S")
    cursor_sqlite.execute('INSERT OR REPLACE INTO state_storage (key, value) VALUES (?, ?)',
                          (last_modified_storage_key, offset))
    conn_sqlite.commit()


def main():
    global offset
    while poll_for_data:
        print(f"Looking for data newer than: {offset}")

        start_time = time.time()

        if not helper_functions.check_table_exists(conn, table_name):
            raise Exception(f"A table called '{table_name}' was not found in the database")

        sql = f"SELECT * FROM {table_name} WHERE '{offset}' > '{1}' ORDER By {config['last_modified_column']} DESC"

        print(sql)

        cursor = conn.cursor()
        cursor.execute(sql)

        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]

        # Check if there are rows fetched
        if not rows:
            print(f"No new data found, waiting for {config['poll_interval']} seconds")
            time.sleep(config["poll_interval"])
            continue

        # Process and publish each row
        for row in rows:
            data_dict = dict(zip(columns, row))
            # Convert datetime to string if necessary
            if isinstance(data_dict[config["last_modified_column"]], datetime):
                data_dict[config["last_modified_column"]] = data_dict[config["last_modified_column"]].strftime("%Y-%m-%d %H:%M:%S")

            # Rename columns if needed
            if config["rename_cols"] is not None:
                data_dict = {config["rename_cols"].get(k, k): v for k, v in data_dict.items()}

            # Drop columns if needed
            if config["drop_cols"] != "":
                for col in config["drop_cols"].split(","):
                    data_dict.pop(col, None)

            # Publish the data
            print("Publishing data to Kafka")
            producer.produce(topic=output_topic.name, 
                             key=f"{database_name}-{table_name}",
                             value=json.dumps(data_dict))
            
        print(f"Loaded {len(rows)} rows in {str(time.time() - start_time)}")
        start_time = time.time()

        # Update the offset with the newest datetime from the db
        offset = rows[0][columns.index(config["last_modified_column"])]
        cursor_sqlite.execute('INSERT OR REPLACE INTO state_storage (key, value) VALUES (?, ?)',
                            (last_modified_storage_key, str(offset)))
        conn_sqlite.commit()

        time.sleep(config["poll_interval"])


if __name__ == "__main__":
    global run
    try:
        main()
    except KeyboardInterrupt:
        print("Exiting.")
        run = False
    except Exception as e:
        print(f"Unhandled exception {e}")
        run = False
    finally:
        conn.close()
        conn_sqlite.close()
        print("Connection to SQL Server closed")