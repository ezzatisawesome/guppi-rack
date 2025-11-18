# Lab Server

Python FastAPI service for running test flows and controlling instruments.

## Features

- **Test Flow DSL**: Define test flows using the `@test_flow` decorator
- **Instrument Drivers**: Control instruments (PSUs, ELOADs, etc.) via PyVISA
  - Generic PSU driver for multi-channel power supplies
  - BK9131B driver for BK Precision 9131B power supply (0-32V, 0-3.1A, single channel)
  - BK9200 series driver for BK Precision 9200 series power supplies:
    - BK9200: Single channel (0-60V, 0-3A)
    - BK9201: Single channel (0-60V, 0-5A)
    - BK9202: Dual channel (0-60V, 0-3A per channel)
    - BK9203: Triple channel (0-60V, 0-3A per channel)
    - BK9204: Quad channel (0-60V, 0-3A per channel)
- **Git Sync**: Automatically pull and reload test flows from git repository
- **App Server Integration**: Push telemetry and events to App Server
- **Manual Control**: Execute manual instrument commands via API

## Project Structure

```
lab-server/
├── src/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── flow_dsl.py          # @test_flow decorator
│   ├── flow_registry.py     # Flow discovery and registry
│   ├── git_sync.py          # Git pull and reload service
│   ├── app_server_client.py # HTTP client for App Server
│   ├── drivers/             # Instrument drivers
│   │   ├── base.py          # Base driver interface
│   │   └── psu/             # Power Supply Unit drivers
│   │       ├── __init__.py  # PSU drivers package
│   │       ├── base.py      # Base PSU driver class
│   │       ├── generic.py   # Generic PSU driver implementation
│   │       ├── bk9131b.py   # BK9131B power supply driver
│   │       └── bk9200.py    # BK9200 series power supply driver
│   └── runtime/             # Test execution engine
│       ├── context.py       # Execution context
│       └── executor.py      # Flow executor
├── tests/                   # Test flows directory
│   └── example_flows.py     # Example test flows
├── requirements.txt
├── Dockerfile
└── .env.example
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables (see `.env.example`)

3. Run the server:
```bash
python -m src.main
```

Or using uvicorn directly:
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

## Configuration

Create a `.env` file based on `.env.example`:

```env
# Git Configuration
GIT_REPO_URL=https://github.com/your-org/test-flows.git
GIT_BRANCH=main
GIT_SYNC_INTERVAL=60

# App Server Configuration
APP_SERVER_URL=http://localhost:3000

# Server Configuration
HOST=0.0.0.0
PORT=8000

# Telemetry Batching
TELEMETRY_BATCH_SIZE=100
TELEMETRY_BATCH_INTERVAL=1.0

# Rig Configurations (JSON format)
# For generic PSU:
# RIG_CONFIGS={"rig1": {"psu": {"type": "power_supply", "resource_string": "USB0::0xFFFF::0x9130::802360043766810027::INSTR"}}}
# For BK9131B:
# RIG_CONFIGS={"rig1": {"psu": {"type": "bk9131b", "resource_string": "USB0::0xXXXX::0xYYYY::SNZZZZ::INSTR"}}}
# For BK9200 series (single channel):
# RIG_CONFIGS={"rig1": {"psu": {"type": "bk9200", "resource_string": "USB0::0xXXXX::0xYYYY::SNZZZZ::INSTR", "max_channels": 1}}}
# For BK9202 (dual channel):
# RIG_CONFIGS={"rig1": {"psu": {"type": "bk9200", "resource_string": "USB0::0xXXXX::0xYYYY::SNZZZZ::INSTR", "max_channels": 2}}}
# Or auto-detect by model:
# RIG_CONFIGS={"rig1": {"psu": {"type": "power_supply", "model": "BK9202", "resource_string": "USB0::0xXXXX::0xYYYY::SNZZZZ::INSTR"}}}
```

## Writing Test Flows

Test flows are defined using the `@test_flow` decorator:

```python
from lab_server.src.flow_dsl import test_flow

@test_flow(
    name="my_test",
    dut_model="MyDUT",
    resource_roles={"psu": "power_supply"}
)
async def my_test(context, params):
    # Get instrument
    psu = await context.get_instrument("psu")
    
    # Configure and control
    await psu.set_voltage(params["voltage"])
    await psu.enable_output(True)
    
    # Emit telemetry
    voltage = await psu.read_voltage()
    await context.emit_telemetry("voltage", voltage, {"unit": "V"})
    
    # Emit events
    await context.emit_event("info", "Test completed")
    
    return {"status": "passed"}
```

## API Endpoints

### Health Check
- `GET /health` - Health check endpoint

### Flow Management
- `GET /internal/flows` - List all available test flows

### Test Execution
- `POST /internal/run` - Execute a test flow
  ```json
  {
    "testRunId": "run_123",
    "flowId": "power_up_smoke",
    "rigId": "rig1",
    "dutId": "SN-12345",
    "params": {"input_voltage": 12.0}
  }
  ```

### Manual Commands
- `POST /internal/manual` - Execute manual instrument command
  ```json
  {
    "rigId": "rig1",
    "command": "set_voltage",
    "params": {"voltage": 5.0}
  }
  ```
  
  Supported commands:
  - `set_voltage` - Set output voltage
  - `set_current` - Set current limit
  - `enable_output` - Enable/disable output
  - `read_voltage` - Read measured voltage
  - `read_current` - Read measured current
  - `read_voltage_setpoint` - Read voltage setpoint
  - `read_current_setpoint` - Read current setpoint
  - `is_output_enabled` - Check output state
  - `read_power` - Read measured power (BK9131B and BK9200 series)
  - `read_all_channels` - Read all channels at once (BK9200 series multi-channel only)
  - `enable_all_outputs` - Enable/disable all outputs (BK9200 series multi-channel only)
  - `write` - Send raw SCPI command
  - `query` - Send raw SCPI query

## Docker

Build the Docker image:
```bash
docker build -t lab-server .
```

Run the container:
```bash
docker run -p 8000:8000 --env-file .env lab-server
```

## Development

The Lab Server automatically:
1. Loads test flows from the `tests/` directory on startup
2. Pulls test flows from git (if configured) and reloads them periodically
3. Announces available flows to the App Server
4. Streams telemetry and events to the App Server during test execution

# orbis-rack
