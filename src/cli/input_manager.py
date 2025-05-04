import sys
import pyperclip
from typing import List, Optional, Tuple, Iterable
from prompt_toolkit import prompt
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from rich.console import Console
from chat.models import Message

# --- Command Definitions ---
COMMAND_DISPLAY_TEXT = {
    "/copy": "copy(c)",
    "/translate": "translate(t)",
    "/save": "save(s)",
    "/quit": "quit(q)"
}
# Map shortcuts and full commands to canonical command name (or 'exit')
COMMAND_MAP = {
    "/c": "/copy",
    "/copy": "/copy",
    "/t": "/translate",
    "/translate": "/translate",
    "/s": "/save",
    "/save": "/save",
    "/q": "exit",
    "/quit": "exit",
    "exit": "exit", # Allow typing 'exit' directly
    "quit": "exit"  # Allow typing 'quit' directly
}
# List of commands/shortcuts that trigger the completer
COMMAND_TRIGGERS = list(COMMAND_MAP.keys())
# --- End Command Definitions ---

class SlashCommandCompleter(Completer):
    """Completer for slash commands with manual filtering and display text."""
    def __init__(self, command_map: dict, display_text: dict):
        # Store the mappings
        self.command_map = command_map
        self.display_text = display_text
        # Get potential inputs (shortcuts and full commands starting with /)
        self.potential_inputs = [k for k in command_map.keys() if k.startswith('/')]

    def get_completions(self, document: Document, complete_event) -> Iterable[Completion]:
        text = document.text_before_cursor.lower()
        # print(f\"DEBUG: Completer called. Text: '{text}'\") # DEBUG

        if text.startswith('/'):
            # print(\"DEBUG: Text starts with /") # DEBUG
            matches_by_canonical = {}

            # 1. Find all matches and group by canonical command
            for potential_input in self.potential_inputs:
                if potential_input.startswith(text):
                    # print(f\"DEBUG: '{potential_input}' starts with '{text}'\") # DEBUG
                    canonical_command = self.command_map[potential_input]
                    if canonical_command not in matches_by_canonical:
                        matches_by_canonical[canonical_command] = []
                    matches_by_canonical[canonical_command].append(potential_input)

            # print(f\"DEBUG: Matches found: {matches_by_canonical}\") # DEBUG
            # 2. For each canonical command, yield the best (shortest) match
            # yielded_count = 0 # DEBUG
            for canonical_command, matching_inputs in matches_by_canonical.items():
                # Sort matches by length (shortest first)
                matching_inputs.sort(key=len)
                best_match = matching_inputs[0] # The shortest one is preferred
                # print(f\"DEBUG: Canonical: {canonical_command}, Best match: {best_match}\") # DEBUG

                # Determine display text and start position
                if best_match == text:
                    display = best_match
                    # start_pos = 0 # Revert this
                else:
                     if canonical_command == 'exit':
                         display = self.display_text.get('/quit', best_match)
                     else:
                         display = self.display_text.get(canonical_command, best_match)
                     # start_pos = -len(text) # This is the default

                # Always use -len(text) for start_position
                start_pos = -len(text)

                yield Completion(
                    best_match,  # Complete with the best match (e.g., /c)
                    start_position=start_pos,
                    display=display # Display shortcut or formatted text
                )
                # yielded_count += 1 # DEBUG
            # print(f\"DEBUG: Yielded {yielded_count} completions.") # DEBUG
        # else:
             # print(\"DEBUG: Text does not start with /. No completions.\") # DEBUG

class InputManager:
    def __init__(self, console: Console):
        self.console = console
        self.slash_completer = SlashCommandCompleter(COMMAND_MAP, COMMAND_DISPLAY_TEXT)

    def get_input(self) -> Tuple[str, str]:
        """Get user input with support for multi-line input and slash commands.

        Returns:
            Tuple[str, str]: A tuple containing:
                - input_type: 'chat', 'command', 'exit', 'empty'
                - value: The user input text or the selected command
        """
        try:
            text_input = prompt(
                'Enter: ',
                completer=self.slash_completer,
                complete_while_typing=True, # <-- Re-enable this
                in_thread=True
            )
            text_input = text_input.rstrip()
            normalized_text = text_input.lower() # Use lowercase for map lookup

            if not text_input:
                return ('empty', '')

            # Check if the input (lowercase) is a known command/shortcut/exit word
            if normalized_text in COMMAND_MAP:
                mapped_value = COMMAND_MAP[normalized_text]
                if mapped_value == 'exit':
                    return ('exit', text_input) # Return original text for exit message context
                else:
                    # Return the canonical command name (e.g., /copy)
                    return ('command', mapped_value)

            # Check for multi-line input start flag
            if text_input == "<<EOF":
                lines = []
                while True:
                    line = prompt(in_thread=True) # No completer needed for multi-line content
                    if line == "EOF":
                        break
                    lines.extend(line.split("\n"))
                return ('chat', "\n".join(lines)) # Treat multi-line as chat

            # Regular chat input
            return ('chat', text_input)
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
