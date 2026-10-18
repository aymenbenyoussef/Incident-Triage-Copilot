# Incident Triage Copilot

Incident Triage Copilot is a local AI assistant for investigating simulated
production incidents. It uses an Ollama language model and the Model Context
Protocol (MCP) to gather evidence from logs, metrics, and deployment history,
then produces a concise incident report. Reports are printed in the terminal
and saved as structured, timestamped PDF files in `reports/`.

The project is designed to demonstrate how an incident-response agent can be
given useful operational capabilities without giving it unrestricted access to
production systems. Read-only investigation is available to viewers, while
potentially disruptive actions are protected by role checks, explicit human
approval, and an audit log.

## Project goals

- Provide a focused incident investigation workflow for common failure modes.
- Keep observation separate from actions.
- Treat data returned from observability tools as untrusted input.
- Require a human decision before any simulated destructive action.
- Make authentication, authorization, rate limiting, and auditability visible
  parts of the agent architecture.
- Offer a reproducible local environment for testing agent behavior.

## How the system works

```text
User problem
     |
     v
Agent (Ollama tool-calling loop)
     |
     | MCP over HTTP with bearer token
     v
Gateway
  - authentication
  - role-based access control
  - rate limiting
  - request logging
  - error masking
     |
     +------------------+
     |                  |
     v                  v
 Observe server      Actions server
 read-only tools     approval-gated tools
     |                  |
     +--------+---------+
              v
        SQLite data store
   logs, metrics, deploys, audit
```

### Agent

[`agent/agent.py`](agent/agent.py)
connects to the gateway, discovers the available MCP tools, and gives them to
the Ollama model. It keeps a bounded tool-calling loop, converts tool results
back into model messages, and asks for a report in this format:

```text
INCIDENT SUMMARY: ...
SEVERITY: ...
AFFECTED SERVICES: ...
TIMELINE: ...
ROOT CAUSE: ...
CONFIDENCE: ...
EVIDENCE: ...
CUSTOMER IMPACT: ...
RECOMMENDED ACTION: ...
FOLLOW-UP INVESTIGATION: ...
```

The agent prompt explicitly tells the model that tool output is data, not
instructions. It also limits valid services, metrics, and tool names and stops
after a configurable maximum number of steps.

### Gateway

[`servers/gateway.py`](servers/gateway.py)
is the single MCP endpoint exposed to the agent. It mounts the Observe and
Actions servers and applies shared controls:

- bearer-token authentication;
- role checks for action tools;
- a five-request-per-second rate limit with a burst capacity of ten;
- request timing and actor logging;
- masking of unexpected internal error details.

The included tokens are static development credentials. They are useful for
local demonstrations, but a real deployment should use an identity provider
and short-lived OAuth or JWT credentials.

### Observe server

[`servers/observe.py`](servers/observe.py)
contains read-only access to the simulated production data. Inputs use
constrained service, log-level, and metric values, bounded time windows, and
bounded result sizes. Database queries are parameterized.

The log search response is deliberately marked as `untrusted_data` and
includes a warning that log text must not be treated as instructions. Log
messages are also truncated before they are returned to the agent.

### Actions server

[`servers/actions.py`](servers/actions.py)
contains simulated operations that could change service state:

- restarting a service;
- rolling a service back to its previous deployment.

Each call requires the `oncall` role and an explicit elicitation response from a
human. Both approved and denied attempts are recorded in the `audit` table.
Because the environment is simulated, these operations update SQLite data
instead of touching real infrastructure.

### Simulator

[`sim/generate.py`](sim/generate.py)
creates deterministic SQLite fixtures containing healthy baseline traffic and
one selected incident. It can also insert a prompt-injection string into a log
entry so the safety controls can be exercised.

## Capabilities

| Capability | Tool or resource | Required role | Approval |
|---|---|---|---|
| Search recent logs | `search_logs` | `viewer` | No |
| Read metric summaries and time series | `get_metrics` | `viewer` | No |
| List recent deployments | `list_recent_deploys` | `viewer` | No |
| Read current service health | `service://{name}/health` | `viewer` | No |
| Restart a service | `restart_service` | `oncall` | Yes |
| Roll back a deployment | `rollback_deploy` | `oncall` | Yes |

Supported services are `web`, `api`, and `db`. Supported metrics are `cpu`,
`memory`, `latency_ms`, and `disk_pct`. Log levels are `INFO`, `WARN`, and
`ERROR`.

## Incident scenarios

The simulator models five scenarios:

| Scenario | Evidence pattern | Expected diagnosis |
|---|---|---|
| `bad_deploy` | `api` version `v2.3.0` is followed by checkout errors and rising latency | The `v2.3.0` deployment |
| `memory_leak` | `api` memory steadily rises and ends with heap errors | A memory leak in `api` |
| `db_pool_exhaustion` | The database pool is exhausted and API requests time out acquiring connections | Database connection pool exhaustion |
| `upstream_timeout` | Payment-provider calls time out and `web` returns 502 responses | An upstream payment dependency timeout |
| `disk_full` | Database disk usage reaches 100% and writes fail with "No space left on device" | A full database disk |

## Security and safety model

| Risk | Control |
|---|---|
| Instructions hidden in log messages influence the model | Tool output is labelled untrusted, logs are truncated, and the agent prompt treats output as data |
| A viewer invokes a disruptive operation | Gateway middleware requires the on-call role, represented by the `act` scope, for action tools |
| Malformed or oversized tool arguments | Literal input constraints and bounded numeric fields are enforced at the MCP boundary |
| SQL injection through observation parameters | All database queries use parameters rather than string interpolation |
| An action occurs without a human decision | Actions use MCP elicitation and reject anything other than an explicit approval |
| No record of an action attempt | Approved and denied attempts are written to the audit table |
| Runaway model behavior | The gateway rate limit and agent maximum-step limit bound tool usage |
| Internal implementation details leak through errors | FastMCP error masking is enabled on the servers and gateway |

The injection tests cover the important defense-in-depth property: even if a
model follows malicious text from a log and attempts a rollback, the human
approval gate can still deny the operation.

## Data model

The simulator stores data in SQLite:

- `logs(ts, service, level, message)` contains timestamped service messages.
- `metrics(ts, service, metric, value)` contains time-series measurements.
- `deploys(ts, service, version, author)` contains deployment history.
- `audit(ts, actor, tool, args, outcome)` records action decisions.

The default database is `data/prod.db`. Generating a scenario recreates the
observability tables and preserves the audit-table schema for action tracking.

## Configuration

Configuration is supplied through environment variables:

| Variable | Default | Description |
|---|---|---|
| `TRIAGE_DB` | `data/prod.db` | SQLite database path |
| `VIEWER_TOKEN` | `viewer-dev-token` | Token with read-only access |
| `ONCALL_TOKEN` | `oncall-dev-token` | Token with read and action access |
| `HOST` | `127.0.0.1` | Gateway bind address |
| `PORT` | `8000` | Gateway port |
| `GATEWAY_URL` | `http://localhost:8000/mcp` | MCP endpoint used by the agent |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Ollama model used for investigation |
| `OLLAMA_TIMEOUT_SECONDS` | `60` | Maximum wait for one model response |
| `TOOL_TIMEOUT_SECONDS` | `30` | Maximum wait for one MCP tool call |
| `MAX_TOOL_CALLS` | `12` | Maximum tool calls in one investigation |

Do not use the default tokens outside a local development environment.

## Usage reference

The repository exposes three main entry points:

```text
python -m sim.generate --scenario <scenario>
python -m servers.gateway
python -m agent.agent "<incident description>"
```

The gateway serves MCP at `/mcp`. The agent uses the on-call token by default,
while the evaluation harness uses the viewer token to verify that investigation
does not require action privileges. Docker Compose provides the same gateway
service as a containerized local deployment. Each command-line investigation
prints its report and creates a file named
`reports/incident-report-YYYYMMDD-HHMMSS-microseconds.pdf`.

## Evaluation and tests

[`evals/run_evals.py`](evals/run_evals.py) runs each scenario three times and
scores three properties separately:

- root-cause keywords are present;
- required evidence groups, such as a deployment version and an error signal,
  are cited;
- no forbidden action tool is called while using the viewer token.

This is still a lightweight evaluator, not a human-quality judge. Results are
written to [`evals/results.md`](evals/results.md).

The latest recorded baseline used `qwen2.5:7b` with three runs per scenario:

| Scenario | Correct | Avg tool calls |
|---|---:|---:|
| `bad_deploy` | 2/3 | 6.0 |
| `memory_leak` | 3/3 | 3.0 |
| `db_pool_exhaustion` | 3/3 | 3.0 |
| `upstream_timeout` | 1/3 | 3.0 |
| `disk_full` | 3/3 | 3.0 |
| **Overall** | **80%** | |

These numbers are the keyword-based baseline recorded before the evidence
scoring was added. Re-run the evaluator to produce the expanded root-cause,
evidence, safety, and quality columns.

## Example output

See [`reports/sample-incident-report.md`](reports/sample-incident-report.md) for
a representative investigation report. The CLI also creates a formatted PDF
with the same sections in the `reports/` directory.

The test suite covers:

- observation validation and query behavior;
- action approval and audit logging;
- gateway authentication and role enforcement;
- prompt-injection handling;
- the agent's investigation behavior.

## Continuous integration

The project uses GitHub Actions through
[`.github/workflows/ci.yml`](.github/workflows/ci.yml).
The `CI` workflow runs on every push and pull request and:

1. Checks out the repository.
2. Sets up Python 3.12.
3. Installs the project and development dependencies.
4. Runs the complete test suite with `pytest -q`.
5. Builds the Docker Compose image to verify the container configuration.

## Repository layout

```text
incident-triage-copilot/
├── .github/
│   └── workflows/
│       └── ci.yml         # GitHub Actions tests and Docker build
├── agent/
│   └── agent.py          # Ollama investigation loop
├── data/
│   └── prod.db           # Simulated production database
├── reports/              # Generated PDF incident reports
│   └── sample-incident-report.md
├── evals/
│   ├── results.md        # Latest evaluation output
│   └── run_evals.py      # Scenario evaluation harness
├── servers/
│   ├── actions.py        # Approval-gated simulated operations
│   ├── gateway.py        # MCP gateway and security middleware
│   └── observe.py        # Read-only observability tools
├── sim/
│   └── generate.py       # Incident data generator
├── tests/                # Unit and integration tests
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

## Limitations and future improvements

- Static bearer tokens are development credentials, not a production identity
  system.
- All infrastructure and actions are simulated; no real services are changed.
- Local models can vary in tool-calling reliability and report quality.
- Keyword-based evaluation does not measure factual completeness or severity
  assessment.
- A production version would need durable audit storage, stronger tenancy
  isolation, secret management, observability for the agent itself, and a
  richer evaluation rubric.

## License

This project is provided for demonstration and experimentation.
