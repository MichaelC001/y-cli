import sys
import pyperclip
from typing import List, Optional, Tuple, Iterable
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter, Completer, Completion
from prompt_toolkit.document import Document
from rich.console import Console
from chat.models import Message

# Define slash commands
SLASH_COMMANDS = ["/copy", "/translate", "/save"]

class SlashCommandCompleter(Completer):
    """Completer for slash commands."""
    def __init__(self, commands: List[str]):
        self.command_completer = WordCompleter(commands, ignore_case=True)

    def get_completions(self, document: Document, complete_event) -> Iterable[Completion]:
        text = document.text_before_cursor
        if text.startswith('/') and ' ' not in text:
            # Only complete if text starts with / and has no spaces yet
            yield from self.command_completer.get_completions(document, complete_event)

class InputManager:
    def __init__(self, console: Console):
        self.console = console
        self.slash_completer = SlashCommandCompleter(SLASH_COMMANDS)

    def get_input(self) -> Tuple[str, str]:
        """Get user input with support for multi-line input and slash commands.

        Returns:
            Tuple[str, str]: A tuple containing:
                - input_type: 'chat', 'command', 'exit', 'empty'
                - value: The user input text or the selected command
        """
        try:
            text = prompt(
                'Enter: ',
                completer=self.slash_completer,
                complete_while_typing=True,
                in_thread=True
            )
            text = text.rstrip()

            if not text:
                return ('empty', '')

            if self.is_exit_command(text):
                return ('exit', text)

            # Check for slash command
            if text.startswith('/') and text in SLASH_COMMANDS:
                return ('command', text)

            # Check for multi-line input start flag (less likely with slash commands)
            if text == "<<EOF":
                lines = []
                while True:
                    line = prompt(in_thread=True) # No completer needed for multi-line content
                    if line == "EOF":
                        break
                    lines.extend(line.split("\n"))
                return ('chat', "\n".join(lines)) # Treat multi-line as chat

            # Regular chat input
            return ('chat', text)
        except EOFError:
            return ('exit', 'EOF') # Treat Ctrl+D as exit

    def _get_last_assistant_message(self, messages: List[Message]) -> Optional[Message]:
        """Find the last message from the assistant."""
        for msg in reversed(messages):
            if msg.role == 'assistant':
                return msg
        return None

    def handle_copy_command(self, command: str, messages: List[Message], last_printed_text_output: Optional[str]) -> bool:
        """Handle the copy command.
        '/copy' copies the last printed text output (message or translation).
        'copy <index>' copies the message by index from history.

        Args:
            command: The copy command (e.g., '/copy' or 'copy 1')
            messages: List of all chat messages (for index-based copy)
            last_printed_text_output: The last text string printed to the console.

        Returns:
            bool: True if command was handled, False otherwise
        """
        parts = command.split()
        if parts[0] == '/copy' and len(parts) == 1:
            # Use the last printed output if available
            if last_printed_text_output:
                pyperclip.copy(last_printed_text_output.strip())
                self.console.print("[green]Copied last output to clipboard[/green]")
                return True
            else:
                self.console.print("[yellow]No output has been printed yet to copy.[/yellow]")
                return True
        elif parts[0] == 'copy' and len(parts) == 2:
             # Keep existing index-based copy functionality (ignores last_printed_text_output)
            try:
                msg_idx = int(parts[1])
                if 0 <= msg_idx < len(messages):
                    content = messages[msg_idx].content
                    if isinstance(content, list):
                        content = next((part['text'] for part in content if part['type'] == 'text'), '')
                    pyperclip.copy(content.strip())
                    self.console.print(f"[green]Copied message [{msg_idx}] to clipboard[/green]")
                else:
                    # Show available message indices
                    msg_indices = [f"[{i}] {msg.role}" for i, msg in enumerate(messages)]
                    self.console.print("[yellow]Invalid message index. Available messages:[/yellow]")
                    for idx in msg_indices:
                        self.console.print(idx)
                return True
            except (IndexError, ValueError):
                self.console.print("[yellow]Invalid copy command. Use '/copy' or 'copy <number>'[/yellow]")
                return True
        else:
             # Handle malformed copy commands
             self.console.print("[yellow]Invalid copy command format. Use '/copy' or 'copy <number>'[/yellow]")
             return True # Indicate handled to prevent further processing

    def handle_translate_command(self, command: str, messages: List[Message]) -> Optional[str]:
        """Handle the translate command. '/translate' finds the last assistant message content.

        Args:
            command: The command string ('/translate')
            messages: List of all chat messages

        Returns:
            Optional[str]: The content of the last assistant message to be translated, or None if not found.
        """
        last_assistant_msg = self._get_last_assistant_message(messages)
        if last_assistant_msg:
            content_to_translate = last_assistant_msg.content
            if isinstance(content_to_translate, list):
                 content_to_translate = next((part['text'] for part in content_to_translate if part['type'] == 'text'), '')
            if content_to_translate:
                 return content_to_translate.strip()
            else:
                 self.console.print("[yellow]Last assistant message has no text content to translate.[/yellow]")
                 return None
        else:
            self.console.print("[yellow]No assistant messages yet to translate.[/yellow]")
            return None

    def handle_save_command(self, command: str, messages: List[Message]) -> bool:
        """Handle the save command. '/save' could save the conversation or last message."""
        # --- Placeholder for actual save logic ---
        self.console.print("[yellow]Save feature not implemented yet.[/yellow]")
        # Example: save_conversation(self.current_chat.id, messages) or save_message(last_message)
        # --- End Placeholder ---
        return True

    def is_exit_command(self, text: str) -> bool:
        """Check if the input is an exit command.

        Args:
            text: The input text to check

        Returns:
            bool: True if the input is an exit command, False otherwise
        """
        return text.lower() in ['exit', 'quit']
