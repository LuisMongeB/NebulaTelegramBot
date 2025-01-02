# command_registry.py

import logging
from dataclasses import dataclass
from typing import Callable, Dict, Optional


@dataclass
class Command:
    handler: Callable
    description: str
    help_text: str


class CommandRegistry:
    def __init__(self):
        self._commands: Dict[str, Command] = {}

    def register(
        self, command_name: str, handler: Callable, description: str, help_text: str
    ) -> None:
        """Register a new command with the registry."""
        if not command_name.startswith("/"):
            command_name = f"/{command_name}"

        self._commands[command_name] = Command(
            handler=handler, description=description, help_text=help_text
        )
        logging.info(f"Registered command: {command_name}")

    async def handle_command(
        self, command_name: str, chat_id: int, **kwargs
    ) -> Optional[str]:
        """Handle a command if it exists in the registry."""
        command = self._commands.get(command_name)
        if command:
            try:
                return await command.handler(chat_id, **kwargs)
            except Exception as e:
                logging.error(f"Error handling command {command_name}: {str(e)}")
                return "Sorry, there was an error processing your command."
        return None

    def get_available_commands(self) -> str:
        """Get a formatted string of available commands and their descriptions."""
        return "\n".join(
            f"{cmd}: {command.description}" for cmd, command in self._commands.items()
        )

    def get_command_help(self, command_name: str) -> Optional[str]:
        """Get the help text for a specific command."""
        command = self._commands.get(command_name)
        return command.help_text if command else None


# Usage example:
"""
registry = CommandRegistry()

async def start_handler(chat_id: int, **kwargs):
    return "Welcome message..."

registry.register(
    'start',
    start_handler,
    'Start the bot',
    'Use /start to initialize the bot and see available commands'
)
"""
