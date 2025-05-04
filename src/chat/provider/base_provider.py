from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from chat.models import Message, Chat
from cli.display_manager import DisplayManager

class BaseProvider(ABC):
    def __init__(self):
        self.display_manager: Optional[DisplayManager] = None

    def set_display_manager(self, display_manager: DisplayManager):
        """Set the display manager for potential use by providers."""
        self.display_manager = display_manager

    @abstractmethod
    async def call_chat_completions(self, messages: List[Message], chat: Optional[Chat] = None, system_prompt: Optional[str] = None) -> Tuple[Message, Optional[str]]:
        """Get a chat response from the provider.
        
        Args:
            messages: List of Message objects
            system_prompt: Optional system prompt to add at the start
            
        Returns:
            Message: The assistant's response message
            external_id: Optional external ID for the chat
            
        Raises:
            Exception: If API call fails
        """
        pass

    @abstractmethod
    async def translate_text(self, text: str, target_language: str) -> Optional[str]:
        """Translate the given text using the provider's model.

        Args:
            text: The text to translate.
            target_language: The target language (e.g., 'Chinese', 'zh-CN').

        Returns:
            Optional[str]: The translated text, or None if translation fails.
        """
        pass
