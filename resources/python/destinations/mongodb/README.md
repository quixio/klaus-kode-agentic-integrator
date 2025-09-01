# MongoDB

[This connector](https://github.com/quixio/quix-samples/tree/main/python/destinations/mongodb) 
demonstrates how to consume data from a Kafka topic in Quix and write the data to a 
MongoDB database using the [Quix Streams MongoDB sink](https://quix.io/docs/quix-streams/connectors/sinks/mongodb-sink.html).

## Using with a Quix Cloud MongoDB Service

This deployment will work seamlessly with a [Quix Cloud MongoDB service](https://github.com/quixio/quix-samples/tree/main/docker/mongodb).

Simply provide the following arguments to this connector, 
where `username` and `password` are are the credentials used when 
creating the **Quix Cloud MongoDB service**: 

```shell
MONGODB_USERNAME="<YOUR USERNAME>"  # (default: "admin")
MONGODB_PASSWORD="<YOUR PASSWORD>"
MONGODB_HOST="mongodb"
MONGODB_PORT="27017"
```
## How to run

Create a [Quix](https://portal.platform.quix.io/signup?xlink=github) account or log-in and visit the `Connectors` tab to use this connector.

Clicking `Set up connector` allows you to enter your connection details and runtime parameters.

Then either: 
* click `Test connection & deploy` to deploy the pre-built and configured container into Quix. 

* or click `Customise connector` to inspect or alter the code before deployment.

## Environment Variables

The connector uses the following environment variables (which correspond to the 
`MongoDBSink` parameter names):

### Required
- `input`: The input Kafka topic name
- `MONGODB_URL`: MongoDB url; most commonly `mongodb://username:password@host:port`
- `MONGODB_DB`: MongoDB database name
- `MONGODB_COLLECTION`: MongoDB collection name

### Optional
Unless explicitly defined, these are set to the [`MongoDBSink` defaults](https://quix.io/docs/quix-streams/connectors/sinks/mongodb-sink.html#configuration-options).

- `MONGODB_DOCUMENT_MATCHER`: How documents are selected to update.    
    Accepts a JSON-serializable string formatted as a MongoDB filter Query.    
    Can handle kafka message refs using `__{ref}` with dot notation for nested fields.  
    ex: `'{"_id": "__key", "first_name": "__value.name.first"}'`    
    Possible refs: key, value, headers, timestamp, topic, partition, offset.    
    **Default**: '{"_id": "__key"}'.
- `MONGODB_UPSERT`: Boolean to create documents if no matches with `MONGODB_DOCUMENT_MATCHER`.    
    **Default**: "true"
- `MONGODB_UPDATE_METHOD`: How documents found with `MONGODB_DOCUMENT_MATCHER` are updated.    
    'Update*' options will only update fields included in the kafka message.    
    'Replace*' option fully replaces the document with the contents of kafka message.    
    - "UpdateOne": Updates the first matching document (usually based on `_id`).    
    - "UpdateMany": Updates ALL matching documents (usually NOT based on `_id`).    
    - "ReplaceOne": Replaces the first matching document (usually based on `_id`).    
    **Default**: "UpdateOne".
- `MONGODB_ADD_MESSAGE_METADATA`: Boolean to include key, timestamp, and headers as `__{field}`    
    **Default**: "false"
- `MONGODB_ADD_TOPIC_METADATA`: Boolean to include topic, partition, and offset as `__{field}`    
    **Default**: "false"


## Requirements / Prerequisites

You will need to have a MongoDB instance with access to a db and collection.

## Contribute

Submit forked projects to the Quix [GitHub](https://github.com/quixio/quix-samples) repo. Any new project that we accept will be attributed to you and you'll receive $200 in Quix credit.

## Open Source

This project is open source under the Apache 2.0 license and available in our [GitHub](https://github.com/quixio/quix-samples) repo. Please star us and mention us on social to show your appreciation.
