import asyncio
import logging
import os

import azure.functions as func

from additional_functions import bp
from commands.command_registry import CommandRegistry
from commands.start_command import StartCommand
from message_processing.audio_processor import AudioProcessor
from message_processing.transcription_processor import summarize_transcription
from services.openai_service import OpenAIService
from services.telegram_service import TelegramService

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

        if (
            "my_chat_member" in req_body
            or "message_auto_delete_timer_changed" in req_body.get("message", {})
        ):
            logging.info("Ignoring non-relevant message.")
            return func.HttpResponse(status_code=200)

        # Check the type of message
        message = req_body.get("message", {})

        if "message_auto_delete_timer_changed" in req_body.get("message", {}):
            logging.info("Received an auto-delete timer change message.")
            return func.HttpResponse(status_code=200)

        # handle commands
        if "entities" in message and message["entities"][0]["type"] == "bot_command":

            command_name = message["text"]
            chat_id = message["chat"]["id"]
            username = message["from"].get("username", "")

            if command_name == "/start":
                response = asyncio.run(
                    start_command_handler.execute_with_name(chat_id, username=username)
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
            logging.info(f"Message: ", message)
            asyncio.run(
                telegram_service.send_message(
                    chat_id=message["chat"]["id"], text=f"Received text message: {text}"
                )
            )
            return func.HttpResponse(f"Received text message: {text}", status_code=200)

        elif "audio" in message or "voice" in message:
            # SET DURATION LIMIT -> TODO: good for now but do it better, don't hardcode it
            duration = message.get("audio", message.get("voice", {})).get("duration", 0)
            if duration < 600:
                asyncio.run(
                    telegram_service.send_message(
                        chat_id=message["chat"]["id"],
                        text="Processing audio message...",
                    )
                )
                transcription, language = asyncio.run(
                    audio_processor.process_audio_message(message, token)
                )

                if duration > 90:
                    final_transcription = asyncio.run(
                        summarize_transcription(transcription, language, openai_service)
                    )
                    asyncio.run(
                        telegram_service.send_message(
                            chat_id=message["chat"]["id"], text=f"{final_transcription}"
                        )
                    )
                else:
                    final_transcription = transcription
                    asyncio.run(
                        telegram_service.send_message(
                            chat_id=message["chat"]["id"],
                            text=f"[{language}] Transcription:\n{final_transcription}",
                        )
                    )

                return func.HttpResponse(
                    "Audio messages longer than 10 minute are not supported.",
                    status_code=200,
                )
            else:
                asyncio.run(
                    telegram_service.send_message(
                        chat_id=message["chat"]["id"],
                        text="Audio messages longer than 10 minute are not supported.",
                    )
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


# @app.function_name(name="ProcessM4AFile")
# @app.blob_trigger(
#     arg_name="myblob", path="filecontainer/{name}.m4a", connection="AdditionalStorage"
# )
# @app.blob_output(
#     arg_name="outputblob",
#     path="processedcontainer/{name}_processed.m4a",  # Use a placeholder for dynamic blob name
#     connection="AdditionalStorage",
# )
# def process_m4a_blob(myblob: func.InputStream, outputblob: func.Out[func.InputStream]):

#     try:
#         # Extract the chat_id from the blob name
#         chat_id = myblob.name.split("/")[-1].split("_")[0]
#         # Log the blob details
#         logging.info(
#             f"Python blob Function triggered after the .m4a file was uploaded to filecontainer.\n"
#             f"Blob path: {myblob.name}, Blob type: {type(myblob)}"
#         )

#         m4a_blob_bytes = myblob.read()
#         transcription, language = asyncio.run(
#             openai_service.transcribe_audio(audio_data=m4a_blob_bytes)
#         )

#         # Set the processed content to the output blob
#         outputblob.set(m4a_blob_bytes)

#         logging.info(
#             f"Blob has been copied to the processed container with dynamic name."
#         )
#         asyncio.run(
#             telegram_service.send_message(
#                 chat_id=chat_id, text=f"Transcription:\n{transcription}"
#             )
#         )
#     except Exception as e:
#         logging.error(f"An error occurred while writing the processed file: {e}")
#         raise Exception(f"An error occurred while writing the processed file: {e}")
