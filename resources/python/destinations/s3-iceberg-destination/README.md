# AWS S3 Iceberg Destination

[This connector](https://github.com/quixio/quix-samples/tree/main/python/destinations/s3-iceberg-destination) demonstrates how to consume data from a Kafka topic and write it to an Apache Iceberg table stored in AWS S3 using the AWS Glue Data Catalog.

## How to run

Create a [Quix](https://portal.platform.quix.io/signup?xlink=github) account or log-in and visit the `Connectors` tab to use this connector.

Clicking `Set up connector` allows you to enter your connection details and runtime parameters.

Then either: 
* click `Test connection & deploy` to deploy the pre-built and configured container into Quix. 

* or click `Customise connector` to inspect or alter the code before deployment.

## Environment Variables

The connector uses the following environment variables:

- **input**: This is the input topic (Default: `input`, Required: `True`)
- **AWS_S3_URI**: The URI or URL to your S3 bucket (Required: `True`)
- **AWS_SECRET_ACCESS_KEY**: Your AWS secret (Required: `True`)
- **AWS_ACCESS_KEY_ID**: Your AWS Access Key (Required: `True`)
- **AWS_REGION**: Your AWS S3 bucket region (Required: `True`)
- **table_name**: The table to publish data to (Required: `True`)

## Requirements / Prerequisites

You will need the appropriate AWS features and access to use this connector.

## Query your data

To query the data from AWS you can use this sample code:

First install pyathena and pandas

`pip install pyathena pandas`

Then update the code below with your connection details and run it to query the data.

```py
from pyathena import connect
import pandas as pd
import os

# Connect to Athena
conn = connect(
    s3_staging_dir='',  # Replace with your S3 bucket for Athena query results
    region_name="eu-north-1", # Replace with your region
    aws_access_key_id='',  # Replace with your AWS access key ID
    aws_secret_access_key=''  # Replace with your AWS secret access key
)

def query_athena(sql_query):
    # Execute the query and load the results into a Pandas DataFrame
    df = pd.read_sql(sql_query, conn)
    return df

data = query_athena("[YOUR SQL QUERY]")
print(data)
```

TIP: We used `'SELECT * FROM "AwsDataCatalog"."glue"."tomas-snakecheating-dev-clickstream"'` as our query.


## Contribute

Submit forked projects to the Quix [GitHub](https://github.com/quixio/quix-samples) repo. Any new project that we accept will be attributed to you and you'll receive $200 in Quix credit.

## Open Source

This project is open source under the Apache 2.0 license and available in our [GitHub](https://github.com/quixio/quix-samples) repo. Please star us and mention us on social to show your appreciation.
