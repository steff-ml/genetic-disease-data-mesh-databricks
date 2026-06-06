Back to [README.md](../README.md)

# Setup

## Contents

- [Prerequisites](#prerequisites)
- [Databricks](#databricks)
  - [VS Code extension](#vs-code-extension)
  - [Databricks Connect](#databricks-connect)
  - [Asset Bundles (DABs)](#asset-bundles-dabs)
- [Local Coding Agents](#local-coding-agents)
  - [Ollama](#ollama)
  - [OpenCode](#opencode)
- [Claude Code Agents](#claude-code-agents)
  - [Available agents](#available-agents)
  - [doc-sync — when and how to use it](#doc-sync--when-and-how-to-use-it)
- [Running the Test Suite](#running-the-test-suite)

---

## Prerequisites

- Windows 10/11
- NVIDIA GPU with up-to-date drivers (recommended)
- Windows Terminal (recommended)
- Node.js ([nodejs.org](https://nodejs.org))

---

## Databricks

This project runs on a Databricks Free tier workspace with Unity Catalog. Authentication uses OAuth (browser-based login) — not Personal Access Tokens. OAuth tokens are short-lived and automatically refreshed; no secrets need to be stored or rotated manually.

### VS Code extension

The Databricks extension for VS Code lets you browse Unity Catalog, run notebooks on remote clusters, and configure Databricks Connect — all from inside VS Code.

#### Step by Step Setup

**1. Install the extension**

In VS Code, open the Extensions panel and search for `Databricks`. Install the extension published by Databricks (`ms-databricks.databricks`).

**2. Open the Databricks panel**

Click the Databricks icon in the VS Code activity bar (left sidebar). You will see a "Configure Databricks" prompt if no workspace is connected.

**3. Enter your workspace host**

Click **Configure Databricks** and enter your workspace URL when prompted:

```
https://<your-workspace-id>.azuredatabricks.net
```

Your workspace URL is shown in the browser address bar when you log in to Databricks.

**4. Select OAuth as the authentication method**

When asked for an authentication method, choose **OAuth (browser-based)**. Do **not** choose Personal Access Token.

A browser window opens. Log in with your Databricks account credentials and click **Allow** to authorise VS Code.

**5. Select a cluster (optional)**

After connecting, the extension may prompt you to select a cluster for Databricks Connect. Choose an existing cluster or skip — you can configure this later.

#### How to Verify Setup

The Databricks panel in VS Code should show your workspace URL and Unity Catalog tree (catalogs → schemas → tables). If you see the `discovery`, `clinical`, and `reference` catalogs, the connection is working.

#### Common Setup Errors

| Symptom | Fix |
|---------|-----|
| Browser opens but redirects to an error page | Ensure you are logged into the correct Databricks account in the browser before authorising |
| "Host not found" or connection timeout | Double-check the workspace URL — it must be the full `https://...azuredatabricks.net` URL, not the Databricks community URL |
| Unity Catalog not visible | The Free tier workspace must have Unity Catalog enabled; confirm in the Databricks UI under **Data** |
| Extension prompts for a PAT | Close the prompt and restart the "Configure Databricks" flow — make sure to select OAuth, not the token option |

---

### Databricks Connect

Databricks Connect allows you to run PySpark code locally in VS Code against a remote Databricks cluster. This is used for iterating on pipeline logic without uploading notebooks.

#### Step by Step Setup

**1. Install Databricks Connect**

Install the version matching your cluster's Databricks Runtime (DBR). Check your cluster's runtime version in the Databricks UI under **Compute**.

```powershell
pip install databricks-connect==15.4.*   # replace 15.4 with your DBR version
```

**2. Configure via the VS Code extension**

In the Databricks panel, select your cluster under **Cluster**. The extension writes the connection config automatically — no manual `databricks.yml` editing needed.

Alternatively, configure via the CLI (if you prefer):

```powershell
databricks auth login --host https://<your-workspace-id>.azuredatabricks.net
# Browser opens — log in and authorise
```

This stores an OAuth token at `~/.databricks/token-cache.json`. Databricks Connect picks it up automatically.

**3. Test the connection**

Open a Python terminal in VS Code and run:

```python
from databricks.connect import DatabricksSession
spark = DatabricksSession.builder.getOrCreate()
spark.sql("SHOW CATALOGS").show()
```

You should see `discovery`, `clinical`, and `reference` in the output.

#### How to Verify Setup

```powershell
databricks auth env --profile DEFAULT
# Should print DATABRICKS_HOST and DATABRICKS_TOKEN without errors
```

#### Common Setup Errors

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError: databricks.connect` | Run `pip install databricks-connect==<your-DBR-version>.*` |
| `INVALID_PARAMETER_VALUE: Cluster ... not found` | The cluster may have been terminated — restart it in the Databricks UI before connecting |
| Version mismatch error on import | The installed `databricks-connect` version must match the cluster's DBR major version exactly |
| OAuth token expired | Run `databricks auth login` again — tokens are refreshed automatically during normal use but may expire after long idle periods |

---

### Asset Bundles (DABs)

Databricks Asset Bundles are the declarative way to define, version-control, and deploy Databricks resources — DLT pipelines, jobs, and cluster configurations — as YAML. The bundle lives in the repo alongside the pipeline code and is deployed via the Databricks CLI.

#### Step by Step Setup

**1. Install the Databricks CLI**

```powershell
winget install Databricks.DatabricksCLI
# Reopen PowerShell after installation
databricks --version  # confirm it installed
```

**2. Authenticate**

If you have already completed the VS Code extension setup, the OAuth token is already cached and the CLI picks it up automatically. If not, run:

```powershell
databricks auth login --host https://<your-workspace-id>.azuredatabricks.net
# Browser opens — log in and authorise
```

**3. Initialise the bundle in the existing project**

From the project root:

```powershell
databricks bundle init
```

The CLI will prompt for a project name and target host, then generate a `databricks.yml` at the project root. For this project, accept the defaults and edit the file afterwards — do not let it create a new subdirectory.

A minimal starting configuration for this project:

```yaml
bundle:
  name: genetic-disease-data-mesh

targets:
  dev:
    mode: development
    default: true
    workspace:
      host: https://<your-workspace-id>.azuredatabricks.net

resources:
  pipelines:
    discovery_bronze:
      name: "[dev] Discovery Bronze Ingestion"
      target: discovery
      libraries:
        - notebook:
            path: ./pipelines/discovery/bronze_ingestion.py
```

`mode: development` prefixes all resource names with `[dev]` and prevents dev deployments from overwriting production resources.

**4. Validate the bundle**

```powershell
databricks bundle validate
```

This checks the YAML syntax and resolves variable references without deploying anything.

**5. Deploy**

```powershell
databricks bundle deploy --target dev
```

The CLI uploads pipeline definitions and notebooks to the workspace. On first run it creates the resources; subsequent runs update them in place.

**6. Run a pipeline**

```powershell
databricks bundle run discovery_bronze --target dev
```

Use the resource key from `databricks.yml` (e.g. `discovery_bronze`), not the display name.

#### How to Verify Setup

```powershell
databricks bundle validate           # exits 0 with a summary if config is valid
databricks bundle deploy --dry-run   # shows what would be deployed without deploying
```

After a successful deploy, the pipeline should appear in the Databricks UI under **Workflows → Delta Live Tables**.

#### Common Setup Errors

| Symptom | Fix |
|---------|-----|
| `databricks: command not found` | Reopen PowerShell after `winget install`; confirm with `databricks --version` |
| `Error: cannot resolve host` | Run `databricks auth login` to refresh the OAuth token |
| `RESOURCE_CONFLICT: Pipeline already exists` | The pipeline was created manually in the UI — import it into the bundle or delete the manual copy |
| `INVALID_PARAMETER_VALUE: target schema not found` | The Unity Catalog schema (e.g. `discovery.bronze`) must exist before deploying; create it in the Databricks UI or via SQL first |
| Bundle init creates a new subdirectory | Run `databricks bundle init` from the project root and set the output path to `.` when prompted |

---

## Local Coding Agents

Local coding agents allow you to run agentic code generation tasks using a locally-hosted model instead of a cloud API. The primary use in this project is the `api-stub` OpenCode agent, which scaffolds Bronze exploration notebooks using a Qwen model running on Ollama.

### Ollama

Ollama hosts local LLMs and exposes an OpenAI-compatible REST API on port 11434.

#### Step by Step Setup

**1. Install Ollama**

Download the installer from [ollama.com](https://ollama.com) and run it. Ollama installs as a background service and adds itself to the system tray.

**2. Configure Ollama to listen on all interfaces**

By default Ollama only listens on localhost. If you plan to use it from WSL or other tools:

```powershell
[System.Environment]::SetEnvironmentVariable("OLLAMA_HOST", "0.0.0.0", "Machine")
```

Fully quit Ollama from the system tray and relaunch it for the change to take effect.

**3. Pull the model**

```powershell
ollama pull qwen3.5:9b
ollama list
```

**4. Create a custom model with expanded context**

Ollama defaults to 4096 tokens, which is too small for agentic tool use:

```powershell
"FROM qwen3.5:9b`nPARAMETER num_ctx 32768`nPARAMETER num_predict 4096" | Out-File -Encoding utf8 $env:USERPROFILE\Modelfile-qwen
ollama create qwen3.5:9b-32k -f $env:USERPROFILE\Modelfile-qwen
ollama list
```

#### How to Verify Setup

```powershell
ollama --version
netstat -ano | findstr "11434"        # should show 0.0.0.0:11434
curl http://localhost:11434/api/tags  # should return JSON listing models
ollama run qwen3.5:9b-32k "say hello" # type /bye to exit
```

#### Common Setup Errors

| Symptom | Fix |
|---------|-----|
| `ollama` command not found | Reopen PowerShell — Ollama adds itself to PATH but requires a fresh session |
| GPU not detected | Update NVIDIA drivers; check Ollama system tray logs for GPU layer offloading confirmation |
| Port 11434 not reachable from WSL | Confirm `OLLAMA_HOST=0.0.0.0` and Ollama was fully restarted after setting it |
| Model runs slowly | Check `netstat` shows `0.0.0.0` not `127.0.0.1`; close GPU-heavy applications competing for VRAM |

---

### OpenCode

OpenCode is an open-source CLI agentic coding tool. It connects to Ollama and runs the `api-stub` agent for generating disposable Bronze exploration notebooks.

#### Step by Step Setup

**1. Install OpenCode**

```powershell
npm install -g opencode-ai

# Add npm to PATH so 'opencode' works directly
$npmPrefix = npm config get prefix
[System.Environment]::SetEnvironmentVariable("PATH", $env:PATH + ";$npmPrefix", "User")
# Reopen PowerShell after this
```

**2. Create the OpenCode config file**

```powershell
mkdir $env:USERPROFILE\.config\opencode
notepad $env:USERPROFILE\.config\opencode\opencode.json
```

Paste and save:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "ollama": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Ollama (local)",
      "options": {
        "baseURL": "http://localhost:11434/v1"
      },
      "models": {
        "qwen3.5:9b-32k": { "tools": true }
      }
    }
  },
  "model": "ollama/qwen3.5:9b-32k"
}
```

**3. Add the auth placeholder**

OpenCode expects an auth entry even for local models:

```powershell
mkdir $env:USERPROFILE\AppData\Local\opencode
'{"ollama": {"type": "api", "key": "ollama"}}' | Out-File -Encoding utf8 $env:USERPROFILE\AppData\Local\opencode\auth.json
```

**4. Launch OpenCode**

```powershell
cd C:\path\to\your\project
opencode
```

> Always use Windows Terminal or VS Code Terminal — the TUI requires proper terminal support. Use `Shift+Enter` to send messages; `Enter` adds a newline.

**5. Activate the api-stub agent**

Inside OpenCode, type `/models` to confirm `qwen3.5:9b-32k` is available, then invoke the agent by name: `api-stub`.

#### How to Verify Setup

```powershell
opencode --version
# Inside OpenCode:
/models   # confirm qwen3.5:9b-32k appears
```

#### Common Setup Errors

| Symptom | Fix |
|---------|-----|
| `opencode: command not found` | Reopen PowerShell after updating PATH |
| Model not found / API connection error | Run `ollama list` to confirm the model exists; verify `OLLAMA_HOST=0.0.0.0` and Ollama was restarted |
| Agent thinks but doesn't act | Context window too small — recreate the custom model with a higher `num_ctx` value |
| TUI not responding | Switch to Windows Terminal; the default PowerShell console has limited TUI support |

---

## Claude Code Agents

Claude Code agents extend Claude Code with specialised, project-aware behaviour. They live in [.claude/agents/](.claude/agents/) and are invoked by name in any Claude Code conversation — no installation required beyond having Claude Code running.

### Available agents

| Agent | When to invoke |
|-------|---------------|
| `doc-sync` | End of a session where production code changed — syncs ADRs, contracts, README, scientific background |
| `adr-drafter` | Starting a new architectural decision — guides you through context, alternatives, and rationale |
| `contract-drafter` | After defining a new Gold table — generates the Bitol YAML contract skeleton |
| `schema-validator` | Before a PR touching a Gold table — checks actual Delta schema against the declared contract (stub: needs Databricks Connect) |
| `quality-report` | After a DLT pipeline run — formats expectation failures into a triage report (stub: needs a running pipeline) |
| `setup-guide` | After completing any setup step — appends the commands and context to this file in the correct section |

### doc-sync — when and how to use it

`doc-sync` is the most regularly-used agent. Its job is to keep structured documentation (ADRs, Bitol contracts, README, scientific background) in sync with the code after a working session.

**When to invoke**

Run doc-sync at the end of any session where production code changed. Specifically after:

- A Gold table schema changes (column added, removed, renamed, or type changed)
- A new data product is published or an existing one is retired
- Pipeline ingestion or transformation logic is modified
- An access control rule or Unity Catalog grant changes
- An ADR decision gets implemented in code and its status should advance

Do **not** invoke after changes to `personal.exploration` notebooks — those are ungoverned and do not require documentation updates.

**How to invoke**

Option 1 — slash command (preferred):

```
/doc-sync
```

This triggers the slash command defined in `.claude/commands/doc-sync.md`, which instructs doc-sync to read the git diff against `main`, identify what changed, and propose updates.

Option 2 — direct agent invocation:

> Use the doc-sync agent. Read `git diff main`, identify what changed, and propose documentation updates.

**What happens**

1. The agent reads `git diff main` and categorises changes by type.
2. It routes each change to the appropriate sub-agent (`adr-updater`, `data-product-doc`, `readme-updater`, or `scientific-background-sync`).
3. All proposed changes are presented as diffs for your review — **nothing is written until you approve**.
4. The agent does not commit. You review the diffs and commit when satisfied.

**Other agents — quick invocation examples**

```
Use the adr-drafter agent. I need to decide how to handle schema evolution in Bronze tables.
```

```
Use the contract-drafter agent. Here is the DLT table definition for discovery.gold.patient_mutation_profile: [paste table definition]
```

```
Use the setup-guide agent. I just configured Databricks CLI authentication. Here are the commands I ran: [paste commands]
```

---

## Running the Test Suite

*(Not yet configured — update this section when the first DLT pipeline test suite is added.)*
