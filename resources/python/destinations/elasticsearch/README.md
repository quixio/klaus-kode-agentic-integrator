# Elasticsearch

[This connector](https://github.com/quixio/quix-samples/tree/main/python/destinations/elasticsearch) 
demonstrates how to consume data from a Kafka topic in Quix and write the data to a 
Elasticsearch using the [Quix Streams Elasticsearch sink](https://quix.io/docs/quix-streams/connectors/sinks/mongodb-sink.html).

## How to run

Create a [Quix](https://portal.platform.quix.io/signup?xlink=github) account or log-in and visit the `Connectors` tab to use this connector.

Clicking `Set up connector` allows you to enter your connection details and runtime parameters.

Then either: 
* click `Test connection & deploy` to deploy the pre-built and configured container into Quix. 

* or click `Customise connector` to inspect or alter the code before deployment.

## Environment Variables

The connector uses the following environment variables (which correspond to the 
`ElasticsearchSink` parameter names):

### Required
- `input`: The input Kafka topic name
- `ELASTICSEARCH_URL`: Elasticsearch url
- `ELASTICSEARCH_INDEX`: Elasticsearch index name
- `ELASTICSEARCH_AUTHENTICATION_JSON`: A json-serializable object with [Elasticsearch connection arguments](https://www.elastic.co/guide/en/elasticsearch/client/python-api/current/connecting.html)
  like `api_key`, `cloud_id`, etc...  
    **Example**: '{"api_key": "mykey-abc123"}'

### Optional
Unless explicitly defined, these are set to the [`ElasticsearchSink` defaults](https://quix.io/docs/quix-streams/connectors/sinks/elasticsearch-sink.html#configuration-options).
- `ELASTICSEARCH_MAPPING`: a custom mapping  
    **Default**: Dynamically maps all field types
- `ELASTICSEARCH_BATCH_SIZE`: how large each chunk size is with bulk  
    **Default**: 500
- `ELASTICSEARCH_MAX_BULK_RETRIES`: number of retry attempts for each bulk batch  
    **Default**: 3
- `ELASTICSEARCH_ADD_MESSAGE_METADATA`: Boolean to include key, timestamp, and headers as `__{field}`    
    **Default**: "false"
- `ELASTICSEARCH_ADD_TOPIC_METADATA`: Boolean to include topic, partition, and offset as `__{field}`    
    **Default**: "false"


## Requirements / Prerequisites

You will need to have an Elasticsearch instance with access to create and/or write to an Index.

## Contribute

Submit forked projects to the Quix [GitHub](https://github.com/quixio/quix-samples) repo. Any new project that we accept will be attributed to you and you'll receive $200 in Quix credit.

## Open Source

This project is open source under the Apache 2.0 license and available in our [GitHub](https://github.com/quixio/quix-samples) repo. Please star us and mention us on social to show your appreciation.
