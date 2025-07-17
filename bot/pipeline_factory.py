#!/usr/bin/env python3
"""
Pipeline factory for creating Pipecat pipelines with different transports
"""

import os
from typing import Optional

import structlog
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask, PipelineParams
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.aggregators.llm_response import LLMAssistantContextAggregator, LLMUserContextAggregator
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.google.tts import GoogleTTSService
from pipecat.services.google.stt import GoogleSTTService
from pipecat.transports.base_transport import BaseTransport
from pipecat.audio.interruptions.min_words_interruption_strategy import MinWordsInterruptionStrategy

from transports.base import TransportConfig
from core.service_pool import ServicePool

logger = structlog.get_logger()


async def create_pipeline(
    transport: BaseTransport,
    context: OpenAILLMContext,
    config: TransportConfig,
    service_pool: Optional[ServicePool] = None
) -> Pipeline:
    """
    Create a Pipecat pipeline with the specified transport and configuration
    """
    
    # Get services from pool or create new ones
    if service_pool:
        stt = await service_pool.get_stt_service()
        llm = await service_pool.get_llm_service()
        tts = await service_pool.get_tts_service()
    else:
        # Create services directly
        stt = GoogleSTTService(
            api_key=os.getenv("GOOGLE_API_KEY"),
            language=os.getenv("GOOGLE_STT_LANGUAGE", "en-US"),
            model=os.getenv("GOOGLE_STT_MODEL", "latest_long")
        )
        
        llm = OpenAILLMService(
            api_key=os.getenv("OPENAI_API_KEY"),
            model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        )
        
        tts = GoogleTTSService(
            api_key=os.getenv("GOOGLE_API_KEY"),
            voice_id=os.getenv("GOOGLE_TTS_VOICE", "en-US-Standard-A"),
            sample_rate=config.sample_rate
        )
    
    # Create context aggregators
    user_context_aggregator = LLMUserContextAggregator(context)
    assistant_context_aggregator = LLMAssistantContextAggregator(context)
    
    # Setup interruption strategy if enabled
    interruption_strategy = None
    if config.enable_interruptions:
        interruption_strategy = MinWordsInterruptionStrategy(min_words=1)
    
    # Create pipeline based on transport type
    if hasattr(transport, 'input') and hasattr(transport, 'output'):
        # Standard transport with input/output methods
        pipeline_components = [
            transport.input(),              # Audio input from client
            stt,                           # Speech-to-text
            user_context_aggregator,       # Add user message to context
            llm,                           # Language model processing
            tts,                           # Text-to-speech
            transport.output(),            # Audio output to client
            assistant_context_aggregator   # Add assistant response to context
        ]
    else:
        # Fallback pipeline structure
        pipeline_components = [
            stt,                           # Speech-to-text
            user_context_aggregator,       # Add user message to context
            llm,                           # Language model processing
            tts,                           # Text-to-speech
            assistant_context_aggregator   # Add assistant response to context
        ]
    
    # Create pipeline
    pipeline = Pipeline(pipeline_components)
    
    # Setup interruption handling
    if interruption_strategy:
        pipeline.set_interruption_strategy(interruption_strategy)
    
    logger.info(
        "Pipeline created",
        transport_type=config.transport_type.value,
        components_count=len(pipeline_components),
        interruptions_enabled=config.enable_interruptions
    )
    
    return pipeline


async def create_pipeline_task(
    pipeline: Pipeline,
    transport: BaseTransport,
    config: TransportConfig
) -> PipelineTask:
    """
    Create a pipeline task for running the pipeline
    """
    
    # Create pipeline parameters
    params = PipelineParams(
        allow_interruptions=config.enable_interruptions,
        enable_metrics=True,
        enable_usage_metrics=True,
    )
    
    # Create task
    task = PipelineTask(pipeline, params=params)
    
    logger.info(
        "Pipeline task created",
        transport_type=config.transport_type.value,
        interruptions_allowed=config.enable_interruptions
    )
    
    return task


async def create_pipeline_runner(
    task: PipelineTask,
    transport: BaseTransport,
    config: TransportConfig
) -> PipelineRunner:
    """
    Create a pipeline runner for the task
    """
    
    # Create runner
    runner = PipelineRunner()
    
    logger.info(
        "Pipeline runner created",
        transport_type=config.transport_type.value
    )
    
    return runner


async def create_full_pipeline_setup(
    transport: BaseTransport,
    context: OpenAILLMContext,
    config: TransportConfig,
    service_pool: Optional[ServicePool] = None
) -> tuple[Pipeline, PipelineTask, PipelineRunner]:
    """
    Create a complete pipeline setup with pipeline, task, and runner
    """
    
    # Create pipeline
    pipeline = await create_pipeline(transport, context, config, service_pool)
    
    # Create task
    task = await create_pipeline_task(pipeline, transport, config)
    
    # Create runner
    runner = await create_pipeline_runner(task, transport, config)
    
    logger.info(
        "Full pipeline setup created",
        transport_type=config.transport_type.value
    )
    
    return pipeline, task, runner
