from dotenv import load_dotenv

from livekit import agents
from livekit.agents import AgentSession, Agent
from livekit.plugins import (
    openai,
    google,
    silero,
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel
import datetime
from livekit.agents import ConversationItemAddedEvent

load_dotenv()


class Assistant(Agent):
    def __init__(self, context_vars=None) -> None:
        instructions = (
            "You are a helpful voice AI assistant."
        )
        # Add context variables to instructions if provided
        if context_vars:
            instructions = (
                "You are a helpful voice AI assistant. "
                "The user's name is {name}. They are {age} years old and live in {city}."
            ).format(**context_vars)
        super().__init__(instructions=instructions)


async def entrypoint(ctx: agents.JobContext):
    await ctx.connect()

    # Define your context variables here
    context_variables = {
        "name": "David",
        "age": 20,
        "city": "Lagos"
    }

    STT = google.STT(
        languages="en-US",
        model="latest_long",
        sample_rate=16000,
        min_confidence_threshold=0.65,
        punctuate=True,
        spoken_punctuation=False
    )

    STT.stream()

    session = AgentSession(
        stt=STT,
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=google.TTS(
            gender="FEMALE",
            language="en-US",
            voice_name="en-US-Chirp3-HD-Achernar"
        ),
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
    )

    @session.on("user_input_transcribed")
    def on_transcript(transcript):
        if transcript.is_final:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open("user_speech_log.txt", "a") as f:
                f.write(f"[{timestamp}] {transcript.transcript}\n")

    @session.on("conversation_item_added")
    def on_conversation_item_added(event: ConversationItemAddedEvent):
        if event.item.role == "assistant":
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open("user_speech_log.txt", "a") as f:
                f.write(f"[{timestamp}] [AGENT] {event.item.text_content}\n")

    await session.start(
        room=ctx.room,
        agent=Assistant(context_vars=context_variables)  # Pass context variables here
    )


    await session.generate_reply(
        instructions="Greet the user and offer your assistance."
    )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))