import logging
import os

import azure.functions as func

from additional_functions import bp
from src.commands.command_registry import CommandRegistry
from src.commands.start_command import StartCommand
from src.message_processing.audio_processor import AudioProcessor
from src.message_processing.transcription_processor import summarize_transcription
from src.services.openai_service import OpenAIService
from src.services.telegram_service import TelegramService

token = os.getenv("TELEGRAM_BOT_TOKEN", "")
telegram_service = TelegramService(token)
openai_service = OpenAIService(os.getenv("OPENAI_API_KEY", ""))
audio_processor = AudioProcessor(telegram_service, openai_service)

command_registry = CommandRegistry()
start_command_handler = StartCommand(telegram_service)

command_registry.register(
    "start",
    start_command_handler.execute_with_name,
    "Start the bot",
    "Initialize the bot and see the welcome message",
)

app = func.FunctionApp()

app.register_blueprint(bp)


@app.function_name("TelegramBotFunction")
@app.route(route="nebula", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
async def telegram_bot_function(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Python HTTP trigger function received a request from Telegram Bot.")

    try:
        req_body = req.get_json()
        logging.info(f"Received message: {req_body}")

        if (
            "my_chat_member" in req_body
            or "message_auto_delete_timer_changed" in req_body.get("message", {})
        ):
            logging.info("Ignoring non-relevant message.")
            return func.HttpResponse(status_code=200)

        message = req_body.get("message", {})

        if "entities" in message and message["entities"][0]["type"] == "bot_command":

            command_name = message["text"]
            chat_id = message["chat"]["id"]
            username = message["from"].get("username", "")

            if command_name == "/start":
                response = await start_command_handler.execute_with_name(
                    chat_id, username=username
                )

                if response:
                    return func.HttpResponse(
                        "Start command executed correctly.", status_code=200
                    )
                else:
                    return func.HttpResponse(
                        "An error occurred while executing the start command.",
                        status_code=500,
                    )

        if "text" in message:
            text = message["text"]
            logging.info(f"Received text message: {text}")
            await telegram_service.send_message(
                chat_id=message["chat"]["id"], text=f"Received text message: {text}"
            )
            return func.HttpResponse(f"Received text message: {text}", status_code=200)

        elif "audio" in message or "voice" in message:
            # SET DURATION LIMIT -> TODO: good for now but improve later, don't hardcode it
            duration = message.get("audio", message.get("voice", {})).get("duration", 0)
            if duration < 420:
                await telegram_service.send_message(
                    chat_id=message["chat"]["id"],
                    text="Processing audio message...",
                )

                transcription, language = await audio_processor.process_audio_message(
                    message, token
                )

                if duration > 90:
                    final_transcription = await summarize_transcription(
                        transcription, language, openai_service
                    )

                    await telegram_service.send_message(
                        chat_id=message["chat"]["id"], text=f"{final_transcription}"
                    )
                    return func.HttpResponse(
                        "Transcription has been summarized", status_code=200
                    )
                else:
                    final_transcription = transcription
                    await telegram_service.send_message(
                        chat_id=message["chat"]["id"],
                        text=f"[{language}] Transcription:\n{final_transcription}",
                    )
                    return func.HttpResponse(
                        "Transcription has been sent", status_code=200
                    )
            else:
                await telegram_service.send_message(
                    chat_id=message["chat"]["id"],
                    text="Audio messages longer than 10 minute are not supported.",
                )
                return func.HttpResponse(
                    "Audio messages longer than 10 minute are not supported.",
                    status_code=200,
                )
        else:
            logging.info("Received unknown type of message.")
            return func.HttpResponse(
                "Received unknown type of message.", status_code=200
            )

    except Exception as e:
        logging.error(f"An error occurred while processing the request: {e}")
        return func.HttpResponse(
            "An error occurred while processing the request.", status_code=500
        )
