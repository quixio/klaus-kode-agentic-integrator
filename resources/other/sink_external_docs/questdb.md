# Connecting to QuestDB with a Token

If your QuestDB instance requires a **token for authentication**, the standard—and most robust—way in Python is to use the official QuestDB Python client (the `questdb` package) and pass the token via a configuration string (or environment variable). Here's how to do it and run a query.

---

## 1. Install the Python Client

```bash
python3 -m pip install -U questdb[dataframe]
```

This installs version 3.0.0 of the official client, with optional dependencies for handling DataFrames like pandas and numpy ([py-questdb-client.readthedocs.io][1]).

---

## 2. Connecting with a Bearer Token via ILP/HTTP

You can authenticate using an HTTP Bearer Token in the configuration string:

```python
from questdb.ingress import Sender, TimestampNanos

# Example configuration string with token
conf = "http::addr=localhost:9000;token=YOUR_BEARER_TOKEN;"

with Sender.from_conf(conf) as sender:
    # Insert a row
    sender.row(
        'trades',
        symbols={'symbol': 'AAPL', 'side': 'buy'},
        columns={'price': 172.50, 'amount': 10},
        at=TimestampNanos.now()
    )
    sender.flush()
```

Or, if you prefer keeping secrets out of your code, set the token via environment variable:

```bash
export QDB_CLIENT_CONF="http::addr=localhost:9000;token=YOUR_BEARER_TOKEN;"
```

Then in Python:

```python
from questdb.ingress import Sender, TimestampNanos

with Sender.from_env() as sender:
    sender.row(
        'trades',
        symbols={'symbol': 'GOOG', 'side': 'sell'},
        columns={'price': 2850.75, 'amount': 5},
        at=TimestampNanos.now()
    )
    sender.flush()
```

This approach leverages ILP over HTTP with token-based authentication—fully supported in Enterprise mode ([QuestDB][2], [py-questdb-client.readthedocs.io][1], [GitHub][3]).

---

## 3. Alternative: REST API + Token (for SELECT Queries)

If you’d rather run SQL queries (e.g. `SELECT`) using QuestDB's REST API, you can use the Python `requests` library:

```python
import requests

url = "http://localhost:9000/exec"
headers = {"Authorization": "Bearer YOUR_REST_API_TOKEN"}
params = {"query": "SELECT * FROM trades LIMIT 10;"}

response = requests.get(url, headers=headers, params=params)
response.raise_for_status()

print(response.json())
```

This mirrors how you’d make a `curl` request with a `Bearer` token—just translated into Python ([QuestDB][4]).

---

## 4. Summary Table

| Scenario                 | Method                      | Configuration Example                        | Use Case                       |
| ------------------------ | --------------------------- | -------------------------------------------- | ------------------------------ |
| Insert data with token   | `questdb` client (ILP/HTTP) | `conf = "http::addr=...;token=...;"`         | High-frequency data ingestion  |
| Execute SQL queries      | REST API with `requests`    | `headers = {"Authorization": "Bearer ..."} ` | SELECT, exports, query results |
| Environment-based config | `QDB_CLIENT_CONF` env var   | Set token in env, use `Sender.from_env()`    | Secrets management / CI/CD     |

---

### Notes on Token-Based Authentication

* **ILP Token (for ingestion)**: In Enterprise mode, you can pass a token (HTTP Bearer) via the config string or env variable, for insertion. Authentication via token is not supported in Open Source QuestDB via ILP—only basic auth is ([QuestDB][2]).
* **REST API Token (for querying)**: You can send SQL via the REST API with token-based auth. In the Open Source edition, you’d still need to configure users and passwords or enable token-based auth via server config ([QuestDB][4]).

---

# Connecting to QuestDB with a Token using env vars

Here’s how you can securely connect to a QuestDB instance in Python using environment variables for configuration, including host, port, token, and other credentials.

---

## 1. Configuring the QuestDB Python Client via Environment Variables

The official QuestDB Python client (`questdb.ingress.Sender`) supports loading your connection configuration entirely from the `QDB_CLIENT_CONF` environment variable—so you avoid hardcoding sensitive data like tokens or passwords in your code ([py-questdb-client.readthedocs.io][1]).

### Example Setup (Shell / `.env`)

```bash
export QDB_CLIENT_CONF="http::addr=myhost.example.com:9000;token=MY_BEARER_TOKEN;tls_verify=on;"
```

This string can include any valid configuration key—like `username`, `password`, `token`, or TLS flags—each separated by semicolons. The `addr=host:port` is mandatory ([py-questdb-client.readthedocs.io][1]).

### Example in Python

```python
from questdb.ingress import Sender, TimestampNanos
import os

# Ensure the env var is set beforehand
conf_str = os.getenv("QDB_CLIENT_CONF")
if not conf_str:
    raise EnvironmentError("Environment variable QDB_CLIENT_CONF is not set")

with Sender.from_env() as sender:
    # Example insertion
    sender.row(
        'trades',
        symbols={'symbol': 'AAPL', 'side': 'buy'},
        columns={'price': 150.25, 'amount': 10},
        at=TimestampNanos.now()
    )
    sender.flush()
```

In this setup, all connection details—including host, token, and TLS options—are managed outside your code, enhancing security and flexibility.

---

## 2. Programmatic Construction (Optional)

If you prefer building the configuration in code (instead of the environment variable), you can still pull the details from environment variables:

```python
import os
from questdb.ingress import Sender, Protocol, TimestampNanos

host = os.getenv("QDB_HOST", "localhost")
port = os.getenv("QDB_PORT", "9000")
token = os.getenv("QDB_TOKEN")

conf = f"http::addr={host}:{port};"
if token:
    conf += f"token={token};"

with Sender.from_conf(conf) as sender:
    sender.row(
        'trades',
        symbols={'symbol': 'GOOG', 'side': 'sell'},
        columns={'price': 2850.75, 'amount': 5},
        at=TimestampNanos.now()
    )
    sender.flush()
```

This approach lets you manage configuration dynamically—adjusting for different environments or deployment scenarios—without direct exposure of secrets in your codebase.

---

## Summary Table

| Approach                       | Configuration Source                | Benefits                              |
| ------------------------------ | ----------------------------------- | ------------------------------------- |
| **Env var: QDB\_CLIENT\_CONF** | `"http::addr=…;token=…;…"` string   | Clean, secure, environment-managed.   |
| **Env vars + programmatic**    | `QDB_HOST`, `QDB_PORT`, `QDB_TOKEN` | Flexible, dynamic, still secret-safe. |

---

## Key Tips

* Always ensure the environment variable `QDB_CLIENT_CONF` is set **before** running your Python application.
* Use `token=` for Bearer-token authentication when using HTTP transport.
* You can also configure TLS options (`tls_verify`, CA roots, etc.) in the same config string ([py-questdb-client.readthedocs.io][1], [QuestDB][2], [GitHub][3], [QuestDB][4]).
* If you’re using TCP/ILP instead of HTTP, you can still pass tokens and credentials via the same `QDB_CLIENT_CONF`.

---


