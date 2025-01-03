import asyncio
import datetime
import io
import logging
import os

import aiohttp
from azure.storage.blob.aio import BlobServiceClient

# from pydub import AudioSegment


async def download_audio_file(file_id, token):
    async with aiohttp.ClientSession() as session:
        # Get file path from Telegram's getFile endpoint
        logging.info(f"Getting file path for file_id: {file_id}")
        response = await session.get(
            f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}"
        )
        logging.info(f"Response status: {response.status}")

        result = await response.json()
        logging.info(f"getFile response: {result}")
        file_path = result.get("result", {}).get("file_path")

        if not file_path:
            logging.error(f"Failed to get file path for file_id: {file_id}")
            return None
        logging.info(f"File path: {file_path}")
        # Download the file using the file path
        file_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
        response = await session.get(file_url)
        return (
            await response.read(),
            file_path.split(".")[-1],
        )  # Return the file bytes and extension


# def convert_to_m4a(audio_bytes, input_format):
#     logging.info("Converting audio to m4a format")
#     audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format=input_format)
#     m4a_audio_io = io.BytesIO()
#     audio.export(m4a_audio_io, format="m4a")
#     m4a_audio_io.seek(0)
#     return m4a_audio_io.read()


async def save_audio_to_blob(chat_id, m4a_audio_data, timestamp):
    try:
        logging.info(
            f"AdditionalStorage__blobStorageUri: {os.getenv('AdditionalStorage__blobServiceUri')}"
        )
        blob_service_client = BlobServiceClient.from_connection_string(
            os.getenv("AdditionalStorage")
        )
        container_name = "filecontainer"
        blob_name = f"{chat_id}_{timestamp}.m4a"
        logging.info(f"M4a data type: {type(m4a_audio_data)}")
        blob_client = blob_service_client.get_blob_client(
            container=container_name, blob=blob_name
        )
        await blob_client.upload_blob(m4a_audio_data, blob_type="BlockBlob")

        logging.info(f"Audio message saved to blob storage at {blob_name}")
    except Exception as e:
        logging.error(f"Failed to save audio file to blob storage: {str(e)}")


async def process_audio_message(message, token):
    # Extract audio file details from the message
    logging.info(f"Processing message: {message}")
    audio_file_id = message.get("audio", {}).get("file_id")
    chat_id = message.get("chat", {}).get("id", "No chat id")
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")

    # Download the audio file from Telegram
    audio_data, file_extension = await download_audio_file(audio_file_id, token)
    if not audio_data:
        logging.error(f"Failed to download audio file with file_id: {audio_file_id}")
        return
    logging.info(f"Downloaded audio data: {type(audio_data)}")
    # Convert the audio data to M4A format
    # try:
    #     logging.info(
    #         f"Converting audio data to M4A format: {len(audio_data)} in {file_extension} format"
    #     )
    #     m4a_audio_data = convert_to_m4a(audio_data, file_extension)
    # except Exception as e:
    #     logging.error(f"Failed to convert audio to m4a format: {e}")
    #     return

    # Save the M4A audio file to Azure Blob Storage
    await save_audio_to_blob(chat_id, audio_data, timestamp)

    logging.info(
        f"Processing audio message from chat: {chat_id} with file_id: {audio_file_id}"
    )
