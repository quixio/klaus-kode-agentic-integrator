from datetime import timedelta
import os
import json


def load_config():
    driver = os.environ["driver"]
    server = os.environ["server"]
    user_id = os.environ["userid"]
    password = os.environ["password"]
    database = os.environ["database"]
    table_name = os.environ["table_name"]
    last_modified_column = os.environ["last_modified_column"]
    time_delta_config = os.environ["time_delta"]
    
    try:
        use_utc_for_offset = bool(os.environ["offset_is_utc"])
    except Exception as e:
        raise Exception("Use UTC For Offset must be True or False", e)

    drop_cols = os.getenv("columns_to_drop")
    rename_cols = None
    passed_rename_cols = os.getenv("columns_to_rename")
    
    try:
        poll_interval = int(os.environ["poll_interval_seconds"])
    except Exception as e:
        raise Exception("Poll Interval must be an integer", e)

    if poll_interval < 1:
        poll_interval = 1

    try:
        if passed_rename_cols != None and passed_rename_cols != "":
            rename_cols = json.loads(passed_rename_cols)
    except Exception as e:
        raise Exception("Invalid JSON supplied for column renames", e)

    return {
            "driver": driver,
            "server": server,
            "user_id": user_id,
            "password": password,
            "database": database,
            "table_name": table_name,
            "last_modified_column": last_modified_column,
            "time_delta": make_time_delta_from_config(time_delta_config),
            "drop_cols": drop_cols,
            "rename_cols": rename_cols,
            "use_utc": use_utc_for_offset,
            "poll_interval": poll_interval
            }


def make_time_delta_from_config(time_delta_config) -> timedelta:
    time_delta_values = time_delta_config.split(",")

    if len(time_delta_values) != 5:
        raise Exception(
            "time_delta_config must contain 5 values, one for each of seconds, minutes, hours, days and weeks")

    try:
        seconds = int(time_delta_values[0])
        minutes = int(time_delta_values[1])
        hours = int(time_delta_values[2])
        days = int(time_delta_values[3])
        weeks = int(time_delta_values[4])
        return timedelta(seconds = seconds, minutes = minutes, hours = hours, days = days, weeks = weeks)
    except TypeError as te:
        raise Exception("Unable to cast one of the supplied values to int", te)
    except Exception as e:
        raise Exception("Something went wrong configuring the time delta", e)


def check_table_exists(conn, table) -> bool:
    if not conn.cursor().tables(table).fetchone():
        print("Table does not exist")
        return False
    return True


def check_column_exists(conn, table, column_name) -> bool:
    for c in conn.cursor().columns(table = table):
        if column_name == c.column_name:
            return True
    print("Key column [{}] not found in table [{}]".format(column_name, table))
    return False


def drop_columns(conn, cols_to_drop, table_data, table_name) -> any:
    for col in cols_to_drop:
        if check_column_exists(conn, table_name, col):
            table_data = table_data.drop(col, 1)
    return table_data


def rename_columns(conn, cols_to_rename, table_data, table_name) -> any:
    for col in cols_to_rename:
        if check_column_exists(conn, table_name, col):
            table_data = table_data.rename(columns={col: cols_to_rename[col]})
    return table_data