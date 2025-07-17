LLM

OpenAI
======

Large Language Model services using OpenAI’s chat completion API

[​

](#overview)

Overview
----------------------------

`OpenAILLMService` provides chat completion capabilities using OpenAI’s API, supporting streaming responses, function calling, vision input, and advanced context management for conversational AI applications.

[

API Reference
-------------

Complete API documentation and method details







](https://reference-server.pipecat.ai/en/latest/api/pipecat.services.openai.base_llm.html)[

OpenAI Docs
-----------

Official OpenAI API documentation







](https://platform.openai.com/docs/api-reference/chat)[

Example Code
------------

Function calling example with weather API







](https://github.com/pipecat-ai/pipecat/blob/main/examples/foundational/14-function-calling.py)

[​

](#installation)

Installation
------------------------------------

To use OpenAI services, install the required dependencies:

Copy

Ask AI

    pip install "pipecat-ai[openai]"
    

You’ll also need to set up your OpenAI API key as an environment variable: `OPENAI_API_KEY`.

Get your API key from the [OpenAI Platform](https://platform.openai.com/api-keys).

[​

](#frames)

Frames
------------------------

### 

[​

](#input)

Input

*   `OpenAILLMContextFrame` - OpenAI-specific conversation context
*   `LLMMessagesFrame` - Standard conversation messages
*   `VisionImageRawFrame` - Images for vision model processing
*   `LLMUpdateSettingsFrame` - Runtime model configuration updates

### 

[​

](#output)

Output

*   `LLMFullResponseStartFrame` / `LLMFullResponseEndFrame` - Response boundaries
*   `LLMTextFrame` - Streamed completion chunks
*   `FunctionCallInProgressFrame` / `FunctionCallResultFrame` - Function call lifecycle
*   `ErrorFrame` - API or processing errors

[​

](#function-calling)

Function Calling
--------------------------------------------

[

Function Calling Guide
----------------------

Learn how to implement function calling with standardized schemas, register handlers, manage context properly, and control execution flow in your conversational AI applications.







](/guides/fundamentals/function-calling)

[​

](#context-management)

Context Management
------------------------------------------------

[

Context Management Guide
------------------------

Learn how to manage conversation context, handle message history, and integrate context aggregators for consistent conversational experiences.







](/guides/fundamentals/context-management)

[​

](#usage-example)

Usage Example
--------------------------------------

### 

[​

](#basic-conversation-with-function-calling)

Basic Conversation with Function Calling

Copy

Ask AI

    import os
    from pipecat.services.openai.llm import OpenAILLMService
    from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
    from pipecat.adapters.schemas.function_schema import FunctionSchema
    from pipecat.adapters.schemas.tools_schema import ToolsSchema
    from pipecat.services.llm_service import FunctionCallParams
    
    # Configure the service
    llm = OpenAILLMService(
        model="gpt-4o",
        api_key=os.getenv("OPENAI_API_KEY"),
        params=OpenAILLMService.InputParams(
            temperature=0.7,
        )
    )
    
    # Define function schema
    weather_function = FunctionSchema(
        name="get_weather",
        description="Get current weather information",
        properties={
            "location": {
                "type": "string",
                "description": "City name"
            }
        },
        required=["location"]
    )
    
    # Create tools and context
    tools = ToolsSchema(standard_tools=[weather_function])
    context = OpenAILLMContext(
        messages=[{
            "role": "system",
            "content": "You are a helpful assistant. Keep responses concise."
        }],
        tools=tools
    )
    
    # Register function handler
    async def get_weather_handler(params: FunctionCallParams):
        location = params.arguments.get("location")
        # Call weather API here...
        weather_data = {"temperature": "75°F", "conditions": "sunny"}
        await params.result_callback(weather_data)
    
    llm.register_function("get_weather", get_weather_handler)
    
    # Create context aggregators
    context_aggregator = llm.create_context_aggregator(context)
    
    # Use in pipeline
    pipeline = Pipeline([
        transport.input(),
        stt,
        context_aggregator.user(),    # Handles user messages
        llm,                          # Processes with OpenAI
        tts,
        transport.output(),
        context_aggregator.assistant() # Captures responses
    ])
    

[​

](#metrics)

Metrics
--------------------------

The service provides:

*   **Time to First Byte (TTFB)** - Latency from request to first response token
*   **Processing Duration** - Total request processing time
*   **Token Usage** - Prompt tokens, completion tokens, and total usage

[Learn how to enable Metrics](/guides/features/metrics) in your Pipeline.

[​

](#additional-notes)

Additional Notes
--------------------------------------------

*   **Streaming Responses**: All responses are streamed for low latency
*   **Context Persistence**: Use context aggregators to maintain conversation history
*   **Error Handling**: Automatic retry logic for rate limits and transient errors
*   **Compatible Services**: Works with OpenAI-compatible APIs by setting `base_url`

Assistant

Responses are generated using AI and may contain mistakes.

[Ollama](/server/services/llm/ollama)[OpenPipe](/server/services/llm/openpipe)

[x](https://x.com/pipecat_ai)[github](https://github.com/pipecat-ai/pipecat)[discord](https://discord.gg/pipecat)

[Powered by Mintlify](https://mintlify.com/preview-request?utm_campaign=poweredBy&utm_medium=referral&utm_source=daily)
