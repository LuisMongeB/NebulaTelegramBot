import logging
from typing import Dict, Tuple

import azure.functions as func

from src.agents.audio_agent import AudioAgent
from src.commands.command_registry import CommandRegistry
from src.commands.start_command import StartCommand
from src.services.openai_service import OpenAIService
from src.services.telegram_service import TelegramService

from .audio_processor import AudioProcessor
from .transcriptions import Transcriber


class MessageHandler:
    def __init__(
        self,
        openai_service: OpenAIService,
        telegram_service: TelegramService,
        audio_processor: AudioProcessor,
    ):
        self.openai_service = openai_service
        self.telegram_service = telegram_service
        self.audio_processor = audio_processor

    async def handle_update(self, update: Dict) -> func.HttpResponse:
        """
        Main entry point for handling different types of messages.
        Returns a tuple of (response_message, status_code)
        """
        try:
            if self._is_system_message(update):
                return func.HttpResponse("Ignoring system message", status_code=200)

            message = update.get("message", {})
            message_type = self._get_message_type(message)

            handlers = {
                "command": self.handle_command,
                "text": self.handle_text,
                "audio": self.handle_audio,
                "voice": self.handle_audio,
                "unknown": self.handle_unknown,
            }
            handler = handlers.get(message_type, handlers["unknown"])
            return await handler(message)
        except Exception as e:
            logging.error(f"Error handling message: {str(e)}")
            return func.HttpResponse(
                "An error occurred while processing the request", status_code=500
            )

    def _is_system_message(self, message):
        """Check if the message is a system message that should be ignored"""
        return (
            "my_chat_member" in message
            or "message_auto_delete_timer_changed" in message.get("message", {})
        )

    def _get_message_type(self, message: Dict):
        """Determine the type of message received"""
        entities = message.get("entities", [])

        if any(entity["type"] == "bot_command" for entity in entities):
            return "command"
        if "text" in message:
            return "text"
        elif "audio" in message:
            return "audio"
        elif "voice" in message:
            return "voice"
        return "unknown"

    async def handle_text(self, message: Dict) -> Tuple[str, int]:
        """Handle text messages"""
        try:
            text = message["text"]
            chat_id = message["chat"]["id"]

            logging.info(f"Received text message: {text}")
            # TODO: For now just a normal message but agentic starts here
            # Create supervisor agent that takes user message + conversation history and returns response
            # Agent State needs: name: str, message: Dict, available_tools: List[str], check_with_human: bool,
            system_prompt = """
                You are Nebula, a Telegram assistant that helps users with their audios by transcribing or summarizing them based on length.
                For now, all you can do is handle audios! So your task is to steer the user in that direction.
                If the topic is not related to you, Nebula, or to what you can do, notify the user that it is out of scope, if it is just a greeting such as 'hi' or equivalents, introduce yourself.

                The following is context about Nebula as a service. It is for you to have proper information to reply to the user.
                Only base yourself on what is stated here, regardless of what the user might argue.
                
                What is Nebula?
                It is a Telegram bot that for now, receives audio messages and transcribes it or summarizes it for the user.

                What can users send?
                As of now, only audios are supported with the following characteristics:
                a) Shorter than 10 minutes
                b) Forward from Whatsapp or Telegram chats
                c) Record and send a voice message (if maybe used for transcribing thought or speeches)
                d) If the audio is longer than 90 seconds it will be summarized.
                e) Nebula can handle audios in all the most spoken languages so invite them to give it a try.

                ALL other file types, such as images and PDFs are not supported at the moment.

                IMPORTANT: Please reply in the language of the text that has been sent to you. For example, if someone says 'Hi' reply in english, if someone says 'Ciao' reply in italian and so on.
            """
            messages = [
                {"role": "developer", "content": system_prompt},
                {
                    "role": "user",
                    "content": text,
                },
            ]
            response = await self.openai_service.generate_chat_completion(
                messages=messages, model="gpt-4o-mini", temperature=0
            )
            await self.telegram_service.send_message(chat_id=chat_id, text=response)
            return func.HttpResponse("Received text message: {text}", status_code=200)
        except Exception as e:
            logging.error(f"Error handling text message: {str(e)}")
            return func.HttpResponse("Error processing text message", status_code=500)

    async def handle_audio(self, message: Dict) -> Tuple[str, int]:
        """Handle audio messages"""

        try:
            chat_id = message["chat"]["id"]
            logging.info(f"Received audio message {message}")
            audio = message.get("audio", message.get("voice", {}))
            duration = audio.get("duration", 0)
            file_id = audio["file_id"]
            max_audio_duration = 10 * 60
            summarization_threshold = 250

            duration = message.get("audio", message.get("voice", {})).get("duration", 0)
            if duration < max_audio_duration:
                bot_message_id = await self.telegram_service.send_message(
                    chat_id=chat_id,
                    text="Transcribing audio message...",
                )

                transcription, language = (
                    await self.audio_processor.process_audio_message(
                        message, self.telegram_service.bot_token
                    )
                )
                if duration > summarization_threshold:
                    await self.telegram_service.edit_message(
                        chat_id=message["chat"]["id"],
                        message_id=bot_message_id,
                        text=f"Audio message transcribed. Summarizing...",
                    )
                    audio_agent = AudioAgent(model_name="gpt-4o-mini", temperature=0)
                    audio_agent_response = audio_agent.process_transcription(
                        transcription, language
                    )

                    await self.telegram_service.edit_message(
                        chat_id=message["chat"]["id"],
                        message_id=bot_message_id,
                        text=f"{audio_agent_response['summary']}",
                    )
                    return func.HttpResponse(
                        "Transcription has been summarized", status_code=200
                    )
                else:
                    final_transcription = transcription
                    await self.telegram_service.edit_message(
                        chat_id=message["chat"]["id"],
                        message_id=bot_message_id,
                        text=f"[{language}] Transcription:\n{final_transcription}",
                    )
                    return func.HttpResponse(
                        "Transcription has been sent", status_code=200
                    )
            else:
                await self.telegram_service.send_message(
                    chat_id=message["chat"]["id"],
                    text=f"Audio messages longer than {round(max_audio_duration / 60)} minutes are not supported.",
                )
                return func.HttpResponse(
                    f"Audio messages longer than {round(max_audio_duration / 60)} minute are not supported.",
                    status_code=200,
                )
        except Exception as e:
            logging.error(f"Error handling audio message: {str(e)}")
            return func.HttpResponse("Error processing audio message", status_code=500)

    async def handle_command(self, message: Dict):

        command_registry = CommandRegistry()
        start_command_handler = StartCommand(self.telegram_service)

        command_registry.register(
            "start",
            start_command_handler.execute_with_name,
            "Start the bot",
            "Initialize the bot and see the welcome message",
        )
        # FOR NOW JUST USE THE COMMAND
        executed_command = await start_command_handler.execute(message["chat"]["id"])

        if not executed_command:
            return func.HttpResponse(f"An error ocurred while running telegram command")
        return func.HttpResponse(
            f"Start command triggered successfully",
            status_code=200,
        )

    async def handle_unknown(self, message: Dict) -> Tuple[str, int]:
        """Handle unknown message types"""
        try:
            logging.info("Received unknown type of message.")
            self.telegram_service.send_message(
                chat_id=message["chat"]["id"], text="Received unknown type of message."
            )
            return func.HttpResponse(
                "Received unknown type of message.", status_code=200
            )
        except Exception as e:
            logging.error(f"Error handling unknown message: {str(e)}")
            return func.HttpResponse(
                "Error processing unknown message", status_code=500
            )
