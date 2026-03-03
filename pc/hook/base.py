from abc import ABC, abstractmethod
from typing import Callable


class KeyboardHookBase(ABC):
    """Abstract base class for platform-specific keyboard hooks."""

    @abstractmethod
    def start(self, on_press: Callable, on_release: Callable) -> None:
        """
        Start listening for keyboard events.

        Args:
            on_press:   Called with (modifier: int, keycode: int) on key press.
            on_release: Called with (modifier: int, keycode: int) on key release.
        """

    @abstractmethod
    def stop(self) -> None:
        """Stop listening and release resources."""

    @abstractmethod
    def set_suppress(self, suppress: bool) -> None:
        """Enable or disable OS-level key suppression (prevent delivery to PC)."""

    @abstractmethod
    def shutdown(self) -> None:
        """Gracefully shut down the hook on app exit."""
