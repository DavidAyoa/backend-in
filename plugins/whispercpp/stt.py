from __future__ import annotations

import asyncio
import os
import tempfile
import wave
from typing import Optional

import numpy as np # For numerical operations and array handling
from scipy.signal import resample # For resampling
from pywhispercpp.model import Model

from livekit.agents import stt, utils
from livekit.agents.stt import (
    STT,
    SpeechData,
    SpeechEvent,
    SpeechEventType,
    STTCapabilities,
)
from livekit.agents.types import (
    APIConnectOptions,
    DEFAULT_API_CONNECT_OPTIONS,
    NotGivenOr,
    NOT_GIVEN,
)
from livekit.agents.utils import AudioBuffer, merge_frames, is_given

WHISPER_TARGET_SAMPLE_RATE = 16000
# Assuming 16-bit PCM audio data commonly used in WebRTC/LiveKit
AUDIO_DATA_TYPE = np.int16

class WhisperCppSTT(STT):
    def __init__(
        self,
        *,
        model: str,
        language: NotGivenOr[str] = NOT_GIVEN,
        **model_kwargs,
    ):
        super().__init__(
            capabilities=STTCapabilities(streaming=False, interim_results=False)
        )
        self._language = language
        self._model_kwargs = model_kwargs

        try:
            self._model = Model(model, **self._model_kwargs)
        except Exception as e:
            raise ValueError(f"Failed to load whisper.cpp model '{model}': {e}") from e

    def update_options(self, *, language: NotGivenOr[str] = NOT_GIVEN) -> None:
        if is_given(language):
            self._language = language

    async def _recognize_impl(
        self,
        buffer: AudioBuffer,
        *,
        language: NotGivenOr[str] = NOT_GIVEN,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> SpeechEvent:
        recognize_language = language if is_given(language) else self._language
        language_str = recognize_language if is_given(recognize_language) else None

        merged_buffer = merge_frames(buffer)
        original_rate = merged_buffer.sample_rate
        audio_data_bytes = merged_buffer.data.tobytes()
        sample_width = merged_buffer.data.itemsize

        # Convert byte data to NumPy array
        try:
            audio_np = np.frombuffer(audio_data_bytes, dtype=AUDIO_DATA_TYPE)
        except ValueError as e:
            raise RuntimeError(f"Failed to interpret audio data as {AUDIO_DATA_TYPE}: {e}") from e

        resampled_audio_data = audio_np
        current_rate = original_rate

        if current_rate != WHISPER_TARGET_SAMPLE_RATE:
            try:
                num_original_samples = len(audio_np)
                num_target_samples = int(num_original_samples * WHISPER_TARGET_SAMPLE_RATE / original_rate)
                resampled_audio_float = resample(audio_np, num_target_samples)

                # Ensure data is back in the original integer format after resampling
                resampled_audio_data = resampled_audio_float.astype(AUDIO_DATA_TYPE)
                current_rate = WHISPER_TARGET_SAMPLE_RATE
            except Exception as e:
                 raise RuntimeError(f"Failed to resample audio from {original_rate}Hz to {WHISPER_TARGET_SAMPLE_RATE}Hz using scipy: {e}") from e

        resampled_audio_bytes = resampled_audio_data.tobytes()

        tmp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_file_path = tmp_file.name
                with wave.open(tmp_file, 'wb') as wf:
                    wf.setnchannels(merged_buffer.num_channels)
                    wf.setsampwidth(sample_width) # Should still be 2 for int16
                    wf.setframerate(current_rate) # Use the potentially new rate (16000)
                    wf.writeframes(resampled_audio_bytes) # Write the potentially resampled data

            transcribe_params = {}

            loop = asyncio.get_event_loop()
            segments = await loop.run_in_executor(
                None, self._model.transcribe, tmp_file_path, transcribe_params
            )

            full_text = "".join(segment.text for segment in segments).strip()

            return SpeechEvent(
                type=SpeechEventType.FINAL_TRANSCRIPT,
                alternatives=[
                    SpeechData(
                        text=full_text,
                        language=language_str or "",
                        start_time=0,
                        end_time=0,
                        confidence=0.0,
                    )
                ],
            )

        except Exception as e:
            raise RuntimeError(f"Whisper.cpp transcription failed: {e}") from e
        finally:
            if tmp_file_path and os.path.exists(tmp_file_path):
                try:
                    os.remove(tmp_file_path)
                except OSError:
                    pass

    async def aclose(self) -> None:
        pass