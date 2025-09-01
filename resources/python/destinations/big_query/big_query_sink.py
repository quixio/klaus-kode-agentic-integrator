from datetime import datetime
import json
import logging
from logging import Logger
import time

from google.cloud import bigquery
from google.cloud.exceptions import NotFound
from google.oauth2 import service_account

from quixstreams.sinks import SinkBatch
from quixstreams.sinks import BatchingSink

from utils import format_nanoseconds, flatten_json



class BigQuerySink(BatchingSink):
    def __init__(
        self,
        project_id: str,
        dataset_id: str,
        location: str,
        table_name: str,
        service_account_json: str,
        logger: Logger = None
    ):
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.location = location
        self.service_account_json = service_account_json
        self.table_name = table_name
        
        self.columns = []
        
        
        self.logger = logger if logger is not None else logging.getLogger("BigQuery Sink") 

        # Define the format for the logs, including the timestamp
        log_format = '%(asctime)s-%(levelname)s-%(message)s'

        # Configure the basicConfig with the new format and, optionally, the date format
        logging.basicConfig(format=log_format, datefmt='%Y-%m-%d %H:%M:%S')

        super().__init__()
        

        
    def connect(self):
        
        try:
            service_account_info = json.loads(self.service_account_json, strict = False)
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info, scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )

            self.client = bigquery.Client(credentials = credentials, project = credentials.project_id)
            
            self.logger.info("CONNECTED!")
        except Exception as e:
            self.logger.info(f"ERROR!: {e}")
            raise
        
        self._create_dataset()
        self._create_table()
        
    
        

    def write(self, batch: SinkBatch):
        
        all_cols = list(set().union(*map(lambda b: b.value, batch)))
        all_cols = list(set().union([*all_cols, "timestamp", "__key"]))
        
        all_rows = []
        
        last_timestamp = None
        
        for row in batch:
            timestamp = format_nanoseconds(row.timestamp * 1E6)

            last_timestamp = row.timestamp
                
            flatten_row = {
                **flatten_json(row.value),
                "timestamp": timestamp,
                "__key": str(row.key)
            }
            
            r_v = []
            
            for col in all_cols:
                r_v.append(flatten_row.get(col, "NULL"))
                
            all_rows.append(r_v)
    
        self._insert_row(all_cols, all_rows)
        
        start_time = time.time()
        self.logger.debug(f"Data ({batch.size}) from {str(datetime.fromtimestamp(last_timestamp / 1000))} sent in {time.time() - start_time}.")
        
            
    def _create_dataset(self):
        dataset_id = f"{self.project_id}.{self.dataset_id}"
        if not self._dataset_exists(dataset_id):
            dataset = bigquery.Dataset(dataset_id)
            dataset.location = self.location
            dataset = self.client.create_dataset(dataset, timeout = 30)
            self.logger.debug("Created dataset {}.{}".format(self.client.project, dataset.dataset_id))
            
    def _dataset_exists(self, dataset_id: str) -> bool:
        try:
            self.client.get_dataset(dataset_id)
            self.logger.debug("Dataset {} already exists".format(dataset_id))
            return True
        except NotFound:
            self.logger.debug("Dataset {} is not found".format(dataset_id))
            return False
        
    def _insert_row(self, cols: list, vals: list):
        table_id = f"{self.project_id}.{self.dataset_id}.{self.table_name}"

        

        rows_to_insert = []
        for val in vals:
            for index, col in enumerate(cols):
                if col not in self.columns:
                    column_type = "NUMERIC" if isinstance(val[index], (int, float)) else "STRING"
                    self._create_column(self.table_name, col, column_type)
                    self.columns.append(col)
                    print(f"Column {col} added.")
            for i in range(len(val)):
                if type(val[i]) == Null:
                    val[i] = None
            row = dict(zip(cols, val))
            rows_to_insert.append(row)

        errors = self.client.insert_rows_json(table_id, rows_to_insert)
        if errors == []:
            self.logger.debug("New rows have been added.")
        else:
            self.logger.error(f"Encountered errors while inserting rows to {table_id} : {errors}")
            table = self.client.get_table(table_id)
            print(str(table.schema))
            
            raise Exception(errors)
        
        
    def _create_column(self, table_name: str, column_name: str, col_type: str):
        table_id = f"{self.project_id}.{self.dataset_id}.{table_name}"
        table = self.client.get_table(table_id)
        original_schema = table.schema

        if col_type == 'NUMERIC':
            col_type = 'FLOAT64'
        
        if not self._column_exists(original_schema, column_name):

            new_schema = original_schema[:]
            new_schema.append(bigquery.SchemaField(column_name, col_type))
            table.schema = new_schema
            table = self.client.update_table(table, ["schema"])

            if len(table.schema) == len(original_schema) + 1 == len(new_schema):
                self.logger.debug("A new column has been added.")
            else:
                self.logger.error("The column has not been added.")
                
    def _column_exists(self, schema, column_name: str):
        fields = []
        for field in schema:
            fields.append(field.name.lower())

        print(fields)
        if column_name.lower() in fields:
            return True
        else:
            return False
        
    def _create_table(self):
        
        schema = [
            bigquery.SchemaField("timestamp", "TIMESTAMP", mode = "REQUIRED")
        ]
        
        table_id = f"{self.project_id}.{self.dataset_id}.{self.table_name}"
        if not self._table_exists(table_id):
            table = bigquery.Table(table_id, schema = schema)
            table = self.client.create_table(table)
            self.logger.debug(
                "Created table {}.{}.{}".format(table.project, table.dataset_id, table.table_id)
            )
            
    def _table_exists(self, table_id: str):
        try:
            self.client.get_table(table_id)
            self.logger.debug("Table {} already exists.".format(table_id))
            return True
        except NotFound:
            self.logger.debug("Table {} is not found.".format(table_id))
            return False 


class Null:
    def __init__(self):
        self.name = 'NULL'

    def __str__(self):
        return self.name