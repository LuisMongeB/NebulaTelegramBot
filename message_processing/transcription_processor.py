import asyncio
import logging
from typing import Dict, List

from services.openai_service import OpenAIService


async def summarize_transcription(
    transcription: str, language: str, openai_service: OpenAIService, metadata={}
) -> str:
    """
    Summarize the transcription using OpenAI's summarization model.

    Parameters:
        transcription (str): The transcription to be summarized
        openai_service (OpenAIService): The OpenAI service instance

    Returns:
        str: The summarized transcription
    """
    summarize_prompt = f"""The following is a transcription from an audio message in {language}. Please summarize the message following these rules:
        1. Keep the summary under 500 characters.
        2. Briefly mention the main topics and main points while narrating it in the order of topics, tone and style of the transcription.
        3. Outline the main topics and for each topic include a maxim seven word sentence.
        4. Do not include any preamble or greetings in the summary.
        5. Make sure the final summary is strongly based on the received message.
        6. Make sure the final summary is in {language}."""

    try:
        # Use the OpenAI service to summarize the transcription
        messages = [
            {"role": "system", "content": summarize_prompt},
            {"role": "user", "content": transcription},
        ]
        summary = await openai_service.generate_chat_completion(messages=messages)
        return summary

    except Exception as e:
        # Log any errors and return the original transcription
        logging.error(f"Error summarizing transcription: {e}")
        return transcription
