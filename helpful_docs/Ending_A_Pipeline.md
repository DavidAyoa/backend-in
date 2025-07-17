Fundamentals

Ending a Pipeline
=================

Best practices for properly terminating Pipecat pipelines

[​

](#overview)

Overview
----------------------------

Properly ending a Pipecat pipeline is essential to prevent hanging processes and ensure clean shutdown of your session and related infrastructure. This guide covers different approaches to pipeline termination and provides best practices for each scenario.

[​

](#shutdown-approaches)

Shutdown Approaches
--------------------------------------------------

Pipecat provides two primary methods for shutting down a pipeline:

1.  **Graceful Shutdown**: Allows completion of in-progress processing before termination
2.  **Immediate Shutdown**: Cancels all tasks immediately

Each approach is designed for different use cases, as detailed below.

[​

](#graceful-shutdown)

Graceful Shutdown
----------------------------------------------

A graceful shutdown is ideal when you want the bot to properly end a conversation. For example, you might want to terminate a session after the bot has completed a specific task or reached a natural conclusion.

This approach ensures that any final messages from the bot are processed and delivered before the pipeline terminates.

### 

[​

](#implementation)

Implementation

To implement a graceful shutdown, there are two options:

*   Push an `EndFrame` from outside your pipeline using the pipeline task:

Copy

Ask AI

    await task.queue_frame(EndFrame())
    

*   Push an `EndTaskFrame` upstream from inside your pipeline. For example, inside a function call:

Copy

Ask AI

    async def end_conversation(params: FunctionCallParams):
        await params.llm.push_frame(TTSSpeakFrame("Have a nice day!"))
    
        # Signal that the task should end after processing this frame
        await params.llm.push_frame(EndTaskFrame(), FrameDirection.UPSTREAM)
    

### 

[​

](#how-graceful-shutdown-works)

How Graceful Shutdown Works

In both cases, an `EndFrame` is pushed downstream from the beginning of the pipeline:

1.  `EndFrame`s are queued, so they’ll process after any pending frames (like goodbye messages)
2.  All processors in the pipeline will shutdown when processing the `EndFrame`
3.  Once the `EndFrame` reaches the sink of the `PipelineTask`, the Pipeline is ready to shut down
4.  The Pipecat processor terminates and related resources are released

Graceful shutdowns allow your bot to say goodbye and complete any final actions before terminating.

[​

](#immediate-shutdown)

Immediate Shutdown
------------------------------------------------

An immediate shutdown is appropriate when the human participant is no longer active in the conversation. For example:

*   In a client/server app, when the user closes the browser tab or ends the session
*   In a phone call, when the user hangs up
*   When an error occurs that requires immediate termination

In these scenarios, there’s no value in having the bot complete its current turn.

### 

[​

](#implementation-2)

Implementation

To implement an immediate shutdown, you can use event handlers to, for example, detect disconnections and then push a `CancelFrame`:

Copy

Ask AI

    @transport.event_handler("on_client_closed")
    async def on_client_closed(transport, client):
        logger.info(f"Client closed connection")
        await task.cancel()
    

### 

[​

](#how-immediate-shutdown-works)

How Immediate Shutdown Works

1.  An event triggers the cancellation (like a client disconnection)
2.  `task.cancel()` is called, which pushes a `CancelFrame` downstream from the `PipelineTask`
3.  `CancelFrame`s are `SystemFrame`s and are not queued
4.  Processors that handle the `CancelFrame` immediate shutdown and push the frame downstream
5.  Once the `CancelFrame` reaches the sink of the `PipelineTask`, the Pipeline is ready to shut down

Immediate shutdowns will discard any pending frames in the pipeline. Use this approach when completing the conversation is no longer necessary.

[​

](#pipeline-idle-detection)

Pipeline Idle Detection
----------------------------------------------------------

In addition to the two explicit shutdown mechanisms, Pipecat includes a backup mechanism to prevent hanging pipelines—Pipeline Idle Detection.

This feature monitors activity in your pipeline and can automatically cancel tasks when no meaningful bot interactions are occurring for an extended period. It serves as a safety net to conditionally terminate the pipeline if anomalous behavior occurs.

Pipeline Idle Detection is enabled by default and helps prevent resources from being wasted on inactive conversations.

For more information on configuring and customizing this feature, see the [Pipeline Idle Detection](/server/pipeline/pipeline-idle-detection) documentation.

[​

](#best-practices)

Best Practices
----------------------------------------

*   **Use graceful shutdowns** when you want to let the bot complete its conversation
*   **Use immediate shutdowns** when the human participant has already disconnected
*   **Implement error handling** to ensure pipelines can terminate even when exceptions occur
*   **Configure idle detection timeouts** appropriate for your use case

By following these practices, you’ll ensure that your Pipecat pipelines terminate properly and efficiently, preventing resource leaks and improving overall system reliability.

Assistant

Responses are generated using AI and may contain mistakes.

[Detecting Idle Users](/guides/fundamentals/detecting-user-idle)[Function Calling](/guides/fundamentals/function-calling)

[x](https://x.com/pipecat_ai)[github](https://github.com/pipecat-ai/pipecat)[discord](https://discord.gg/pipecat)

[Powered by Mintlify](https://mintlify.com/preview-request?utm_campaign=poweredBy&utm_medium=referral&utm_source=daily)
