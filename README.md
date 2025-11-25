# Burger Joint Voice Agent

A Pipecat voice agent that acts as a burger joint employee, taking meal orders from customers via voice interaction. This agent demonstrates function calling patterns with reusable state management functions and session-based order state.

## Features

- Voice-based order taking using Pipecat
- Function calling for cart management (add, remove, read items)
- Session state management for order persistence
- Mock burger joint data for testing and development
- Natural conversation flow with order confirmation

## Prerequisites

- Python 3.13 or later
- [uv](https://docs.astral.sh/uv/getting-started/installation/) package manager
- API keys for:
  - Deepgram (Speech-to-Text)
  - Google Gemini (LLM)
  - Cartesia (Text-to-Speech)

## Setup

1. Install dependencies:

```bash
uv sync
```

2. Configure API keys:

Create a `.env` file in the project root:

```ini
DEEPGRAM_API_KEY=your_deepgram_api_key
GOOGLE_API_KEY=your_google_api_key
CARTESIA_API_KEY=your_cartesia_api_key
```

**Note**: The bot uses built-in mock data for the menu and orders, so no external API server is required.

## Running the Bot

Start the bot:

```bash
uv run bot.py
```

You should see output similar to:

```
🚀 Starting Burger Joint bot...
🚀 WebRTC server starting at http://localhost:7860/client
   Open this URL in your browser to connect!
```

Open [http://localhost:7860/client](http://localhost:7860/client) in your browser and click **Connect** to start talking to the bot.

## How the Pipecat Runner Works

The bot uses Pipecat's runner framework to handle command-line arguments, transport configuration, and async execution. Here's how it works:

### Entry Point

At the bottom of `bot.py`, the entry point uses Pipecat's `main()` function:

```python
if __name__ == "__main__":
    from pipecat.runner.run import main
    main()
```

### Execution Flow

1. **`main()` function** (from `pipecat.runner.run`):
   This method from Pipecat library does the following:
   - Parses command-line arguments (transport type, Daily room URL, WebRTC port, etc.)
   - Creates a `RunnerArguments` object with the parsed configuration
   - Automatically discovers and calls the `bot()` function in the module
   - Handles async execution and lifecycle management

2. **`bot(runner_args: RunnerArguments)` function**:
   - Receives `RunnerArguments` containing transport configuration
   - Defines transport parameters for different transport types (Daily, WebRTC)
   - Creates the appropriate transport using `create_transport()`
   - Calls `run_bot()` with the transport and runner arguments

3. **`run_bot(transport, runner_args)` function**:
   - Initializes services (STT, TTS, LLM)
   - Sets up the pipeline with processors
   - Creates a `PipelineTask` and `PipelineRunner`
   - Registers event handlers for client connections/disconnections
   - Runs the pipeline using `runner.run(task)`

### Transport Configuration

The `bot()` function defines transport parameters for different modes:

- **WebRTC**: Default mode, runs a local WebRTC server (default port 7860)
- **Daily**: Connects to a Daily.co room for voice calls

The runner framework automatically selects the transport based on command-line arguments or defaults to WebRTC.

### Pipeline Execution

The `PipelineRunner` manages the async execution of the pipeline:
- Handles frame processing through the pipeline
- Manages signal handling (SIGINT for graceful shutdown)
- Coordinates between transport, processors, and services
- Ensures proper cleanup when the bot stops

This architecture separates concerns: the runner handles infrastructure (transports, arguments), while your bot code focuses on business logic (services, pipeline, state management).

## Project Structure

```
burger-bot/
├── bot.py                         # Main bot entry point
├── functions/                     # Agent function implementations
│   ├── base.py                   # Base class for agent functions
│   ├── state_operations.py      # Add/remove/read state functions
│   └── order_operations.py      # Calculate price, create order functions
├── models/                        # Data models
│   └── session_state.py         # Pydantic models for session state
├── prompts/                       # Agent prompts
│   └── conversation_prompt.md    # Main conversation prompt with menu
└── services/                      # Service layer
    ├── burger_api.py             # Mock burger API client
    ├── models.py                 # API models (MenuItem, OrderResponse, etc.)
    └── mock_data.py              # Mock menu catalog data
```

## Agent Functions

The bot uses the following functions:

- `add_item_to_order(item_id, quantity)`: Add items to the order
- `remove_item_from_order(item_id, quantity)`: Remove items from the order
- `read_current_order()`: Read back the current order for confirmation
- `calculate_order_total()`: Calculate the total price
- `create_order()`: Finalize and submit the order

## Mock Data

The bot uses built-in mock data that simulates a burger joint menu with:
- Burgers (Classic, Cheeseburger, Bacon Burger, Double Burger)
- Sides (French Fries, Onion Rings, Sweet Potato Fries)  
- Drinks (Coca Cola, Sprite, Iced Tea, Lemonade)

The `BurgerAPIClient` class provides mock implementations of:
- `get_catalog()`: Returns the menu items as Pydantic models
- `create_order()`: Calculates totals and returns a mock order confirmation

## Patterns Demonstrated

1. **Function Calling**: LLM calls functions to manage order state
2. **Pydantic Models**: Type-safe data models for session state and API responses
3. **Session State Management**: Structured state management with validation
4. **State Reading**: Agent reads state to confirm orders
5. **Mock Data Integration**: Clean separation between business logic and data layer

