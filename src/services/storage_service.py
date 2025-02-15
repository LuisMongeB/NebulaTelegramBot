from typing import Optional

from azure.storage.blob import BlobServiceClient


class StorageService:
    def __init__(self, connection_string: str):
        """
        Initialize the StorageService with an Azure Storage connection string.

        Args:
            connection_string (str): Azure Storage account connection string
        """
        try:
            self.blob_service_client = BlobServiceClient.from_connection_string(
                connection_string
            )
        except Exception as e:
            raise Exception(f"Invalid connection string: {str(e)}")

    def upload_blob(self, container_name: str, blob_name: str, data: bytes):
        """
        Upload bytes data to a blob.

        Args:
            container_name (str): Name of the blob container.
            blob_name (str): Name of the blob.
            data (bytes): The byte data to upload.
        """
        try:
            container_client = self.blob_service_client.get_container_client(
                container_name
            )
            blob_client = container_client.get_blob_client(blob_name)
            blob_client.upload_blob(data, overwrite=True)
            print(f"Blob {blob_name} uploaded to container {container_name}.")
        except Exception as e:
            raise Exception(f"Failed to upload blob: {str(e)}")

    def download_blob(self, container_name: str, blob_name: str) -> bytes:
        """
        Download a blob and return its data as bytes.

        Args:
            container_name (str): Name of the blob container.
            blob_name (str): Name of the blob.

        Returns:
            bytes: The blob data.
        """
        try:
            container_client = self.blob_service_client.get_container_client(
                container_name
            )
            blob_client = container_client.get_blob_client(blob_name)
            downloader = blob_client.download_blob()
            data = downloader.readall()
            print(f"Blob {blob_name} downloaded from container {container_name}.")
            return data
        except Exception as e:
            raise Exception(f"Failed to download blob: {str(e)}")
