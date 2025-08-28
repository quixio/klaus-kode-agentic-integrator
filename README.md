# **Getting Started with Klaus Kode — the Agentic Data Integrator** 

 Klaus Kode is a Python-based Agentic Data Integrator that helps you [vibe code](https://en.wikipedia.org/wiki/Vibe_coding) your data integrations so you can connect to more systems, faster. You run it in your terminal as a workflow wizard. It uses AI agents to generate connector code, run and test that code, analyze logs, as well as managing dependencies and environment variables. It uses the [Quix Cloud](https://quix.io/quix-cloud) platform as a sandbox for running code in isolated containers and storing data. 

Note that Klaus Kode is designed to help build pipelines that need *high throughput*. If you’re dealing with a very small number of events such as emails and chat messages for a handful of users, you might be better off with [make.com](http://make.com) or [n8n.io](https://n8n.io/). Klaus Kode is best suited for scenarios where you need to integrate high-fidelity data sources — from continuous telemetry streams and blockchain transaction feeds to large static datasets that need to be ingested and processed in a distributed manner.

## **Prerequisites**# **Getting Started with Klaus Kode — the Agentic Data Integrator** 

 Klaus Kode is a Python-based Agentic Data Integrator that helps you [vibe code](https://en.wikipedia.org/wiki/Vibe_coding) your data integrations so you can connect to more systems, faster. You run it in your terminal as a workflow wizard. It uses AI agents to generate connector code, run and test that code, analyze logs, as well as managing dependencies and environment variables. It uses the [Quix Cloud](https://quix.io/quix-cloud) platform as a sandbox for running code in isolated containers and storing data. 

Note that Klaus Kode is designed to help build pipelines that need *high throughput*. If you’re dealing with a very small number of events such as emails and chat messages for a handful of users, you might be better off with [make.com](http://make.com) or [n8n.io](https://n8n.io/). Klaus Kode is best suited for scenarios where you need to integrate high-fidelity data sources — from continuous telemetry streams and blockchain transaction feeds to large static datasets that need to be ingested and processed in a distributed manner.

## **Prerequisites**

You’ll need a few things already in place before you can start with Klaus Kode. 

These include:

1. Python and Git installed on your system  
2. The Claude Code CLI  
3. A Quix project and PAT token   
4. API tokens and billing enabled for OpenAI GPT APIs and Anthropic Claude APIs   
   *\* If you are a Quix customer and early beta tester you might be able to get these keys from the Quix team*

Klaus Kode has been tested on Ubuntu (via WIndows WSL), and Mac OS. It should work on Windows too but has not been tested on Windows yet.

### **Notes on Installing the Claude Code CLI** 

Klaus Kode leverages the Claude Code SDK under the hood, which in turn uses the Claude Code CLI. If you don't have an Anthropic account yet, [sign up](https://claude.ai/login) first.

According to the [Anthropics official instructions](https://docs.anthropic.com/en/docs/claude-code/setup), you install Claude Code like this:

```shell
npm install -g @anthropic-ai/claude-code
```

However, many of our test users seem to encounter permissions errors with the previous method. 

The following install commands seem to be more reliable:

```shell
(Linux/Mac)            curl -fsSL https://claude.ai/install.sh | bash

(Windows Powershell)   irm https://claude.ai/install.ps1 | iex
```

### **Tokens and API Keys**

Klaus Kode uses OpenAI GPT4o for log file analysis and Anthropic’s Claude Sonnet 4 (via Claude Code). Therefore you need accounts with both services with billing enabled. Quix Cloud is used for deployments and sandbox testing. 

In summary, you need the following keys and tokens: 

1. An [Anthropic API key](https://docs.anthropic.com/en/api/overview) API key — requires an Anthopic account with billing enabled and enough credit to run Claude Code. 

2. An [OpenAI API key](https://platform.openai.com/docs/libraries) API key — if you have verified your organization already, it is cheaper to switch to GPT5-mini. You can do this 

3. A [Quix Cloud PAT token](https://quix.io/docs/develop/authentication/personal-access-token.html) — you can [sign up for free](https://portal.cloud.quix.io/signup?utm_campaign=klaus-kode) to get one (this lets Klaus Kode run the code in a cloud sandbox)  
     
   You should then configure your environment variables with these keys as described in the following section

## **Klaus Kode Setup**

To use Klaus Kode, clone the repo, create and activate a virtual environment, install the dependencies and run the startup script.

Here are those steps in detail:

1) Clone the Klaus Kode repo   
   

```shell
$ git clone https://github.com/quixio/quix-coding-agent.git
```

   

2) Set up a virtual environment and activate it (assuming Linux/Mac)  
   

```shell
$ python -m venv venv
$ source venv/bin/activate
```

   

3) Install the Klaus Kode dependencies.  
   

```shell
(venv)$ pip install -r requirements.txt
```

   

4) Create a .env file (make a copy of the.env example) and enter your API keys and PAT token  
   

```py
OPENAI_API_KEY=<your-openai-api-key> # "sk-proj..."
ANTHROPIC_API_KEY=<your-anthropic-api-key> # "sk-ant-api..."
QUIX_TOKEN=<your-quix-token> # "pat-..." 
QUIX_BASE_URL=https://portal-api.cloud.quix.io/

## OPTIONAL: If Klaus cannot autonmatically detect your Claude Code installation
CLAUDE_CLI_PATH=/home/username/.claude/local/node_modules/.bin
```

   

   

5) Run Klaus Kode  
   

```shell
(venv)$ python main.py
```

 


## **Klaus Kode Data Integration Workflow**

When you start Klaus Kode you’ll see the following options:

```

Select Workflow Type
--------------------
  ▶ 1. Source Workflow (Bring data in from another system)
    2. Sink Workflow (Write data out into an external system)
    3. Transform Workflow (Process data in flight) *Coming soon
    4. Debug Workflow (Diagnose and fix existing sandbox code) *Coming soon

```

Hopefully, the wording is straightforward enough to help you choose the right option.

 To understand the workflow better, let's look at an example scenario and break down how you would implement it in Klaus Kode. 

Suppose that I want to do some kind of research on Wikipedia page edits that happen in the coming week. In technical terms,  I want to listen to the Wikipedia Change Event Stream and sink the data to a Clickhouse database so that I can query it offline.

Here’s an outline of how it would work in Klaus Kode:

* First, you start Klaus Kode and choose the “**Source Workflow**” option (since we’re sourcing data from an external data stream)  
    
  * Klaus Kode will help you create a sandbox app for you to get started and will guide you through the process of creating Python code to get data out of the Wikipedia change event stream. This data is written to a “topic”  (a topic is essentially just a giant log file—a place to put the data we get from Wikipedia).

* Once that’s done,  you loop back to the start of the wizard and choose the “**Sink Workflow**”.

  * Klaus Kode will help you create another sandbox app and will guide you through the process of creating Python code to read from the topic you created in the source workflow, and sink that data into a Clickhouse database (with proper backpressure, batching and other dark magic)

This is a very simple example scenario, and we’re purposely not doing much to the data while it’s in flight (such as aggregating or analyzing it). The purpose of this early prototype is to simply show you how you can use AI to get high volumes of data in and out of any system. 

### **Source Workflow**

When following the sink workflow, you’ll be guided through the following phases:

[1—SOURCE SETUP](#1—source-setup-phase)

[2—KNOWLEDGE GATHERING](#2—knowledge-gathering-phase)

[3—CODE GENERATION](#3—code-generation-phase)

[4—CONNECTION CODE TESTING](#4—connection-code-testing-phase)

[5—FIRST DEBUG PHASE (IF CONNECTION CODE FAILS)](#5—first-debug-phase-\(if-connection-code-fails\))

[6—SCHEMA ANALYSIS](#6—schema-analysis-phase)

[5—PRODUCER CODE CREATION](#5—producer-code-creation-phase)

[6—PRODUCER CODE TESTING](#6—producer-code-testing-phase)

[7—SECOND DEBUG PHASE (IF CODE FAILS)](#7—second-debug-phase-\(if-producer-code-fails\))

[8—DEPLOYMENT](#8—deployment-phase)

---

#### 1—SOURCE SETUP PHASE {#1—source-setup-phase}

Klaus Kode will ask you for some details that are specific to the Quix Cloud environment (it detects these based on your PAT token). This where code is run and data is stored.

* Choose an **app name** for the sandbox app. Lets just call it “*wikipedia-source*”  
* Select a **Project**: Just choose the default “MyProject”  
* Select a **Topic**: Just choose the default “input-data” (a topic is essentially just a giant log file, a place to put the data we get from Wikipedia)

---

#### 2—KNOWLEDGE GATHERING PHASE {#2—knowledge-gathering-phase}

Next, Klaus Kode will ask you what you want to do, i.e. what kind of data you want to get from the source. The purpose of this phase is to create code that will connect to the source and read some sample data from it, and analyse the shape of the data. We will not write anything to a Kafka topic yet.

* **Enter Requirements**: Lets just say “*I want to read basic page edit metadata from the Wikipedia Change Event Stream”*   
  (you can of course be much more precise about the fields you want to get)

#### 3—CODE GENERATION PHASE {#3—code-generation-phase}

* **Generate Code:** Klaus Kode will invoke the mighty Claude Code CLI which will get to work drafting some code that reads from data from the Wikipedia EventStreams HTTP Service  
    
  In this step, you can switch to something else  and keep an eye on Claude while it works. The o might take a few minutes as Claude examples the existing documentation and the sample files in the “resources” directory.   
    
  * **Note about knowledge**: Klaus Kode comes with a knowledge folder where you can put documentation about any system that you want to connect to. Claude Code is configured to search the web but if you want to read from a proprietary system there probably wont be any documentation online. That’s the idea behind the knowledge folder. 

  * To accompany this tutorial, we’ve placed markdown version of the Wikipedia event stream documentation in the knowledge folder at the following location:  
    *  /resources/other/source\_external\_docs/Wikipedia Changes Event Stream HTTP Service \- Wikitech.md  
  * This helps Claude get the knowledge it needs without resorting to a web search straight away (which can slow things down).


* **Review Code:** When Claude is finished, Klaus prompts you to look at the generated code to make sure it’s OK — for now, let's just be lazy and place all our trust in Claude's ability to get it right — tap “**Y**”.

* **Collect Variables:** Claude is instructed to use environment variables in the code, but of course doesn't know what the values should be. Thus Klaus Kode will guide you though a questionnaire to configure values for the variables that Claude has decided will be necessary.

  * Luckily for us, the Wikipedia EventStreams Service doesn’t need an API key, so the only variable you’ll probably need to set the **output topic**. Claude will have proposed a default which may or may not match the one you selected in the previous step. You can choose another topic or accept the one that Claude proposed as a default either option is fine. 

---

#### 4—CONNECTION CODE TESTING PHASE {#4—connection-code-testing-phase}

In this phase, Klause Kode, will upload the file to the app sandbox in Quix Cloud, set the environment variables, install the dependencies and run the code.

Klaus Kode will then retrieve the output logs from the sandbox and examine the logs to determine if the run was successful or not. As mentioned before, the purpose is to get some sample data to try and infer the schema of the data.

Here’s an example of what what an event looks like when Klaus Kode successfully reads from the Wikipedia event stream

```
[23:20:59] Raw event received: <class 'dict'> with keys: ['$schema', 'meta', 'id', 'type', 'namespace', 'title', 'title_url', 'comment', 'timestamp', 'user', 'bot', 'log_id', 'log_type', 'log_action', 'log_params', 'log_action_comment', 'server_url', 'server_name', 'server_script_path', 'wiki', 'parsedcomment']
[23:20:59] Processing event #999997
  Title: File:Barbara Ronchi-66092.jpg
  User: Harald Krichel
  Wiki: commons.wikimedia.org
  Type: log
  Time: 2025-08-27T23:20:58Z
✅ Event #999997 produced successfully!

```

---

#### 5—FIRST DEBUG PHASE (IF CONNECTION CODE FAILS) {#5—first-debug-phase-(if-connection-code-fails)}

If for any reason Claude Code has created code that doesn’t work on the first try,  you’ll get some options to debug it.

```
1. Let Claude Code SDK fix the error directly
2. Provide manual feedback yourself
3. Retry with manual code fix (fix directly in IDE without regeneration)
4. Continue anyway (the error is not serious or you have fixed it in the IDE)
5. Abort the workflow
6. ⬅️ Go back to previous phase
7. 🚀 Auto-debug (keep retrying with Claude until fixed or 10 attempts)
```

If you want to have Claude fix the code, (but also manually inspect the fixed code first), press \#1. Otherwise the easiest option is to choose \#7 “Auto-debug”. 

In this case, Claude will read the log analysis, fix it, upload it, run it again. If the code still has bugs, it will repeat the same cycle if it works or the configured amount of attempts has been exceeded (by default 10).

**Note**: Be careful with auto-debug, Claude Clode can burn through API tokens by thinking copious amounts of thoughts. Currently, Claude is still not perfect at identifying incredibly basic connection issues (wrong password, port or hostname) and wont ask you to fix those on its behalf. Instead it can get very creative in trying to work around these issues. Thus, it’s a good idea to keep an eye on the auto-debug output for signs of a simple connection issue.

---

#### 6—SCHEMA ANALYSIS PHASE {#6—schema-analysis-phase}

If Klaus Kode determines that the test worked, it means that we have sample data available to analyze. Klaus Kode will then use the GPT to create some basic schema documentation that can be reused as knowledge to when creating the code for the main application (the app that actually writes the data to a Kafka topic).  

---

####  5—PRODUCER CODE CREATION PHASE {#5—producer-code-creation-phase}

In this phase, we create the main producer app that actually writes the data to a Kafka topic (later, we can then read this topic when we sink the data to Clickhouse).

* **Extra Requirements**: Klaus Kode will ask you if you have any extra requirements to add for the main app (for example maybe you only want to write certain fields to the topic and discard the rest). Lets just say “*Write all the metadata to a kafka topic”* 

* **Generate Code:** Klaus Kode will invoke the Claude Code CLI again, read the connection code that it successfully created previously and read appropriate samples to update the code with logic that will write the data to the topic (using the quixstreams python library).

---

#### 6—PRODUCER CODE TESTING PHASE {#6—producer-code-testing-phase}

Again, Klaus Kode, will upload the file to the app sandbox in Quix Cloud, set the environment variables, install the dependencies and run the code.

The purpose here is to make sure that the application is correctly writing data to the topic.

**REMINDER**: Claude (specifically Sonnet 4 \+ Claude Code CLI) can get things wrong, and often fails to get it right on the first attempt. Be prepared to go through multiple debug cycles. Since we are uploading and running the code in a cloud sandbox rather than locally, this can take a few minutes to go through each cycle (especially when Claude Code thinks a lot)

Here’s an example of what an event looks like when Klaus Kode produces data from the Wikipedia event stream to your selected topic.

```
[23:20:59] Raw event received: <class 'dict'> with keys: ['$schema', 'meta', 'id', 'type', 'namespace', 'title', 'title_url', 'comment', 'timestamp', 'user', 'bot', 'log_id', 'log_type', 'log_action', 'log_params', 'log_action_comment', 'server_url', 'server_name', 'server_script_path', 'wiki', 'parsedcomment']
[23:20:59] Processing event #999997
  Title: File:Barbara Ronchi-66092.jpg
  User: Harald Krichel
  Wiki: commons.wikimedia.org
  Type: log
  Time: 2025-08-27T23:20:58Z
✅ Event #999997 produced successfully!

```

---

#### 7—SECOND DEBUG PHASE (IF PRODUCER CODE FAILS) {#7—second-debug-phase-(if-producer-code-fails)}

Basically the same process as the first debug phase with the same options

---

#### 8—DEPLOYMENT PHASE {#8—deployment-phase}

If Klaus Kode determines that that data is being produced correctly, it will offer to deploy it for you in Quix Cloud. You can fill out the deployment details and opt to monitor the deployment logs using AI (GPT4o or 5-mini)

Klaus Kode will deploy the code in a Docker container that will run continuously (Quix Cloud uses Kubernetes under the hood to run containers). 

If you log into the Quix platform you’ll see a deployment that looks, like this:

![][image1]

You can then click the deployment title to open it and inspect the logs.

**NOTE**: It has been observed in testing that the deployments sometimes pick up an older version of the codec(only relevant if you’ve been through a couple of debug iterations). If this happens, just [redeploy your application](https://quix.io/docs/deploy/overview.html?h=redeploy#redeploying-a-service).

### **Sink Workflow**

The sink workflow isn’t much different from the Source workflow, except that we don’t need to create and test bespoke connection code to analyze the data. We can use standard service that reads from a topic using the Quix API.

Let's continue with our illustrative use case and sink the Wikipedia change events into a Clickhouse database. The chances are, you probably don’t have a Clickhouse database ready to go, but you can provision one in Quix Cloud using the utility script \`deploy\_clickhouse.py\` in the resources directory. Alternatively, you can use a service like Railway to provision an [external Clickhouse database](https://railway.com/deploy/clickhousehttps://railway.com/deploy/clickhouse). In this workflow example, we’ll assume you used the utility script to deploy a Clickhouse DB within Quix.

When following the sink workflow, you’ll be guided through the following phases:

[1—SINK SETUP](#1—sink-setup-phase)

[3—SCHEMA ANALYSIS](#3—schema-analysis-phase)

[4—SINK CODE CREATION](#4—sink-code-creation-phase)

[5—SINK CODE TESTING](#5—sink-code-testing-phase)

[6—SINK DEBUG PHASE (IF CODE FAILS)](#6—sink-debug-phase-\(if-code-fails\))

[7—DEPLOYMENT](#7—deployment-phase)

#### 1—SINK SETUP PHASE {#1—sink-setup-phase}

Now it will ask you for some details that are specific to the Quix Cloud environment (it detects these based in your PAT token)

* Select a **Project**: Just choose the default “MyProject”  
* Select a **Topic**: Just choose the default “input-data” (a topic is essential just a giant log file, a place to output the data we get from Wikipedia)

#### 3—SCHEMA ANALYSIS PHASE {#3—schema-analysis-phase}

Klaus Kode will retrieve a data sample from your selected input topic, then analyze it to infer the schema. Klaus Kode will then use the GPT to create some basic schema documentation that can be reused as knowledge when creating the code for the main application (the app that actually consumes the data from the Kafka topic).  

#### 4—SINK CODE CREATION PHASE {#4—sink-code-creation-phase}

In this phase, we create the main consumer app that actually reads the data from the Kafka topic and sinks it to the destination system. Klaus Kode will prompt you to tell it what kind of sink application you want to create.

* **Enter Requirements**: Lets just say “*I want to write all the page edit metadata from the source topic into clickhouse using clickhouse-connect”* 

  Note that we’re being prescriptive with the Python library that we want to use here (clickhouse-connect), since Claude occasionally uses a different approach that might not be suitable for the latest version of Clickhouse. You can also leave it up to Claude to choose the Python library it thinks is best. Yet, sometimes this results in longer debug cycles if there's an error on the first try (since Claude Code will eventually search the web to find out what it is supposed to use).

* **Generate Code:** Klaus Kode will invoke the Claude Code CLI again, read the connection code that it successfully created previously and read appropriate samples to update the code with logic that will write the data to the topic (using the quixstreams python library).

#### 5—SINK CODE TESTING PHASE {#5—sink-code-testing-phase}

Klaus Kode, will upload the file to the app sandbox in Quix Cloud, set the environment variables, install the dependencies and run the code.

The purpose here is to make sure that the application is correctly sinking data to Clickhouse (or whatever destination you are using)

**REMINDER**: Claude (specifically Sonnet 4 \+ Claude Code CLI) can get things wrong, and often fails to get it right on the first attempt. Be prepared to go through multiple debug cycles. Since we are uploading and running the code in a cloud sandbox rather than locally, this can take a few minutes to go through each cycle (especially when Claude Code thinks a lot)

Here’s an example of what what an event looks like when Klaus Kode successfully reads from the Wikipedia event stream

```
[23:20:59] Raw event received: <class 'dict'> with keys: ['$schema', 'meta', 'id', 'type', 'namespace', 'title', 'title_url', 'comment', 'timestamp', 'user', 'bot', 'log_id', 'log_type', 'log_action', 'log_params', 'log_action_comment', 'server_url', 'server_name', 'server_script_path', 'wiki', 'parsedcomment']
[23:20:59] Processing event #999997
  Title: File:Barbara Ronchi-66092.jpg
  User: Harald Krichel
  Wiki: commons.wikimedia.org
  Type: log
  Time: 2025-08-27T23:20:58Z
✅ Event #999997 produced successfully!

```

#### 6—SINK DEBUG PHASE (IF CODE FAILS) {#6—sink-debug-phase-(if-code-fails)}

Again, if the code that doesn’t work on the first try,  you’ll get some options to debug it.

```
1. Let Claude Code SDK fix the error directly
2. Provide manual feedback yourself
3. Retry with manual code fix (fix directly in IDE without regeneration)
4. Continue anyway (the error is not serious or you have fixed it in the IDE)
5. Abort the workflow
6. ⬅️ Go back to previous phase
7. 🚀 Auto-debug (keep retrying with Claude until fixed or 10 attempts)
```

If you want to have Claude fix the code, (but also manually inspect the fixed code first), press \#1. Otherwise the easiest option is to choose \#7 “Auto-debug”. 

In this case, Claude will read the log analysis, fix it, upload it, run it again. If the code still has bugs, it will repeat the same cycle if it works or the configured amount of attempts has been exceeded (by default 10).

**Reminder**: The usual caveat applies here too: Be careful with auto-debug, Claude Clode can burn through API tokens by thinking copious amounts of thoughts. Currently, Claude is still not perfect at identifying incredibly basic connection issues (wrong password, port or hostname) and wont ask you to fix those on its behalf. Instead it can get very creative in trying to work around these issues. Thus, it’s a good idea to keep an eye on the auto-debug output for signs of a simple connection issue.

#### 7—DEPLOYMENT PHASE {#7—deployment-phase}

If Klaus Kode determines that that data is being produced correctly, it will offer to deploy it for you in Quix Cloud. You can fill out the deployment details and opt to monitor the deployment logs using AI (GPT4o or 5-mini)

### 

## **Klaus Kode configuration**

### **Local Configuration (Optional)**

For installation-specific settings (like Claude CLI path), use a local config file that won't be committed to git:

1. **Option 1: Environment Variable** (Recommended)

```shell
export CLAUDE_CLI_PATH=/path/to/your/claude/cli/bin
```

2. **Option 2: Local Config File**

```shell
cp config/local.yaml.example config/local.yaml
# Edit config/local.yaml with your Claude CLI path
```

The system will auto-detect Claude CLI in common locations if not configured. Any detected paths are saved to `config/local.yaml` (which is gitignored) for future use.




You’ll need a few things already in place before you can start with Klaus Kode. 

These include:

1. Python and Git installed on your system  
2. The Claude Code CLI  
3. A Quix project and PAT token   
4. API tokens and billing enabled for OpenAI GPT APIs and Anthropic Claude APIs   
   *\* If you are a Quix customer and early beta tester you might be able to get these keys from the Quix team*

Klaus Kode has been tested on Ubuntu (via WIndows WSL), and Mac OS. It should work on Windows too but has not been tested on Windows yet.

### **Notes on Installing the Claude Code CLI** 

Klaus Kode leverages the Claude Code SDK under the hood, which in turn uses the Claude Code CLI. If you don't have an Anthropic account yet, [sign up](https://claude.ai/login) first.

According to the [Anthropics official instructions](https://docs.anthropic.com/en/docs/claude-code/setup), you install Claude Code like this:

```shell
npm install -g @anthropic-ai/claude-code
```

However, many of our test users seem to encounter permissions errors with the previous method. 

The following install commands seem to be more reliable:

```shell
(Linux/Mac)            curl -fsSL https://claude.ai/install.sh | bash

(Windows Powershell)   irm https://claude.ai/install.ps1 | iex
```

### **Tokens and API Keys**

Klaus Kode uses OpenAI GPT4o for log file analysis and Anthropic’s Claude Sonnet 4 (via Claude Code). Therefore you need accounts with both services with billing enabled. Quix Cloud is used for deployments and sandbox testing. 

In summary, you need the following keys and tokens: 

1. An [Anthropic API key](https://docs.anthropic.com/en/api/overview) API key — requires an Anthopic account with billing enabled and enough credit to run Claude Code. 

2. An [OpenAI API key](https://platform.openai.com/docs/libraries) API key — if you have verified your organization already, it is cheaper to switch to GPT5-mini. You can do this 

3. A [Quix Cloud PAT token](https://quix.io/docs/develop/authentication/personal-access-token.html) — you can [sign up for free](https://portal.cloud.quix.io/signup?utm_campaign=klaus-kode) to get one (this lets Klaus Kode run the code in a cloud sandbox)  
     
   You should then configure your environment variables with these keys as described in the following section

## **Klaus Kode Setup**

To use Klaus Kode, clone the repo, create and activate a virtual environment, install the dependencies and run the startup script.

Here are those steps in detail:

1) Clone the Klaus Kode repo   
   

```shell
$ git clone https://github.com/quixio/quix-coding-agent.git
```

   

2) Set up a virtual environment and activate it (assuming Linux/Mac)  
   

```shell
$ python -m venv venv
$ source venv/bin/activate
```

   

3) Install the Klaus Kode dependencies.  
   

```shell
(venv)$ pip install -r requirements.txt
```

   

4) Create a .env file (make a copy of the.env example) and enter your API keys and PAT token  
   

```py
OPENAI_API_KEY=<your-openai-api-key> # "sk-proj..."
ANTHROPIC_API_KEY=<your-anthropic-api-key> # "sk-ant-api..."
QUIX_TOKEN=<your-quix-token> # "pat-..." 
QUIX_BASE_URL=https://portal-api.cloud.quix.io/

## OPTIONAL: If Klaus cannot autonmatically detect your Claude Code installation
CLAUDE_CLI_PATH=/home/username/.claude/local/node_modules/.bin
```

   

   

5) Run Klaus Kode  
   

```shell
(venv)$ python main.py
```

 


## **Klaus Kode Data Integration Workflow**

When you start Klaus Kode you’ll see the following options:

```

Select Workflow Type
--------------------
  ▶ 1. Source Workflow (Bring data in from another system)
    2. Sink Workflow (Write data out into an external system)
    3. Transform Workflow (Process data in flight) *Coming soon
    4. Debug Workflow (Diagnose and fix existing sandbox code) *Coming soon

```

Hopefully, the wording is straightforward enough to help you choose the right option.

 To understand the workflow better, let's look at an example scenario and break down how you would implement it in Klaus Kode. 

Suppose that I want to do some kind of research on Wikipedia page edits that happen in the coming week. In technical terms,  I want to listen to the Wikipedia Change Event Stream and sink the data to a Clickhouse database so that I can query it offline.

Here’s an outline of how it would work in Klaus Kode:

* First, you start Klaus Kode and choose the “**Source Workflow**” option (since we’re sourcing data from an external data stream)  
    
  * Klaus Kode will help you create a sandbox app for you to get started and will guide you through the process of creating Python code to get data out of the Wikipedia change event stream. This data is written to a “topic”  (a topic is essentially just a giant log file—a place to put the data we get from Wikipedia).

* Once that’s done,  you loop back to the start of the wizard and choose the “**Sink Workflow**”.

  * Klaus Kode will help you create another sandbox app and will guide you through the process of creating Python code to read from the topic you created in the source workflow, and sink that data into a Clickhouse database (with proper backpressure, batching and other dark magic)

This is a very simple example scenario, and we’re purposely not doing much to the data while it’s in flight (such as aggregating or analyzing it). The purpose of this early prototype is to simply show you how you can use AI to get high volumes of data in and out of any system. 

### **Source Workflow**

When following the sink workflow, you’ll be guided through the following phases:

[1—SOURCE SETUP](#1—source-setup-phase)

[2—KNOWLEDGE GATHERING](#2—knowledge-gathering-phase)

[3—CODE GENERATION](#3—code-generation-phase)

[4—CONNECTION CODE TESTING](#4—connection-code-testing-phase)

[5—FIRST DEBUG PHASE (IF CONNECTION CODE FAILS)](#5—first-debug-phase-\(if-connection-code-fails\))

[6—SCHEMA ANALYSIS](#6—schema-analysis-phase)

[5—PRODUCER CODE CREATION](#5—producer-code-creation-phase)

[6—PRODUCER CODE TESTING](#6—producer-code-testing-phase)

[7—SECOND DEBUG PHASE (IF CODE FAILS)](#7—second-debug-phase-\(if-producer-code-fails\))

[8—DEPLOYMENT](#8—deployment-phase)

---

#### 1—SOURCE SETUP PHASE {#1—source-setup-phase}

Klaus Kode will ask you for some details that are specific to the Quix Cloud environment (it detects these based on your PAT token). This where code is run and data is stored.

* Choose an **app name** for the sandbox app. Lets just call it “*wikipedia-source*”  
* Select a **Project**: Just choose the default “MyProject”  
* Select a **Topic**: Just choose the default “input-data” (a topic is essentially just a giant log file, a place to put the data we get from Wikipedia)

---

#### 2—KNOWLEDGE GATHERING PHASE {#2—knowledge-gathering-phase}

Next, Klaus Kode will ask you what you want to do, i.e. what kind of data you want to get from the source. The purpose of this phase is to create code that will connect to the source and read some sample data from it, and analyse the shape of the data. We will not write anything to a Kafka topic yet.

* **Enter Requirements**: Lets just say “*I want to read basic page edit metadata from the Wikipedia Change Event Stream”*   
  (you can of course be much more precise about the fields you want to get)

#### 3—CODE GENERATION PHASE {#3—code-generation-phase}

* **Generate Code:** Klaus Kode will invoke the mighty Claude Code CLI which will get to work drafting some code that reads from data from the Wikipedia EventStreams HTTP Service  
    
  In this step, you can switch to something else  and keep an eye on Claude while it works. The o might take a few minutes as Claude examples the existing documentation and the sample files in the “resources” directory.   
    
  * **Note about knowledge**: Klaus Kode comes with a knowledge folder where you can put documentation about any system that you want to connect to. Claude Code is configured to search the web but if you want to read from a proprietary system there probably wont be any documentation online. That’s the idea behind the knowledge folder. 

  * To accompany this tutorial, we’ve placed markdown version of the Wikipedia event stream documentation in the knowledge folder at the following location:  
    *  /resources/other/source\_external\_docs/Wikipedia Changes Event Stream HTTP Service \- Wikitech.md  
  * This helps Claude get the knowledge it needs without resorting to a web search straight away (which can slow things down).


* **Review Code:** When Claude is finished, Klaus prompts you to look at the generated code to make sure it’s OK — for now, let's just be lazy and place all our trust in Claude's ability to get it right — tap “**Y**”.

* **Collect Variables:** Claude is instructed to use environment variables in the code, but of course doesn't know what the values should be. Thus Klaus Kode will guide you though a questionnaire to configure values for the variables that Claude has decided will be necessary.

  * Luckily for us, the Wikipedia EventStreams Service doesn’t need an API key, so the only variable you’ll probably need to set the **output topic**. Claude will have proposed a default which may or may not match the one you selected in the previous step. You can choose another topic or accept the one that Claude proposed as a default either option is fine. 

---

#### 4—CONNECTION CODE TESTING PHASE {#4—connection-code-testing-phase}

In this phase, Klause Kode, will upload the file to the app sandbox in Quix Cloud, set the environment variables, install the dependencies and run the code.

Klaus Kode will then retrieve the output logs from the sandbox and examine the logs to determine if the run was successful or not. As mentioned before, the purpose is to get some sample data to try and infer the schema of the data.

Here’s an example of what what an event looks like when Klaus Kode successfully reads from the Wikipedia event stream

```
[23:20:59] Raw event received: <class 'dict'> with keys: ['$schema', 'meta', 'id', 'type', 'namespace', 'title', 'title_url', 'comment', 'timestamp', 'user', 'bot', 'log_id', 'log_type', 'log_action', 'log_params', 'log_action_comment', 'server_url', 'server_name', 'server_script_path', 'wiki', 'parsedcomment']
[23:20:59] Processing event #999997
  Title: File:Barbara Ronchi-66092.jpg
  User: Harald Krichel
  Wiki: commons.wikimedia.org
  Type: log
  Time: 2025-08-27T23:20:58Z
✅ Event #999997 produced successfully!

```

---

#### 5—FIRST DEBUG PHASE (IF CONNECTION CODE FAILS) {#5—first-debug-phase-(if-connection-code-fails)}

If for any reason Claude Code has created code that doesn’t work on the first try,  you’ll get some options to debug it.

```
1. Let Claude Code SDK fix the error directly
2. Provide manual feedback yourself
3. Retry with manual code fix (fix directly in IDE without regeneration)
4. Continue anyway (the error is not serious or you have fixed it in the IDE)
5. Abort the workflow
6. ⬅️ Go back to previous phase
7. 🚀 Auto-debug (keep retrying with Claude until fixed or 10 attempts)
```

If you want to have Claude fix the code, (but also manually inspect the fixed code first), press \#1. Otherwise the easiest option is to choose \#7 “Auto-debug”. 

In this case, Claude will read the log analysis, fix it, upload it, run it again. If the code still has bugs, it will repeat the same cycle if it works or the configured amount of attempts has been exceeded (by default 10).

**Note**: Be careful with auto-debug, Claude Clode can burn through API tokens by thinking copious amounts of thoughts. Currently, Claude is still not perfect at identifying incredibly basic connection issues (wrong password, port or hostname) and wont ask you to fix those on its behalf. Instead it can get very creative in trying to work around these issues. Thus, it’s a good idea to keep an eye on the auto-debug output for signs of a simple connection issue.

---

#### 6—SCHEMA ANALYSIS PHASE {#6—schema-analysis-phase}

If Klaus Kode determines that the test worked, it means that we have sample data available to analyze. Klaus Kode will then use the GPT to create some basic schema documentation that can be reused as knowledge to when creating the code for the main application (the app that actually writes the data to a Kafka topic).  

---

####  5—PRODUCER CODE CREATION PHASE {#5—producer-code-creation-phase}

In this phase, we create the main producer app that actually writes the data to a Kafka topic (later, we can then read this topic when we sink the data to Clickhouse).

* **Extra Requirements**: Klaus Kode will ask you if you have any extra requirements to add for the main app (for example maybe you only want to write certain fields to the topic and discard the rest). Lets just say “*Write all the metadata to a kafka topic”* 

* **Generate Code:** Klaus Kode will invoke the Claude Code CLI again, read the connection code that it successfully created previously and read appropriate samples to update the code with logic that will write the data to the topic (using the quixstreams python library).

---

#### 6—PRODUCER CODE TESTING PHASE {#6—producer-code-testing-phase}

Again, Klaus Kode, will upload the file to the app sandbox in Quix Cloud, set the environment variables, install the dependencies and run the code.

The purpose here is to make sure that the application is correctly writing data to the topic.

**REMINDER**: Claude (specifically Sonnet 4 \+ Claude Code CLI) can get things wrong, and often fails to get it right on the first attempt. Be prepared to go through multiple debug cycles. Since we are uploading and running the code in a cloud sandbox rather than locally, this can take a few minutes to go through each cycle (especially when Claude Code thinks a lot)

Here’s an example of what an event looks like when Klaus Kode produces data from the Wikipedia event stream to your selected topic.

```
[23:20:59] Raw event received: <class 'dict'> with keys: ['$schema', 'meta', 'id', 'type', 'namespace', 'title', 'title_url', 'comment', 'timestamp', 'user', 'bot', 'log_id', 'log_type', 'log_action', 'log_params', 'log_action_comment', 'server_url', 'server_name', 'server_script_path', 'wiki', 'parsedcomment']
[23:20:59] Processing event #999997
  Title: File:Barbara Ronchi-66092.jpg
  User: Harald Krichel
  Wiki: commons.wikimedia.org
  Type: log
  Time: 2025-08-27T23:20:58Z
✅ Event #999997 produced successfully!

```

---

#### 7—SECOND DEBUG PHASE (IF PRODUCER CODE FAILS) {#7—second-debug-phase-(if-producer-code-fails)}

Basically the same process as the first debug phase with the same options

---

#### 8—DEPLOYMENT PHASE {#8—deployment-phase}

If Klaus Kode determines that that data is being produced correctly, it will offer to deploy it for you in Quix Cloud. You can fill out the deployment details and opt to monitor the deployment logs using AI (GPT4o or 5-mini)

Klaus Kode will deploy the code in a Docker container that will run continuously (Quix Cloud uses Kubernetes under the hood to run containers). 

If you log into the Quix platform you’ll see a deployment that looks, like this:

![][image1]

You can then click the deployment title to open it and inspect the logs.

**NOTE**: It has been observed in testing that the deployments sometimes pick up an older version of the codec(only relevant if you’ve been through a couple of debug iterations). If this happens, just [redeploy your application](https://quix.io/docs/deploy/overview.html?h=redeploy#redeploying-a-service).

### **Sink Workflow**

The sink workflow isn’t much different from the Source workflow, except that we don’t need to create and test bespoke connection code to analyze the data. We can use standard service that reads from a topic using the Quix API.

Let's continue with our illustrative use case and sink the Wikipedia change events into a Clickhouse database. The chances are, you probably don’t have a Clickhouse database ready to go, but you can provision one in Quix Cloud using the utility script \`deploy\_clickhouse.py\` in the resources directory. Alternatively, you can use a service like Railway to provision an [external Clickhouse database](https://railway.com/deploy/clickhousehttps://railway.com/deploy/clickhouse). In this workflow example, we’ll assume you used the utility script to deploy a Clickhouse DB within Quix.

When following the sink workflow, you’ll be guided through the following phases:

[1—SINK SETUP](#1—sink-setup-phase)

[3—SCHEMA ANALYSIS](#3—schema-analysis-phase)

[4—SINK CODE CREATION](#4—sink-code-creation-phase)

[5—SINK CODE TESTING](#5—sink-code-testing-phase)

[6—SINK DEBUG PHASE (IF CODE FAILS)](#6—sink-debug-phase-\(if-code-fails\))

[7—DEPLOYMENT](#7—deployment-phase)

#### 1—SINK SETUP PHASE {#1—sink-setup-phase}

Now it will ask you for some details that are specific to the Quix Cloud environment (it detects these based in your PAT token)

* Select a **Project**: Just choose the default “MyProject”  
* Select a **Topic**: Just choose the default “input-data” (a topic is essential just a giant log file, a place to output the data we get from Wikipedia)

#### 3—SCHEMA ANALYSIS PHASE {#3—schema-analysis-phase}

Klaus Kode will retrieve a data sample from your selected input topic, then analyze it to infer the schema. Klaus Kode will then use the GPT to create some basic schema documentation that can be reused as knowledge when creating the code for the main application (the app that actually consumes the data from the Kafka topic).  

#### 4—SINK CODE CREATION PHASE {#4—sink-code-creation-phase}

In this phase, we create the main consumer app that actually reads the data from the Kafka topic and sinks it to the destination system. Klaus Kode will prompt you to tell it what kind of sink application you want to create.

* **Enter Requirements**: Lets just say “*I want to write all the page edit metadata from the source topic into clickhouse using clickhouse-connect”* 

  Note that we’re being prescriptive with the Python library that we want to use here (clickhouse-connect), since Claude occasionally uses a different approach that might not be suitable for the latest version of Clickhouse. You can also leave it up to Claude to choose the Python library it thinks is best. Yet, sometimes this results in longer debug cycles if there's an error on the first try (since Claude Code will eventually search the web to find out what it is supposed to use).

* **Generate Code:** Klaus Kode will invoke the Claude Code CLI again, read the connection code that it successfully created previously and read appropriate samples to update the code with logic that will write the data to the topic (using the quixstreams python library).

#### 5—SINK CODE TESTING PHASE {#5—sink-code-testing-phase}

Klaus Kode, will upload the file to the app sandbox in Quix Cloud, set the environment variables, install the dependencies and run the code.

The purpose here is to make sure that the application is correctly sinking data to Clickhouse (or whatever destination you are using)

**REMINDER**: Claude (specifically Sonnet 4 \+ Claude Code CLI) can get things wrong, and often fails to get it right on the first attempt. Be prepared to go through multiple debug cycles. Since we are uploading and running the code in a cloud sandbox rather than locally, this can take a few minutes to go through each cycle (especially when Claude Code thinks a lot)

Here’s an example of what what an event looks like when Klaus Kode successfully reads from the Wikipedia event stream

```
[23:20:59] Raw event received: <class 'dict'> with keys: ['$schema', 'meta', 'id', 'type', 'namespace', 'title', 'title_url', 'comment', 'timestamp', 'user', 'bot', 'log_id', 'log_type', 'log_action', 'log_params', 'log_action_comment', 'server_url', 'server_name', 'server_script_path', 'wiki', 'parsedcomment']
[23:20:59] Processing event #999997
  Title: File:Barbara Ronchi-66092.jpg
  User: Harald Krichel
  Wiki: commons.wikimedia.org
  Type: log
  Time: 2025-08-27T23:20:58Z
✅ Event #999997 produced successfully!

```

#### 6—SINK DEBUG PHASE (IF CODE FAILS) {#6—sink-debug-phase-(if-code-fails)}

Again, if the code that doesn’t work on the first try,  you’ll get some options to debug it.

```
1. Let Claude Code SDK fix the error directly
2. Provide manual feedback yourself
3. Retry with manual code fix (fix directly in IDE without regeneration)
4. Continue anyway (the error is not serious or you have fixed it in the IDE)
5. Abort the workflow
6. ⬅️ Go back to previous phase
7. 🚀 Auto-debug (keep retrying with Claude until fixed or 10 attempts)
```

If you want to have Claude fix the code, (but also manually inspect the fixed code first), press \#1. Otherwise the easiest option is to choose \#7 “Auto-debug”. 

In this case, Claude will read the log analysis, fix it, upload it, run it again. If the code still has bugs, it will repeat the same cycle if it works or the configured amount of attempts has been exceeded (by default 10).

**Reminder**: The usual caveat applies here too: Be careful with auto-debug, Claude Clode can burn through API tokens by thinking copious amounts of thoughts. Currently, Claude is still not perfect at identifying incredibly basic connection issues (wrong password, port or hostname) and wont ask you to fix those on its behalf. Instead it can get very creative in trying to work around these issues. Thus, it’s a good idea to keep an eye on the auto-debug output for signs of a simple connection issue.

#### 7—DEPLOYMENT PHASE {#7—deployment-phase}

If Klaus Kode determines that that data is being produced correctly, it will offer to deploy it for you in Quix Cloud. You can fill out the deployment details and opt to monitor the deployment logs using AI (GPT4o or 5-mini)

### 

## **Klaus Kode configuration**

### **Local Configuration (Optional)**

For installation-specific settings (like Claude CLI path), use a local config file that won't be committed to git:

1. **Option 1: Environment Variable** (Recommended)

```shell
export CLAUDE_CLI_PATH=/path/to/your/claude/cli/bin
```

2. **Option 2: Local Config File**

```shell
cp config/local.yaml.example config/local.yaml
# Edit config/local.yaml with your Claude CLI path
```

The system will auto-detect Claude CLI in common locations if not configured. Any detected paths are saved to `config/local.yaml` (which is gitignored) for future use.

## 

[image1]: <data:image/png;base64,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>
