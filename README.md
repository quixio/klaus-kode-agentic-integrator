# Quix Coding Agent Prototype

## Prerequisites

### Environment Variables
Copy the `.env.example` as `.env` and populate the required values.
You will need the following credentials:
* Quix PAT token for Quix API Operations
* `OPENAI_API_KEY` for GPT related calls (schema analysis, template matching)
* `ANTHOPIC_API_KEY` for code generation calls (GPT o3 still seems to be lacklustre compared to Sonnet 4)
  * If you dont want to set up these keys yourself ask MC to generate some for you.
  * If you really want to change the model to an OpenAI one, you can update the model config file `./config/models.yaml`.

### Local Configuration (Optional)
For installation-specific settings (like Claude CLI path), use a local config file that won't be committed to git:

1. **Option 1: Environment Variable** (Recommended)
   ```bash
   export CLAUDE_CLI_PATH=/path/to/your/claude/cli/bin
   ```

2. **Option 2: Local Config File**
   ```bash
   cp config/local.yaml.example config/local.yaml
   # Edit config/local.yaml with your Claude CLI path
   ```

The system will auto-detect Claude CLI in common locations if not configured. Any detected paths are saved to `config/local.yaml` (which is gitignored) for future use.
  
  

## Testing instructions:
* Clone this repo and check out the branch `e2e_v2`.
* Create a `venv`, preferably with Python 3.12.*
* Install the requirements with `pip install -r requirements.txt`
* Actviate the `venv` with `source venv/bin/activate` (linux/mac)
* Run `python main.py` or `python3 main.py`
<img width="913" height="445" alt="image" src="https://github.com/user-attachments/assets/6d7ff3e8-9ff0-4cb5-86d5-f19b38391eb8" />

## Workfow

**Connection Details Phase**
1. Select Workspace
2. Select Topic
3. Enter target Technology name (i.e Oracle DB, IBM DB2, ect..)
4. 🤖 AI Agent will prepare a short prerequisites document for you and show it to you, to remind you of all the credentials that you need to have in place.

**Knowledge Gathering Phase**
1. 🤖 AI Agent finds the nearest matching template
2. 👷 Workflow Agent Asks you if you agree with its match.
3. 👷 Workflow Agent Creates an app in Quix using the template and downloads all the files (`app.yaml`,`main.py`, `requirements.txt` as knowledge).


**Environment variable definition Phase**
1. 👷 Workflow Agent converts downloaded `app.yaml` (from template) to local .env file.
2. 🤖 AI Agent looks at env file and tries to find equivalents for the target technology (i.e Google Storage Bucket or whatever)
3. 🤖 AI Agent looks at new env var list and creates suggestion list for any extra vars.
4. 👷 Workflow Agent iterates through converted env var list and askes you to fill out the values.
5. 👷 Workflow Agent asks you if you want to use any of extra suggested env vars too
6. 👷 Workflow Agent asks you to pick items from the suggested env var list and fill out the values. 
7. 👷 Workflow Agent asks you if there are any extra free-form values that you want to add.

## From here, workflow differs depending on whether you selected SOURCE or SINK

### SOURCE Creation Workflow

**Connector Code Generation**
This phase is required to get the "shape" of the data from the external system so that the AI later knows how to convert it to a Kafka message.

1. 🤖 AI Agent (Claude Sonnet 4) recieves knowledge from Agent (env vars, template code, Quix source docs) and 👷 Workflow Agent asks for draft code to "read 10 samples" from target system
2. 👷 Workflow Agent shows you the draft connection code that the AI produced and asks if it looks OK.

**Connector Code Testing**
1. 👷 Workflow Agent uploads the code to the app and runs it in the IDE and attempts to get 10 sample items/entries/ect...
2. If there's an ERROR:

    You can choose a debugging approach:
      * **1)** Let 🤖 AI Agent analyze the error and propose a fix (it usually fixes the code after 1-3 interations)
        * GPT o3 analyses the issue and proposes a fix which you need to accept.
        * GPT's suggestion is given back to the AI Agent and it implements the fix and runs it in the IDE again.
      * **2)** Provide manual feedback yourself
      * **3)** Fixed the issue in the IDE yourself and opt to continue
      * **4)** Abort the workflow

**Data Analysis**
1. 👷 Workflow Agent downloads the logs of the successful run which prints the data it received from the system and passes it to AI for analysis
2. 🤖 AI Agent reads the data and creates "Schema Documentation" to describe the shape of the data and adds advice for transforming it to a Kafka message (saved as markdown file)
3. 👷 Workflow Agent asks you if you're fine with the analysis.

    * If you're not fine with it:

      You can:
        * **1)** Prompt the AI Agent to generate it again with your own prompt
        * **2)** Edit the "schema documentation" markdown file yourself and proceed.
        * **3)** Abort the workflow.

**Final Code Generation and Testing**
1. 🤖 AI Agent (Claude Sonnet 4) receives knowledge from Agent (env vars, previous sucessful connection code, Quix Source docs) and 👷 Workflow Agent asks for final code to write the data to the designated Kafka topic.

2. 👷 Workflow Agent shows you the code and asks you if it looks OK.

   * If you're not fine with it:

     You can:
      * **1)** Prompt the AI Agent to generate it again with your own prompt, until you are happy with it.
      * **2)** Abort the workflow.

3. 👷 Workflow Agent uploads the code to the IDE, runs it, and checks the logs for keywords that indicate signs of an error.

    If there's an ERROR:

   * You can choose a debugging approach:
      * **1)** Let 🤖 AI Agent analyze the error and propose a fix (it usually fixes the code after 1-3 interations)
        * GPT o3 analyses the issue and proposes a fix which you need to accept.
        * GPT's suggestion is given back to the AI Agent and it implements the fix and runs it in the IDE again.
      * **2)** Provide manual feedback yourself
      * **3)** Fixed the issue in the IDE yourself and opt to continue
      * **4)** Abort the workflow

**Deployment Phase**
Assuming test worked...
1. 👷 Workflow Agent asks you if you want to prepare the code for deployment (take out the stop conditions)
2. 🤖 AI Agent removes the stop conditions and commits the changes.
3. 👷 Workflow Agent asks you if you want to deploy.
  * **Note**: we need a short delay for stop condition removal to register as the "latest" commit.
  * If we deploy too quickly, the stop conditions are left in the code as it takes about 10 seconds for the commit to propagate.
4. 👷 Workflow Agent deploys the app and monitors the status until it reaches a terminal state (Running or Error) .
5. If build successful, 🤖 AI Agent gets the first 100 entries of runtime logs to make sure everything is OK, and gives you its assessment,
6. If the build errors, 🤖 AI Agent gets the build logs and provides a fix recommendation.

   
# Current implementation details (07.08.2025)

* The current workflow pompts you to choose a workflow, bu the Source and Sink workflows are the only ones that work E2E right now.
* I have tested it with the following technologies so far:
   * Sources (Google Sheets, Google Storage Bucket)
   * Sinks (TimescaleDB, QuestDB, Google Sheets)
   * Need to work through the [coming soon list](https://quix.io/docs/quix-connectors/quix-streams/sinks/coming-soon/Clickhouse-sink.html) to test more technologies
* When it does make mistakes, it's usually always the same ones, so we just need to improve the debugger with a common checklist.
* Quite often, the issues have nothing to do with the code, just misconfigured environment variables.
  * In testing it will be helpful if you note down the classic mistakes that it makes.
* The whole interaction flow is logged to the logging dir, so you can take a closer look at the debugging output
* The files that it generates along the way are saved to working_files, and are used a cached answers if you dont want to repeatedly answer the same questions
* Your answers and generated artifacts are cached so you dont have to enter the same input each team on repeat attempts (however generated code is not yet cached)

# TODOS

**Debug an existing app**
 * For some people, it might be faster just to boostrap a starter template in the UI and configure the env vars yourself.
 * Maybe the user has already started some of the code themselves.
 * In this case, we just want the AI to just straight to looking at the code and update it for a use case that the user types in as their prompt and go through the workflow it getting it to work.

 **Use web search and RunLLM for enhanced knowledge**
 * For newer technologies, it would help to do a web search as part of the knowledge gatherings phase (about how to connect)
 * See how good RunLLM is at debugging/first draft generation (it's more expensive and rate-limited so left it out for now.)
 
 **Misc Smaller things**

 * (_still TODO 07.08_) Before deployment, the agent is supposed to use a simple regex to remove the stop conditions (count, timeout) which it does no problem.
   * However, when it proceeds to deploy, the deployment immediately recognizes that it is out of date (and still has the stop conditions in it). Need to do a manual syc in the UI and sometimes service restart to get the changes to kick in.
   * There is some kind of timing or commit issue when it prepares the code for deployment.

 * (_still TODO 07.08_) Give the debugging agent the root README from the quixstreams repo for a more general guide on how to handle data (The quixstreams README is quite long so we preserve tokens by only using it when we really need it)

 * (_still TODO 07.08_) Give the debugging agent a list of common issues to check (See also the [Common Issues Google Doc](https://docs.google.com/document/d/1xp3rNV5eyrv4ZTMBnl4yDVmQ67y_KAvncWenQhQy4l4/edit?usp=sharing) )
 
 * (_still TODO 07.08_) Fix double dependency installation: Template requirements: `['quixstreams[postgresql]==3.14.1', 'python-dotenv'] Additional packages detected from generated code: ['psycopg2-binary', 'python-dotenv', 'quixstreams']`
