import logging
import os

import azure.functions as func

from additional_functions import bp
from src.commands.command_registry import CommandRegistry
from src.commands.start_command import StartCommand
from src.message_processing.audio_processor import AudioProcessor
from src.message_processing.message_handler import MessageHandler
from src.message_processing.transcription_processor import summarize_transcription
from src.services.openai_service import OpenAIService
from src.services.telegram_service import TelegramService

token = os.getenv("TELEGRAM_BOT_TOKEN", "")
telegram_service = TelegramService(token)
openai_service = OpenAIService(os.getenv("OPENAI_API_KEY", ""))
audio_processor = AudioProcessor(telegram_service, openai_service)

message_handler = MessageHandler(
    openai_service=openai_service,
    telegram_service=telegram_service,
    audio_processor=audio_processor,
)

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
        
        response_message = await message_handler.handle_update(req_body)
        return response_message

    except Exception as e:
        logging.error(f"An error occurred while processing the request: {e}")
        return func.HttpResponse(
            "An error occurred while processing the request.", status_code=500
        )
