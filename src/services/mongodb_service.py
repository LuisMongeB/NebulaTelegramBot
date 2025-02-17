import logging
from datetime import datetime
from typing import Dict, List, Optional

from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, InvalidURI


class NebulaUsers:
    def __init__(self, connection_string: str):
        """Initialize database connection.

        Args:
            connection_string: MongoDB Atlas connection string
        """
        try:
            self.client = MongoClient(connection_string)
            self.db = self.client.nebula_agent
            self.users = self.db.users
            # Create indexes
            # self.users.create_index('email', unique=True)
            self.users.create_index("username", unique=True)
            logging.info("Connected to MongoDB Atlas")
        except InvalidURI as e:
            raise InvalidURI(f"Failed to connect to Mongo DB: {str(e)}")

    def create_user(self, user_data: Dict) -> Optional[str]:
        """Create a new user.

        Args:
            user_data: Dictionary containing user information

        Returns:
            str: ID of created user or None if creation failed
        """
        try:
            user_data["created_at"] = datetime.now()
            user_data["updated_at"] = datetime.now()

            result = self.users.insert_one(user_data)
            return str(result.inserted_id)

        except DuplicateKeyError:
            logging.error(
                f"User with username {user_data.get('username')} already exists."
            )
            return None
        except Exception as e:
            logging.error(f"Error creating user: {str(e)}")
            return None

    def get_user(self, username: str) -> Optional[Dict]:
        """Retrieve user by ID.

        Args:
            user_id: User's MongoDB ID

        Returns:
            Dict: User document or None if not found
        """
        try:
            logging.info(f"self.users: {self.users}")
            return self.users.find_one({"username": username})
        except Exception as e:
            logging.error(f"Error retrieving user: {str(e)}")
            return None

    def update_user(self, user_id: str, update_data: Dict) -> bool:
        """Update user information.

        Args:
            user_id: User's MongoDB ID
            update_data: Dictionary containing fields to update

        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            update_data["updated_at"] = datetime.utcnow()
            result = self.users.update_one({"_id": user_id}, {"$set": update_data})
            return result.modified_count > 0
        except Exception as e:
            logging.error(f"Error updating user: {str(e)}")
            return False

    def delete_user(self, username: str) -> bool:
        """Delete user by ID.

        Args:
            user_id: User's MongoDB ID

        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            result = self.users.delete_one({"username": username})
            return result.deleted_count > 0
        except Exception as e:
            logging.error(f"Error deleting user: {str(e)}")
            return False
