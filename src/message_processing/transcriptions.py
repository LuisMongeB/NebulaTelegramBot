import asyncio
import io
import logging
from typing import Dict, List, Optional, Tuple

from openai import OpenAI, OpenAIError, RateLimitError

from src.services.openai_service import OpenAIService


class Transcriber:
    def __init__(self, openai_api_key: str):
        self.client = OpenAIService(api_key=openai_api_key)

    async def transcribe_audio(
        self, audio_data: bytes, prompt: Optional[str] = None
    ) -> Optional[Tuple[str, str]]:
        """
        Transcribe an audio file using OpenAI's Whisper model.

        Parameters:
            audio_data (bytes): Byte data of the audio file
            prompt (str, optional): Optional transcription prompt

        Returns:
            Optional[Tuple[str, str]]: (transcription_text, detected_language) or None
        """
        try:
            logging.info(f"Transcribing audio data of type: {type(audio_data)}")

            # TODO: user should be able to specify prompt if desired
            # Define our synchronous transcription operation with bytes
            def _transcribe():
                with io.BytesIO(audio_data) as audio_file:
                    audio_file.name = "audio.m4a"
                    return self._client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="verbose_json",
                        prompt=prompt,
                    )

            # Run the synchronous operation in a thread pool
            transcript = await asyncio.to_thread(_transcribe)

            text = transcript.text
            detected_language = transcript.language

            logging.info("Successfully transcribed audio")
            logging.info(f"Detected language: {detected_language}")

            return text, detected_language

        except OpenAIError as e:
            logging.error(f"OpenAI API error: {str(e)}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error: {str(e)}", exc_info=True)
            return None
