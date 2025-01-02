import asyncio
import codecs
import csv
import datetime
import json
import logging
import os

import azure.functions as func
from additional_functions import bp
from commands.command_registry import CommandRegistry
from commands.start_command import StartCommand
from message_processing.audio_processor import process_audio_message
from services.telegram_service import TelegramService

token = os.getenv("TELEGRAM_BOT_TOKEN", "")

if not token:
    logging.error(f"Telegram Token not found in the environment variables.")
    raise Exception("Telegram Token not found in the environment variables.")

telegram_service = TelegramService(token)

command_registry = CommandRegistry()
start_command = StartCommand(telegram_service)

command_registry.register(
    "start",
    start_command.execute,
    "Start the bot",
    "Initialize the bot and see welcome message",
)


app = func.FunctionApp()

app.register_blueprint(bp)


@app.function_name("TelegramBotFunction")
@app.route(route="nebula", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def telegram_bot_function(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Python HTTP trigger function received a request from Telegram Bot.")

    logging.info(f"Instantiated the TelegramService class.")
    try:
        req_body = req.get_json()
        logging.info(f"Received message: {req_body}")

        # Check the type of message
        message = req_body.get("message", {})

        if "entities" in message and message["entities"][0]["type"] == "bot_command":
            command_text = message["text"]
            chat_id = message["chat"]["id"]
            user_name = message["from"].get("username", "")

            if command_text == "/start" and user_name:
                logging.info(f"Received /start command from {user_name}")
                asyncio.run(start_command.execute_with_name(chat_id, user_name))
                return func.HttpResponse(
                    f"Received /start command from {user_name}", status_code=200
                )

        if "text" in message:
            text = message["text"]
            logging.info(f"Received text message: {text}")
            asyncio.run(
                telegram_service.send_message(
                    chat_id=message["chat"]["id"], text=f"Received text message: {text}"
                )
            )
            return func.HttpResponse(f"Received text message: {text}", status_code=200)
        elif "audio" in message or "voice" in message:
            # Call the function to process the audio message
            process_audio_message(message)
            return func.HttpResponse(
                "Audio message received and processing started.", status_code=200
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


@app.function_name(name="ProcessM4AFile")
@app.blob_trigger(
    arg_name="myblob", path="filecontainer/{name}.m4a", connection="AdditionalStorage"
)
@app.blob_output(
    arg_name="outputblob",
    path="processedcontainer/{name}_processed.m4a",  # Use a placeholder for dynamic blob name
    connection="AdditionalStorage",
)
def process_m4a_blob(myblob: func.InputStream, outputblob: func.Out[func.InputStream]):
    try:
        # Log the blob details
        logging.info(
            f"Python blob Function triggered after the .csv file was uploaded to filecontainer.\n"
            f"Blob path: {myblob.name}, Blob type: {type(myblob)}"
        )

        # Read the blob content
        content = myblob.read().decode("utf-8")  # Assuming the content is a text/csv

        # Optionally process the content here
        processed_content = content  # For now, we are not modifying the content

        # Set the processed content to the output blob
        outputblob.set(processed_content)

        logging.info(
            f"Blob has been copied to the processed container with dynamic name."
        )
    except Exception as e:
        logging.error(f"An error occurred while writing the processed file: {e}")
        raise Exception(f"An error occurred while writing the processed file: {e}")
