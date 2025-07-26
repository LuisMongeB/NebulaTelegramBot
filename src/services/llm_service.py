import asyncio
import io
import logging
import os
from typing import Dict, List, Optional, Tuple, Union

import yaml
from langchain_openai import ChatOpenAI
from openai import OpenAI, OpenAIError


class LLMService:
    def __init__(self, provider: str, api_key: str):

        if provider == "openai":
            self.llm = ChatOpenAI(api_key=api_key, model="gpt-4o-mini")
        else:
            raise NotImplementedError(f"Provider '{provider}' not supported")

        self.provider = provider
        self.prompts_path = os.path.join("src", "agents", "prompts.yaml")

    def generate_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = 1000,
    ) -> Optional[str]:
        """
        Generate a response using OpenAI API.

        Parameters:
            messages: List of message dictionaries with 'role' and 'content' keys
            temperature: Controls randomness (higher = more random)
            max_tokens: Maximum length of response

        Returns:
            The generated text response or None if an error occurred
        """
        try:
            response = self.llm.invoke(
                messages, temperature=temperature, max_tokens=max_tokens
            )

            # Return the content string
            return response.content

        except Exception as e:
            logging.error(f"{self.provider} API error: {str(e)}")
            return None

    def build_prompt(self, prompt_name: str):
        """
        Load a prompt from the prompts YAML file.

        Parameters:
            prompt_name: The name of the prompt to load

        Returns:
            The prompt string or None if not found
        """
        try:
            with open(self.prompts_path, "r") as file:
                prompts = yaml.safe_load(file)
            agent_prompt = prompts.get(prompt_name)
            return "\n".join(
                [prompt_section for prompt_section in agent_prompt.values()]
            )

        except Exception as e:
            logging.error(f"Error loading prompt: {str(e)}")
            return None

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
                    _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                    return _client.audio.transcriptions.create(
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
