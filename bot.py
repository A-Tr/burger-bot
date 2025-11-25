"""Burger Joint Voice Agent.

A Pipecat voice agent that acts as a burger joint employee, taking meal orders
from customers via voice interaction.

Required AI services:
- Deepgram (Speech-to-Text)
- OpenAI (LLM)
- Cartesia (Text-to-Speech)

Run the bot using::

    uv run bot.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

logger.remove(0)
logger.add(sys.stderr, level="INFO")
print("🚀 Starting Burger Joint bot...")
print("⏳ Loading models and imports (20 seconds, first run only)\n")

logger.info("Loading Local Smart Turn Analyzer V3...")
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3

logger.info("✅ Local Smart Turn Analyzer V3 loaded")
logger.info("Loading Silero VAD model...")
from pipecat.audio.vad.silero import SileroVADAnalyzer

logger.info("✅ Silero VAD model loaded")

from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import LLMRunFrame, TranscriptionUpdateFrame
from pipecat.processors.transcript_processor import TranscriptProcessor

logger.info("Loading pipeline components...")
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.services.cartesia.tts import CartesiaTTSService, GenerationConfig
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.google.llm import GoogleLLMService
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.daily.transport import DailyParams

from functions.order_operations import (
    CalculateOrderTotalFunction,
    CreateOrderFunction,
)
from functions.state_operations import (
    AddItemToOrderFunction,
    ReadCurrentOrderFunction,
    RemoveItemFromOrderFunction,
)
from models.session_state import SessionState
from services.burger_api import BurgerAPIClient

logger.info("✅ All components loaded successfully!")

load_dotenv(override=True)


def format_catalog_for_prompt(catalog_items):
    """Format catalog items for inclusion in system prompt."""
    lines = []
    current_category = None

    for item in catalog_items:
        if item.category != current_category:
            current_category = item.category
            category_name = current_category.capitalize() + "s"
            lines.append(f"\n{category_name}:")
        lines.append(f"  {item.name} (ID: {item.id}) - ${item.price:.2f}")
        lines.append(f"    {item.description}")

    return "\n".join(lines)


def load_system_prompt(catalog_items):
    """Load and format the system prompt with catalog."""
    prompt_path = Path(__file__).parent / "prompts" / "conversation_prompt.md"
    with open(prompt_path, "r") as f:
        prompt_template = f.read()

    catalog_text = format_catalog_for_prompt(catalog_items)
    return prompt_template.format(catalog_text=catalog_text)


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    """Run the burger joint bot."""
    logger.info("Starting burger joint bot")

    # Initialize API client
    api_client = BurgerAPIClient()

    # Fetch catalog
    try:
        catalog = await api_client.get_catalog()
        logger.info(f"Loaded {len(catalog)} items from catalog")
    except Exception as e:
        logger.error(f"Failed to load catalog: {e}")
        raise

    # Initialize session state
    session_state = SessionState()

    # Initialize services
    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))

    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        voice_id="79f8b5fb-2cc8-479a-80df-29f7a7cf1a3e",
        model="sonic-3",
        params=CartesiaTTSService.InputParams(
            generation_config=GenerationConfig(
                speed=1.3,
            ),
        ),
    )

    llm = GoogleLLMService(api_key=os.getenv("GOOGLE_API_KEY"), model="gemini-2.5-flash")

    # Load system prompt
    system_prompt = load_system_prompt(catalog)

    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
    ]

    # Create function instances
    add_item_function = AddItemToOrderFunction(session_state, catalog)
    remove_item_function = RemoveItemFromOrderFunction(session_state)
    read_order_function = ReadCurrentOrderFunction(session_state)
    calculate_total_function = CalculateOrderTotalFunction(session_state)
    create_order_function = CreateOrderFunction(session_state, api_client)

    # Collect all functions
    agent_functions = [
        add_item_function,
        remove_item_function,
        read_order_function,
        calculate_total_function,
        create_order_function,
    ]

    # Create tools schema from function schemas
    tools = ToolsSchema(standard_tools=[func.get_schema() for func in agent_functions])

    # Create context with tools
    context = LLMContext(messages, tools)
    context_aggregator = LLMContextAggregatorPair(context)

    # Register all functions with LLM
    for func in agent_functions:
        llm.register_function(func.name, func.get_handler())

    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))
    transcript_processor = TranscriptProcessor()

    pipeline = Pipeline(
        [
            transport.input(),  # Transport user input
            rtvi,  # RTVI processor
            stt,
            context_aggregator.user(),  # User responses
            llm,  # LLM
            tts,  # TTS
            transport.output(),  # Transport bot output
            context_aggregator.assistant(),  # Assistant spoken responses
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        observers=[RTVIObserver(rtvi)],
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Client connected")
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Client disconnected")
        await api_client.close()
        await task.cancel()

    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)

    try:
        await runner.run(task)
    finally:
        await api_client.close()


async def bot(runner_args: RunnerArguments):
    """Main bot entry point."""
    transport_params = {
        "daily": lambda: DailyParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            video_in_enabled=False,
            video_out_enabled=False,
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
            turn_analyzer=LocalSmartTurnAnalyzerV3(),
        ),
        "webrtc": lambda: TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            video_in_enabled=False,
            video_out_enabled=False,
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
            turn_analyzer=LocalSmartTurnAnalyzerV3(),
        ),
    }

    transport = await create_transport(runner_args, transport_params)

    await run_bot(transport, runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
