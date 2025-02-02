import logging
from dataclasses import dataclass
from typing import Optional

from src.services.telegram_service import TelegramService


@dataclass
class StartCommandConfig:
    """
    Configuration for the start command response. This allows us to easily modify
    the welcome message and its components without changing the command logic.
    """

    welcome_title: str = "Hi, I'm Nebula"
    bot_description: str = (
        "I'll help you with audio messages that are sent from chats on Whatsapp or Telegram."
    )
    capabilities: list[str] = (
        "• Convert voice messages to text\n"
        "• Provide summaries for longer messages (over 100 words)\n"
        "• Process audio in multiple languages\n"
    )
    usage_instructions: list[str] = (
        "1. Send or forward any voice/audio message (up to 10 minutes)\n"
        "2. Wait while I process it\n"
        "3. Get your transcription, summary, and response!"
    )
    privacy_notice: str = "🔒 Your messages are processed securely **are note stored**."
    try_now_prompt: str = "Try it now by sending a voice message! 🎤"


class StartCommand:
    """
    Handles the /start command for the Telegram bot. This command is triggered
    automatically when a user first interacts with the bot or manually when
    they send /start.
    """

    def __init__(self, telegram_service: TelegramService):
        """
        Initialize the command handler with required services.

        The telegram_service parameter is injected, following dependency injection
        principles for better testing and modularity.
        """
        self.telegram_service = telegram_service
        self.config = StartCommandConfig()

    def _build_welcome_message(self) -> str:
        """
        Constructs the welcome message using the configuration components.

        This is separated into its own method to make the message structure
        clear and easily modifiable. It also makes it easier to add
        conditional content in the future.
        """
        return (
            f"{self.config.welcome_title} {self.config.bot_description}\n\n"
            f"🎯 Here's what I can do:\n"
            f"{self.config.capabilities}\n\n"
            f"📱 To use me, simply:\n"
            f"{self.config.usage_instructions}\n\n"
            f"{self.config.privacy_notice}\n\n"
            f"{self.config.try_now_prompt}"
        )

    async def execute(self, chat_id: int) -> bool:
        """
        Execute the start command by sending the welcome message to the user.

        Parameters:
            chat_id (int): The Telegram chat ID to send the message to

        Returns:
            bool: True if the message was sent successfully, False otherwise
        """
        try:
            welcome_message = self._build_welcome_message()
            await self.telegram_service.send_message(chat_id, welcome_message)
            logging.info(f"Sent welcome message to chat_id: {chat_id}")
            return True

        except Exception as e:
            logging.error(
                f"Error sending welcome message to chat_id {chat_id}: {str(e)}",
                exc_info=True,
            )
            return False

    async def execute_with_name(
        self, chat_id: int, username: Optional[str] = None
    ) -> bool:
        """
        Execute the start command with a personalized welcome message.

        This variation of the execute method allows for personalization when
        we have the user's name. It demonstrates how we can extend the basic
        functionality while maintaining backward compatibility.

        Parameters:
            chat_id (int): The Telegram chat ID to send the message to
            user_name (Optional[str]): The user's name for personalization

        Returns:
            bool: True if the message was sent successfully, False otherwise
        """
        try:
            welcome_message = self._build_welcome_message()
            if username:
                # Insert the personalized greeting at the start
                welcome_message = f"Hello, {username}! 👋\n\n{welcome_message}"

            await self.telegram_service.send_message(chat_id, welcome_message)
            logging.info(
                f"Sent personalized welcome message to {username} (chat_id: {chat_id})"
            )
            return True

        except Exception as e:
            logging.error(
                f"Error sending personalized welcome message to chat_id {chat_id}: {str(e)}",
                exc_info=True,
            )
            return False
