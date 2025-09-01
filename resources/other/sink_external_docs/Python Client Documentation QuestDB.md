QuestDB supports the Python ecosystem.

The QuestDB Python client provides ingestion high performance and is insert only.

The client, in combination with QuestDB, offers peak performance time-series ingestion and analysis.

Apart from blazing fast ingestion, our clients provide these key benefits:

-   **Automatic table creation**: No need to define your schema upfront.
-   **Concurrent schema changes**: Seamlessly handle multiple data streams with on-the-fly schema modifications
-   **Optimized batching**: Use strong defaults or curate the size of your batches
-   **Health checks and feedback**: Ensure your system's integrity with built-in health monitoring
-   **Automatic write retries**: Reuse connections and retry after interruptions

This quick start will help you get started.

It covers basic connection, authentication and some insert patterns.

![Python](https://questdb.com/docs/images/logos/python.svg)

## Requirements[](https://questdb.com/docs/clients/ingest-python/#requirements "Direct link to Requirements")

Requires Python >= 3.8 Assumes QuestDB is running. Not running? See the [general quick start](https://questdb.com/docs/quick-start/).

## Client installation[](https://questdb.com/docs/clients/ingest-python/#client-installation "Direct link to Client installation")

To install the client (or update it) globally:

```
python3 -m pip install -U questdb
```

Or, from from within a virtual environment:

If you’re using poetry, you can add questdb as a dependency:

Or to update the dependency:

Using dataframes?

Add following dependencies:

-   `pandas`
-   `pyarrow`
-   `numpy`

## Authentication[](https://questdb.com/docs/clients/ingest-python/#authentication "Direct link to Authentication")

Passing in a configuration string with basic auth:

```javascript
from questdb.ingress import Senderconf = "http::addr=localhost:9000;username=admin;password=quest;"with Sender.from_conf(conf) as sender:    ...
```

Passing via the `QDB_CLIENT_CONF` env var:

```bash
export QDB_CLIENT_CONF="http::addr=localhost:9000;username=admin;password=quest;"
```

```javascript
from questdb.ingress import Senderwith Sender.from_env() as sender:    ...
```

```javascript
from questdb.ingress import Sender, Protocolwith Sender(Protocol.Http, 'localhost', 9000, username='admin', password='quest') as sender:
```

When using QuestDB Enterprise, authentication can also be done via REST token. Please check the [RBAC docs](https://questdb.com/docs/operations/rbac/#authentication) for more info.

## Basic insert[](https://questdb.com/docs/clients/ingest-python/#basic-insert "Direct link to Basic insert")

Basic insertion (no-auth):

```javascript
from questdb.ingress import Sender, TimestampNanosconf = f'http::addr=localhost:9000;'with Sender.from_conf(conf) as sender:    sender.row(        'trades',        symbols={'symbol': 'ETH-USD', 'side': 'sell'},        columns={'price': 2615.54, 'amount': 0.00044},        at=TimestampNanos.now())    sender.row(        'trades',        symbols={'symbol': 'BTC-USD', 'side': 'sell'},        columns={'price': 39269.98, 'amount': 0.001},        at=TimestampNanos.now())    sender.flush()
```

In this case, the designated timestamp will be the one at execution time. Let's see now an example with timestamps, custom auto-flushing, basic auth, and error reporting.

```python
from questdb.ingress import Sender, IngressError, TimestampNanosimport sysimport datetimedef example():    try:        conf = (            'http::addr=localhost:9000;'            'username=admin;password=quest;'            'auto_flush_rows=100;auto_flush_interval=1000;')        with Sender.from_conf(conf) as sender:            # Record with provided designated timestamp (using the 'at' param)            # Notice the designated timestamp is expected in Nanoseconds,            # but timestamps in other columns are expected in Microseconds.            # You can use the TimestampNanos or TimestampMicros classes,            # or you can just pass a datetime object            sender.row(                'trades',                symbols={                    'symbol': 'ETH-USD',                    'side': 'sell'},                columns={                    'price': 2615.54,                    'amount': 0.00044},                at=datetime.datetime(                    2022, 3, 8, 18, 53, 57, 609765,                    tzinfo=datetime.timezone.utc))            # You can call `sender.row` multiple times inside the same `with`            # block. The client will buffer the rows and send them in batches.            # You can flush manually at any point.            sender.flush()            # If you don't flush manually, the client will flush automatically            # when a row is added and either:            #   * The buffer contains 75000 rows (if HTTP) or 600 rows (if TCP)            #   * The last flush was more than 1000ms ago.            # Auto-flushing can be customized via the `auto_flush_..` params.        # Any remaining pending rows will be sent when the `with` block ends.    except IngressError as e:        sys.stderr.write(f'Got error: {e}\n')if __name__ == '__main__':    example()
```

We recommended `User`\-assigned timestamps when ingesting data into QuestDB. Using `Server`\-assigned timestamps hinders the ability to deduplicate rows which is [important for exactly-once processing](https://questdb.com/docs/reference/api/ilp/overview/#exactly-once-delivery-vs-at-least-once-delivery).

The same `trades` insert, but via a Pandas dataframe:

```javascript
import pandas as pdfrom questdb.ingress import Senderdf = pd.DataFrame({    'symbol': pd.Categorical(['ETH-USD', 'BTC-USD']),    'side': pd.Categorical(['sell', 'sell']),    'price': [2615.54, 39269.98],    'amount': [0.00044, 0.001],    'timestamp': pd.to_datetime(['2022-03-08T18:03:57.609765Z', '2022-03-08T18:03:57.710419Z'])})conf = f'http::addr=localhost:9000;'with Sender.from_conf(conf) as sender:    sender.dataframe(df, table_name='trades', at=TimestampNanos.now())
```

Note that you can also add a column of your dataframe with your timestamps and reference that column in the `at` parameter:

```javascript
import pandas as pdfrom questdb.ingress import Senderdf = pd.DataFrame({    'symbol': pd.Categorical(['ETH-USD', 'BTC-USD']),    'side': pd.Categorical(['sell', 'sell']),    'price': [2615.54, 39269.98],    'amount': [0.00044, 0.001],    'timestamp': pd.to_datetime(['2022-03-08T18:03:57.609765Z', '2022-03-08T18:03:57.710419Z'])})conf = f'http::addr=localhost:9000;'with Sender.from_conf(conf) as sender:    sender.dataframe(df, table_name='trades', at='timestamp')
```

## Insert numpy.ndarray[](https://questdb.com/docs/clients/ingest-python/#insert-numpyndarray "Direct link to Insert numpy.ndarray")

NumPy arrays of `dtype=numpy.float64` may be inserted either row-by-row or as objects inside a dataframe.

note

Arrays are supported from QuestDB version 9.0.0, and require updated client libraries.

note

Other types such as `list`, `array.array`, `torch.Tensor` and other objects aren't supported directly and must first be converted to NumPy arrays.

In the two examples below, we insert some FX order book data.

-   `bids` and `asks`: 2D arrays of L2 order book depth. Each level contains price and volume.
-   `bids_exec_probs` and `asks_exec_probs`: 1D arrays of calculated execution probabilities for the next minute.

### Direct Array Insertion[](https://questdb.com/docs/clients/ingest-python/#direct-array-insertion "Direct link to Direct Array Insertion")

```javascript
from questdb.ingress import Sender, TimestampNanosimport numpy as npconf = f'http::addr=localhost:9000;'with Sender.from_conf(conf) as sender:    sender.row(        'fx_order_book',        symbols={            'symbol': 'EUR/USD'        },        columns={            'bids': np.array(                [                    [1.0850, 600000],                    [1.0849, 300000],                    [1.0848, 150000]                ],                dtype=np.float64            ),            'asks': np.array(                [                    [1.0853, 500000],                    [1.0854, 250000],                    [1.0855, 125000]                ],                dtype=np.float64            )        },        at=TimestampNanos.now())    sender.flush()
```

### DataFrame Insertion[](https://questdb.com/docs/clients/ingest-python/#dataframe-insertion "Direct link to DataFrame Insertion")

```go
import pandas as pdfrom questdb.ingress import Senderimport numpy as npdf = pd.DataFrame({    'symbol': [        'EUR/USD',        'GBP/USD'    ]    'bids': [        np.array(            [                [1.0850, 600000],                [1.0849, 300000],                [1.0848, 150000]            ],            dtype=np.float64        ),        np.array(            [                [1.3200, 550000],                [1.3198, 275000],                [1.3196, 130000]            ],            dtype=np.float64        )    ],    'asks': [        np.array(            [                [1.0853, 500000],                [1.0854, 250000],                [1.0855, 125000]            ],            dtype=np.float64        ),        np.array(            [                [1.3203, 480000],                [1.3205, 240000],                [1.3207, 120000]            ],            dtype=np.float64        )    ],    'timestamp': pd.to_datetime([        '2022-03-08T18:03:57.609765Z',        '2022-03-08T18:03:57.710419Z'    ])})# or 'tcp::addr=localhost:9009;protocol_version=2;'conf = 'http::addr=localhost:9000;'with Sender.from_conf(conf) as sender:    sender.dataframe(        df,        table_name='fx_order_book',        at='timestamp')
```

note

The example above uses ILP/HTTP. If instead you're using ILP/TCP you'll need to explicity opt into the newer protocol version 2 that supports sending arrays.

```cpp
tcp::addr=127.0.0.1:9009;protocol_version=2;
```

Protocol Version 2 along with its support for arrays is available from QuestDB version 9.0.0.

## Configuration options[](https://questdb.com/docs/clients/ingest-python/#configuration-options "Direct link to Configuration options")

The minimal configuration string needs to have the protocol, host, and port, as in:

```cpp
http::addr=localhost:9000;
```

In the Python client, you can set the configuration options via the standard config string, which is the same across all clients, or using [the built-in API](https://py-questdb-client.readthedocs.io/en/latest/sender.html#sender-programmatic-construction).

For all the extra options you can use, please check [the client docs](https://py-questdb-client.readthedocs.io/en/latest/conf.html#sender-conf)

Alternatively, for a breakdown of Configuration string options available across all clients, see the [Configuration string](https://questdb.com/docs/configuration-string/) page.

## Transactional flush[](https://questdb.com/docs/clients/ingest-python/#transactional-flush "Direct link to Transactional flush")

As described at the [ILP overview](https://questdb.com/docs/reference/api/ilp/overview/#http-transaction-semantics), the HTTP transport has some support for transactions.

The python client exposes [an API](https://py-questdb-client.readthedocs.io/en/latest/sender.html#http-transactions) to make working with transactions more convenient

## Next steps[](https://questdb.com/docs/clients/ingest-python/#next-steps "Direct link to Next steps")

Please refer to the [ILP overview](https://questdb.com/docs/reference/api/ilp/overview/) for general details about transactions, error control, delivery guarantees, health check, or table and column auto-creation. The [Python client docs](https://py-questdb-client.readthedocs.io/en/latest/sender.html) explain how to apply those concepts using the built-in API.

For full docs, checkout [ReadTheDocs](https://py-questdb-client.readthedocs.io/en).

With data flowing into QuestDB, now it's time to for analysis.

To learn _The Way_ of QuestDB SQL, see the [Query & SQL Overview](https://questdb.com/docs/reference/sql/overview/).

Alone? Stuck? Want help? Visit us in our [Community Forum](https://community.questdb.com/).

## Additional resources[](https://questdb.com/docs/clients/ingest-python/#additional-resources "Direct link to Additional resources")

-   [QuestDB Python clients guide](https://questdb.com/docs/pgwire/python/)
-   [Integration with Polars](https://questdb.com/docs/third-party-tools/polars/)
-   [Integration with Pandas](https://questdb.com/docs/third-party-tools/pandas/)