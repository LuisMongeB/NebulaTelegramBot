# command_registry.py

import asyncio
import logging
from dataclasses import dataclass
from typing import Callable, Dict, Optional

import azure.functions as func


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
        username = kwargs.get("username", "")

        if command_name == "/start":
            start_command = self._commands.get(command_name)
            if username:
                logging.info(f"Received /start command from {username}")
                logging.info(f"Command: {start_command}")
                start_command.handler(chat_id, username=username)
                return func.HttpResponse(
                    f"Received /start command from {username}", status_code=200
                )
            else:
                logging.info("Received /start command")
                await start_command.handler(chat_id)
                return func.HttpResponse("Received /start command", status_code=200)
        elif command_name != "/start":
            logging.info(f"Received unknown command: {command_name}")
            return func.HttpResponse(
                f"Received unknown command: {command_name}", status_code=500
            )

    def get_available_commands(self) -> str:
        """Get a formatted string of available commands and their descriptions."""
        return "\n".join(
            f"{cmd}: {command.description}" for cmd, command in self._commands.items()
        )

    def get_command_help(self, command_name: str) -> Optional[str]:
        """Get the help text for a specific command."""
        command = self._commands.get(command_name)
        return command.help_text if command else None
