Pipeline

PipelineParams
==============

Configure pipeline execution with PipelineParams

[​

](#overview)

Overview
----------------------------

The `PipelineParams` class provides a structured way to configure various aspects of pipeline execution. These parameters control behaviors like audio settings, metrics collection, heartbeat monitoring, and interruption handling.

[​

](#basic-usage)

Basic Usage
----------------------------------

Copy

Ask AI

    from pipecat.pipeline.task import PipelineParams, PipelineTask
    
    # Create with default parameters
    params = PipelineParams()
    
    # Or customize specific parameters
    params = PipelineParams(
        allow_interruptions=True,
        audio_in_sample_rate=16000,
        enable_metrics=True
    )
    
    # Pass to PipelineTask
    pipeline = Pipeline([...])
    task = PipelineTask(pipeline, params=params)
    

[​

](#available-parameters)

Available Parameters
----------------------------------------------------

[​

](#param-allow-interruptions)

allow\_interruptions

bool

default:"False"

Whether to allow pipeline interruptions. When enabled, a user’s speech will immediately interrupt the bot’s response.

[​

](#param-audio-in-sample-rate)

audio\_in\_sample\_rate

int

default:"16000"

Input audio sample rate in Hz.

Setting the `audio_in_sample_rate` as a `PipelineParam` sets the input sample rate for all corresponding services in the pipeline.

[​

](#param-audio-out-sample-rate)

audio\_out\_sample\_rate

int

default:"24000"

Output audio sample rate in Hz.

Setting the `audio_out_sample_rate` as a `PipelineParam` sets the output sample rate for all corresponding services in the pipeline.

[​

](#param-enable-heartbeats)

enable\_heartbeats

bool

default:"False"

Whether to enable heartbeat monitoring to detect pipeline stalls. See [Heartbeats](/server/pipeline/heartbeats) for details.

[​

](#param-heartbeats-period-secs)

heartbeats\_period\_secs

float

default:"1.0"

Period between heartbeats in seconds (when heartbeats are enabled).

[​

](#param-enable-metrics)

enable\_metrics

bool

default:"False"

Whether to enable metrics collection for pipeline performance.

[​

](#param-enable-usage-metrics)

enable\_usage\_metrics

bool

default:"False"

Whether to enable usage metrics tracking.

[​

](#param-report-only-initial-ttfb)

report\_only\_initial\_ttfb

bool

default:"False"

Whether to report only initial time to first byte metric.

[​

](#param-send-initial-empty-metrics)

send\_initial\_empty\_metrics

bool

default:"True"

Whether to send initial empty metrics frame at pipeline start.

[​

](#param-start-metadata)

start\_metadata

Dict\[str, Any\]

default:"{}"

Additional metadata to include in the StartFrame.

[​

](#common-configurations)

Common Configurations
------------------------------------------------------

### 

[​

](#audio-processing-configuration)

Audio Processing Configuration

You can set the audio input and output sample rates in the `PipelineParams` to set the sample rate for all input and output services in the pipeline. This acts as a convenience to avoid setting the sample rate for each service individually. Note, if services are set individually, they will supersede the values set in `PipelineParams`.

Copy

Ask AI

    params = PipelineParams(
        audio_in_sample_rate=8000,   # Lower quality input audio
        audio_out_sample_rate=8000  # High quality output audio
    )
    

### 

[​

](#performance-monitoring-configuration)

Performance Monitoring Configuration

Pipeline heartbeats provide a way to monitor the health of your pipeline by sending periodic heartbeat frames through the system. When enabled, the pipeline will send heartbeat frames every second and monitor their progress through the pipeline.

Copy

Ask AI

    params = PipelineParams(
        enable_heartbeats=True,
        heartbeats_period_secs=2.0,  # Send heartbeats every 2 seconds
        enable_metrics=True
    )
    

[​

](#how-parameters-are-used)

How Parameters Are Used
----------------------------------------------------------

The parameters you set in `PipelineParams` are passed to various components of the pipeline:

1.  **StartFrame**: Many parameters are included in the StartFrame that initializes the pipeline
2.  **Metrics Collection**: Metrics settings configure what performance data is gathered
3.  **Heartbeat Monitoring**: Controls the pipeline’s health monitoring system
4.  **Audio Processing**: Sample rates affect how audio is processed throughout the pipeline

[​

](#complete-example)

Complete Example
--------------------------------------------

Copy

Ask AI

    from pipecat.frames.frames import TTSSpeakFrame
    from pipecat.observers.file_observer import FileObserver
    from pipecat.pipeline.task import PipelineParams, PipelineTask
    from pipecat.pipeline.runner import PipelineRunner
    
    # Create comprehensive parameters
    params = PipelineParams(
        allow_interruptions=True,
        audio_in_sample_rate=8000,
        audio_out_sample_rate=8000,
        enable_heartbeats=True,
        enable_metrics=True,
        enable_usage_metrics=True,
        heartbeats_period_secs=1.0,
        report_only_initial_ttfb=False,
        start_metadata={
            "conversation_id": "conv-123",
            "session_data": {
                "user_id": "user-456",
                "start_time": "2023-10-25T14:30:00Z"
            }
        }
    )
    
    # Create pipeline and task
    pipeline = Pipeline([...])
    task = PipelineTask(
        pipeline,
        params=params,
        observers=[FileObserver("pipeline_logs.jsonl")]
    )
    
    # Run the pipeline
    runner = PipelineRunner()
    await runner.run(task)
    

[​

](#additional-information)

Additional Information
--------------------------------------------------------

*   Parameters are immutable once the pipeline starts
*   The `start_metadata` dictionary can contain any serializable data
*   For metrics collection to work properly, `enable_metrics` must be set to `True`


