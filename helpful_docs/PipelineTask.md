Pipeline

PipelineTask
============

Manage pipeline execution and lifecycle with PipelineTask

[​

](#overview)

Overview
----------------------------

`PipelineTask` is the central class for managing pipeline execution. It handles the lifecycle of the pipeline, processes frames in both directions, manages task cancellation, and provides event handlers for monitoring pipeline activity.

[​

](#basic-usage)

Basic Usage
----------------------------------

Copy

Ask AI

    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.runner import PipelineRunner
    from pipecat.pipeline.task import PipelineParams, PipelineTask
    
    # Create a pipeline
    pipeline = Pipeline([...])
    
    # Create a task with the pipeline
    task = PipelineTask(pipeline)
    
    # Queue frames for processing
    await task.queue_frame(TTSSpeakFrame("Hello, how can I help you today?"))
    
    # Run the pipeline
    runner = PipelineRunner()
    await runner.run(task)
    

[​

](#constructor-parameters)

Constructor Parameters
--------------------------------------------------------

[​

](#param-pipeline)

pipeline

BasePipeline

required

The pipeline to execute.

[​

](#param-params)

params

PipelineParams

default:"PipelineParams()"

Configuration parameters for the pipeline. See [PipelineParams](/server/pipeline/pipeline-params) for details.

[​

](#param-observers)

observers

List\[BaseObserver\]

default:"\[\]"

List of observers for monitoring pipeline execution. See [Observers](/server/utilities/observers/observer-pattern) for details.

[​

](#param-clock)

clock

BaseClock

default:"SystemClock()"

Clock implementation for timing operations.

[​

](#param-task-manager)

task\_manager

Optional\[BaseTaskManager\]

default:"None"

Custom task manager for handling asyncio tasks. If None, a default TaskManager is used.

[​

](#param-check-dangling-tasks)

check\_dangling\_tasks

bool

default:"True"

Whether to check for processors’ tasks finishing properly.

[​

](#param-idle-timeout-secs)

idle\_timeout\_secs

Optional\[float\]

default:"300"

Timeout in seconds before considering the pipeline idle. Set to None to disable idle detection. See [Pipeline Idle Detection](/server/pipeline/pipeline-idle-detection) for details.

[​

](#param-idle-timeout-frames)

idle\_timeout\_frames

Tuple\[Type\[Frame\], ...\]

default:"(BotSpeakingFrame, LLMFullResponseEndFrame)"

Frame types that should prevent the pipeline from being considered idle. See [Pipeline Idle Detection](/server/pipeline/pipeline-idle-detection) for details.

[​

](#param-cancel-on-idle-timeout)

cancel\_on\_idle\_timeout

bool

default:"True"

Whether to automatically cancel the pipeline task when idle timeout is reached. See [Pipeline Idle Detection](/server/pipeline/pipeline-idle-detection) for details.

[​

](#param-enable-tracing)

enable\_tracing

bool

default:"False"

Whether to enable OpenTelemetry tracing. See [The OpenTelemetry guide](/server/utilities/opentelemetry) for details.

[​

](#param-enable-turn-tracking)

enable\_turn\_tracking

bool

default:"False"

Whether to enable turn tracking. See [The OpenTelemetry guide](/server/utilities/opentelemetry) for details.

[​

](#param-conversation-id)

conversation\_id

Optional\[str\]

default:"None"

Custom ID for the conversation. If not provided, a UUID will be generated. See [The OpenTelemetry guide](/server/utilities/opentelemetry) for details.

[​

](#param-additional-span-attributes)

additional\_span\_attributes

Optional\[dict\]

default:"None"

Any additional attributes to add to top-level OpenTelemetry conversation span. See [The OpenTelemetry guide](/server/utilities/opentelemetry) for details.

[​

](#methods)

Methods
--------------------------

### 

[​

](#task-lifecycle-management)

Task Lifecycle Management

[​

](#param-run)

run()

async

Starts and manages the pipeline execution until completion or cancellation.

Copy

Ask AI

    await task.run()
    

[​

](#param-stop-when-done)

stop\_when\_done()

async

Sends an EndFrame to the pipeline to gracefully stop the task after all queued frames have been processed.

Copy

Ask AI

    await task.stop_when_done()
    

[​

](#param-cancel)

cancel()

async

Stops the running pipeline immediately by sending a CancelFrame.

Copy

Ask AI

      await task.cancel()
    

[​

](#param-has-finished)

has\_finished()

bool

Returns whether the task has finished (all processors have stopped).

Copy

Ask AI

    if task.has_finished(): print("Task is complete")
    

### 

[​

](#frame-management)

Frame Management

[​

](#param-queue-frame)

queue\_frame()

async

Queues a single frame to be pushed down the pipeline.

Copy

Ask AI

    await task.queue_frame(TTSSpeakFrame("Hello!"))
    

[​

](#param-queue-frames)

queue\_frames()

async

Queues multiple frames to be pushed down the pipeline.

Copy

Ask AI

    frames = [TTSSpeakFrame("Hello!"), TTSSpeakFrame("How are you?")]
    
    await task.queue_frames(frames)
    
    

[​

](#event-handlers)

Event Handlers
----------------------------------------

PipelineTask provides an event handler that can be registered using the `event_handler` decorator:

### 

[​

](#on-idle-timeout)

on\_idle\_timeout

Triggered when no activity frames (as specified by `idle_timeout_frames`) have been received within the idle timeout period.

Copy

Ask AI

    @task.event_handler("on_idle_timeout")
    async def on_idle_timeout(task):
        print("Pipeline has been idle too long")
        await task.queue_frame(TTSSpeakFrame("Are you still there?"))
    

Assistant

Responses are generated using AI and may contain mistakes.

[PipelineParams](/server/pipeline/pipeline-params)[Pipeline Idle Detection](/server/pipeline/pipeline-idle-detection)

[x](https://x.com/pipecat_ai)[github](https://github.com/pipecat-ai/pipecat)[discord](https://discord.gg/pipecat)

[Powered by Mintlify](https://mintlify.com/preview-request?utm_campaign=poweredBy&utm_medium=referral&utm_source=daily)
