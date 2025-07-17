Pipeline

Pipeline Idle Detection
=======================

Automatically detect and handle idle pipelines with no bot activity

[​

](#overview)

Overview
----------------------------

Pipeline idle detection is a feature that monitors activity in your pipeline and can automatically cancel tasks when no meaningful bot interactions are occurring. This helps prevent pipelines from running indefinitely when a conversation has naturally ended but wasn’t properly terminated.

[​

](#how-it-works)

How It Works
------------------------------------

The system monitors specific “activity frames” that indicate the bot is actively engaged in the conversation. By default, these are:

*   `BotSpeakingFrame` - When the bot is speaking
*   `LLMFullResponseEndFrame` - When the LLM has completed a response

If no activity frames are detected within the configured timeout period (5 minutes by default), the system considers the pipeline idle and can automatically terminate it.

Idle detection only starts after the pipeline has begun processing frames. The idle timer resets whenever an activity frame (as specified in `idle_timeout_frames`) is received.

[​

](#configuration)

Configuration
--------------------------------------

You can configure idle detection behavior when creating a `PipelineTask`:

Copy

Ask AI

    from pipecat.pipeline.task import PipelineParams, PipelineTask
    
    # Default configuration - cancel after 5 minutes of inactivity
    task = PipelineTask(pipeline)
    
    # Custom configuration
    task = PipelineTask(
        pipeline,
        params=PipelineParams(allow_interruptions=True),
        idle_timeout_secs=600,  # 10 minute timeout
        idle_timeout_frames=(BotSpeakingFrame,),  # Only monitor bot speaking
        cancel_on_idle_timeout=False,  # Don't auto-cancel, just notify
    )
    

[​

](#configuration-parameters)

Configuration Parameters
------------------------------------------------------------

[​

](#param-idle-timeout-secs)

idle\_timeout\_secs

Optional\[float\]

default:"300"

Timeout in seconds before considering the pipeline idle. Set to `None` to disable idle detection.

[​

](#param-idle-timeout-frames)

idle\_timeout\_frames

Tuple\[Type\[Frame\], ...\]

default:"(BotSpeakingFrame, LLMFullResponseEndFrame)"

Frame types that should prevent the pipeline from being considered idle.

[​

](#param-cancel-on-idle-timeout)

cancel\_on\_idle\_timeout

bool

default:"True"

Whether to automatically cancel the pipeline task when idle timeout is reached.

[​

](#handling-idle-timeouts)

Handling Idle Timeouts
--------------------------------------------------------

You can respond to idle timeout events by adding an event handler:

Copy

Ask AI

    @task.event_handler("on_idle_timeout")
    async def on_idle_timeout(task):
        logger.info("Pipeline has been idle for too long")
        # Perform any custom cleanup or logging
        # Note: If cancel_on_idle_timeout=True, the pipeline will be cancelled after this handler runs
    

[​

](#example-implementation)

Example Implementation
--------------------------------------------------------

Here’s a complete example showing how to configure idle detection with custom handling:

Copy

Ask AI

    from pipecat.frames.frames import BotSpeakingFrame, LLMFullResponseEndFrame, TTSSpeakFrame
    from pipecat.pipeline.runner import PipelineRunner
    from pipecat.pipeline.task import PipelineParams, PipelineTask
    
    # Create pipeline
    pipeline = Pipeline([...])
    
    # Configure task with custom idle settings
    task = PipelineTask(
        pipeline,
        params=PipelineParams(allow_interruptions=True),
        idle_timeout_secs=180,  # 3 minutes
        cancel_on_idle_timeout=False  # Don't auto-cancel
    )
    
    # Add event handler for idle timeout
    @task.event_handler("on_idle_timeout")
    async def on_idle_timeout(task):
        logger.info("Conversation has been idle for 3 minutes")
    
        # Add a farewell message
        await task.queue_frame(TTSSpeakFrame("I haven't heard from you in a while. Goodbye!"))
    
        # Then end the conversation gracefully
        await task.stop_when_done()
    
    runner = PipelineRunner()
    
    await runner.run(task)
    

Assistant

Responses are generated using AI and may contain mistakes.

[PipelineTask](/server/pipeline/pipeline-task)[Pipeline Heartbeats](/server/pipeline/heartbeats)

[x](https://x.com/pipecat_ai)[github](https://github.com/pipecat-ai/pipecat)[discord](https://discord.gg/pipecat)

[Powered by Mintlify](https://mintlify.com/preview-request?utm_campaign=poweredBy&utm_medium=referral&utm_source=daily)
