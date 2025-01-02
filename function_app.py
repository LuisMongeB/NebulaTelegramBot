import codecs
import csv
import datetime
import json
import logging

import azure.functions as func
from additional_functions import bp

app = func.FunctionApp()

app.register_blueprint(bp)


def process_audio_message(message):
    # Extract audio file details from the message
    audio_file_id = message.get("audio", {}).get("file_id") or message.get(
        "voice", {}
    ).get("file_id")
    chat_id = message.get("chat", {}).get("id", "No chat id")
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")

    # Here you can include logic to download the audio file using Telegram Bot API
    # For example, use Telegram Bot API to get the file path and then download the file

    # Placeholder: Log the extraction details
    logging.info(
        f"Processing audio message from chat: {chat_id} with file_id: {audio_file_id}"
    )

    # Call function to save audio details or file to Azure Blob Storage
    save_audio_to_blob(chat_id, audio_file_id, timestamp)


def save_audio_to_blob(chat_id, audio_file_id, timestamp):
    # Placeholder: Include logic to save the audio file or its metadata to Azure Blob Storage
    logging.info(
        f"Saving audio message to blob storage for chat: {chat_id} with file_id: {audio_file_id} at {timestamp}"
    )


@app.function_name("TelegramBotFunction")
@app.route(route="nebula", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def telegram_bot_function(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Python HTTP trigger function received a request from Telegram Bot.")

    try:
        req_body = req.get_json()
        logging.info(f"Received message: {req_body}")

        # Check the type of message
        message = req_body.get("message", {})
        if "text" in message:
            text = message["text"]
            logging.info(f"Received text message: {text}")
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


@app.function_name("SecondHTTPFunction")
@app.route(route="newroute")
def test_function(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Starting the second HTTP Function request.")

    name = req.params.get("name")
    if name:
        message = f"Hello, {name}, so glad this Function worked!!"
    else:
        message = "Hello, so glad this Function worked!!"
    return func.HttpResponse(message, status_code=200)


@app.function_name(name="MyFirstBlobFunction")
@app.blob_trigger(
    arg_name="myblob", path="filecontainer/{name}.csv", connection="AdditionalStorage"
)
@app.blob_output(
    arg_name="outputblob",
    path="processedcontainer/{name}_processed.csv",  # Use a placeholder for dynamic blob name
    connection="AdditionalStorage",
)
def process_blob(myblob: func.InputStream, outputblob: func.Out[func.InputStream]):
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


@app.function_name(name="ReadFileBlobFunction")
@app.blob_trigger(
    arg_name="readfile",
    path="newcontainer/People2.csv",
    connection="AzureWebJobsStorage",
)
def main(readfile: func.InputStream):
    reader = csv.reader(codecs.iterdecode(readfile, "utf-8"))
    for line in reader:
        print(line)
