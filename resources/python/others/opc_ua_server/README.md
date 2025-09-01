# OPC UA Server

[This code](https://github.com/quixio/quix-samples/tree/main/python/others/opc_ua_server) is a demo OPC UA server designed to help you start integrating your on site OPC UA servers with Quix.

## How to run

Create a [Quix](https://portal.platform.quix.io/signup?xlink=github) account or log-in and visit the `Templates` tab to use this connector.

Clicking `Deploy` allows you to deploy the server to your Quix instance.
Clicking `Preview code` allows you to view or save the code to the repo that backs your Quix cloud instance.

## Usage and Config

Upon deployment the following YAML will be added to your environments YAML file:

```
  - name: Demo OPC UA Server
    application: OPCServer
    version: latest
    deploymentType: Service
    resources:
      cpu: 200
      memory: 500
      replicas: 1
    network:
      serviceName: intopcserver
      ports:
        - port: 4840
          targetPort: 4840
```

The server does not require any configuration.
However, you should note that when deployed within Quix, the following YAML settings are worth knowing about.

 * network - These network setting will allow the server to be accessed on the specified port *within* the Quix server. They do not enable access from the internet.
 * service name and port - these will be used by the client to access the server, again, within the Quix backend network.

## Contribute

Submit forked projects to the Quix [GitHub](https://github.com/quixio/quix-samples) repo. Any new project that we accept will be attributed to you and you'll receive $200 in Quix credit.

## Open source

This project is open source under the Apache 2.0 license and available in our [GitHub](https://github.com/quixio/quix-samples) repo.

Please star us and mention us on social to show your appreciation.
