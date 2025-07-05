import os
import asyncio
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import JobContext, WorkerOptions, cli
from livekit.plugins import openai

load_dotenv()

async def entrypoint(ctx: JobContext):
    await ctx.connect()
    session = agents.AgentSession()
    agent = agents.Agent(
        instructions=os.environ.get("AGENT_INSTRUCTIONS", "You are a helpful assistant."),
        llm=openai.LLM(model="gpt-4o-mini")
    )

    @session.on("user_input_transcribed")
    async def on_transcript(transcript):
        if transcript.is_final:
            # Echo the transcript or use LLM to generate a reply
            reply = await agent.llm.generate_reply(transcript.transcript)
            await session.send_text(reply)

    await session.start(
        agent=agent,
        room=ctx.room
    )

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint)) 