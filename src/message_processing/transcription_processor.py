import asyncio
import logging
from typing import Dict, List

from src.services.openai_service import OpenAIService


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
        1. An audio is sent to you from a chat the user has with somebody else, keep the summary down to the main topics and supporting details.
        2. Summary must be brief but mention the main topics and main points while narrating it in the order of appearance of the topics, tone and style of the transcription.
        3. Do not include any preamble or greetings in the summary.
        4. Make sure the final summary is strongly based on the received message.
        5. Make sure the final summary is in {language}.
        6. It is mandatory that the summary is formmated with html tags supported by Telegram to escape these special characters.

        Telegram supports these HTML tags:

            <b> or <strong> - Bold
            <i> or <em> - Italic
            <u> - Underline
            <s> or <del> - Strikethrough
                
            Important considerations
            You must escape special characters:
        """

    try:
        # Use the OpenAI service to summarize the transcription
        messages = [
            {"role": "developer", "content": summarize_prompt},
            {"role": "user", "content": transcription},
        ]
        summary = await openai_service.generate_chat_completion(messages=messages)

        logging.info(f"Summary: {summary}")
        return summary

    except Exception as e:
        # Log any errors and return the original transcription
        logging.error(f"Error summarizing transcription: {e}")
        return transcription
