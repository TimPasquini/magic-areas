"""Unit tests for core.listener_registry module."""

import logging
from unittest.mock import MagicMock, call, patch

import pytest

from custom_components.magic_areas.core.listener_registry import (
    ListenerRegistry,
)


class TestListenerRegistryInitialization:
    """Tests for ListenerRegistry initialization."""

    def test_init_default(self) -> None:
        """Test initialization with default logger."""
        registry = ListenerRegistry()
        assert registry.count == 0

    def test_init_with_logger_name(self) -> None:
        """Test initialization with custom logger name."""
        registry = ListenerRegistry(logger_name="test.module")
        assert registry.count == 0


class TestTrack:
    """Tests for listener tracking."""

    def test_track_single_listener(self) -> None:
        """Test tracking a single listener."""
        registry = ListenerRegistry()
        remove_fn = MagicMock()

        registry.track("test_listener", remove_fn)

        assert registry.count == 1

    def test_track_multiple_listeners(self) -> None:
        """Test tracking multiple listeners."""
        registry = ListenerRegistry()
        remove_fns = [MagicMock() for _ in range(3)]

        for i, remove_fn in enumerate(remove_fns):
            registry.track(f"listener_{i}", remove_fn)

        assert registry.count == 3

    def test_track_preserves_order(self) -> None:
        """Test that listeners are tracked in order."""
        registry = ListenerRegistry()
        names = ["first", "second", "third"]
        remove_fns = [MagicMock(name=name) for name in names]

        for name, remove_fn in zip(names, remove_fns):
            registry.track(name, remove_fn)

        # Cleanup and verify order
        registry.cleanup()
        for i, remove_fn in enumerate(remove_fns):
            assert remove_fn.call_count == 1

    def test_track_logging(self, caplog) -> None:
        """Test that tracking logs debug messages."""
        registry = ListenerRegistry()

        with caplog.at_level(logging.DEBUG):
            registry.track("test_listener", MagicMock())

        assert "Tracked listener: test_listener" in caplog.text
        assert "total: 1" in caplog.text


class TestCleanup:
    """Tests for listener cleanup."""

    def test_cleanup_calls_remove_functions(self) -> None:
        """Test that cleanup calls all registered remove functions."""
        registry = ListenerRegistry()
        remove_fns = [MagicMock() for _ in range(3)]

        for i, remove_fn in enumerate(remove_fns):
            registry.track(f"listener_{i}", remove_fn)

        registry.cleanup()

        for remove_fn in remove_fns:
            remove_fn.assert_called_once()

    def test_cleanup_clears_listeners(self) -> None:
        """Test that cleanup clears the listener list."""
        registry = ListenerRegistry()
        registry.track("listener_1", MagicMock())
        registry.track("listener_2", MagicMock())

        assert registry.count == 2
        registry.cleanup()
        assert registry.count == 0

    def test_cleanup_empty_registry(self, caplog) -> None:
        """Test cleanup on empty registry is safe."""
        registry = ListenerRegistry()

        with caplog.at_level(logging.DEBUG):
            registry.cleanup()

        assert registry.count == 0
        assert "No listeners to clean up" in caplog.text

    def test_cleanup_logging(self, caplog) -> None:
        """Test that cleanup logs debug messages."""
        registry = ListenerRegistry()
        registry.track("listener_1", MagicMock())
        registry.track("listener_2", MagicMock())

        with caplog.at_level(logging.DEBUG):
            registry.cleanup()

        assert "Cleaning up 2 listeners" in caplog.text
        assert "Cleaned up listener: listener_1" in caplog.text
        assert "Cleaned up listener: listener_2" in caplog.text


class TestCleanupErrorHandling:
    """Tests for error handling during cleanup."""

    def test_cleanup_one_listener_raises(self) -> None:
        """Test that one listener raising doesn't stop others."""
        registry = ListenerRegistry()
        remove_fn_1 = MagicMock()
        remove_fn_2 = MagicMock(side_effect=RuntimeError("test error"))
        remove_fn_3 = MagicMock()

        registry.track("listener_1", remove_fn_1)
        registry.track("listener_2", remove_fn_2)
        registry.track("listener_3", remove_fn_3)

        # Should not raise
        registry.cleanup()

        # All should have been called
        remove_fn_1.assert_called_once()
        remove_fn_2.assert_called_once()
        remove_fn_3.assert_called_once()

    def test_cleanup_error_logging(self, caplog) -> None:
        """Test that errors are logged without raising."""
        registry = ListenerRegistry()
        remove_fn = MagicMock(side_effect=RuntimeError("test error"))
        registry.track("failing_listener", remove_fn)

        with caplog.at_level(logging.ERROR):
            registry.cleanup()

        assert "Error cleaning up listener 'failing_listener'" in caplog.text
        assert "test error" in caplog.text

    def test_cleanup_all_listeners_raise(self) -> None:
        """Test cleanup when all listeners raise."""
        registry = ListenerRegistry()
        remove_fns = [
            MagicMock(side_effect=RuntimeError(f"error_{i}"))
            for i in range(3)
        ]

        for i, remove_fn in enumerate(remove_fns):
            registry.track(f"listener_{i}", remove_fn)

        # Should not raise
        registry.cleanup()

        # All should have been called
        for remove_fn in remove_fns:
            assert remove_fn.call_count == 1


class TestCleanupIdempotent:
    """Tests for cleanup idempotency."""

    def test_cleanup_twice(self) -> None:
        """Test that calling cleanup twice doesn't error."""
        registry = ListenerRegistry()
        remove_fn = MagicMock()
        registry.track("listener_1", remove_fn)

        registry.cleanup()
        assert registry.count == 0

        # Second cleanup should not error
        registry.cleanup()
        assert registry.count == 0

    def test_cleanup_twice_second_doesn_not_call_remove(self) -> None:
        """Test that second cleanup doesn't call remove functions."""
        registry = ListenerRegistry()
        remove_fn = MagicMock()
        registry.track("listener_1", remove_fn)

        registry.cleanup()
        assert remove_fn.call_count == 1

        # Second cleanup should not call remove again
        registry.cleanup()
        assert remove_fn.call_count == 1


class TestLogging:
    """Tests for logging behavior."""

    def test_logger_name_affects_output(self) -> None:
        """Test that custom logger name is used."""
        with patch("custom_components.magic_areas.core.listener_registry.logging") as mock_logging:
            registry = ListenerRegistry(logger_name="custom.logger")
            mock_logging.getLogger.assert_called_once_with("custom.logger")

    def test_debug_logging_on_track(self, caplog) -> None:
        """Test debug logging when tracking listener."""
        registry = ListenerRegistry()

        with caplog.at_level(logging.DEBUG):
            registry.track("my_listener", MagicMock())
            registry.track("another_listener", MagicMock())

        messages = caplog.text
        assert "Tracked listener: my_listener" in messages
        assert "Tracked listener: another_listener" in messages
        assert "total: 1" in messages
        assert "total: 2" in messages

    def test_debug_logging_on_cleanup(self, caplog) -> None:
        """Test debug logging when cleaning up listeners."""
        registry = ListenerRegistry()
        registry.track("listener_1", MagicMock())
        registry.track("listener_2", MagicMock())

        with caplog.at_level(logging.DEBUG):
            registry.cleanup()

        assert "Cleaning up 2 listeners" in caplog.text


class TestEdgeCases:
    """Tests for edge cases."""

    def test_track_with_none_name(self) -> None:
        """Test tracking with empty name (edge case)."""
        registry = ListenerRegistry()
        registry.track("", MagicMock())
        assert registry.count == 1

    def test_track_same_name_multiple_times(self) -> None:
        """Test tracking listeners with the same name."""
        registry = ListenerRegistry()
        remove_fn_1 = MagicMock()
        remove_fn_2 = MagicMock()

        registry.track("same_name", remove_fn_1)
        registry.track("same_name", remove_fn_2)

        assert registry.count == 2

        registry.cleanup()
        remove_fn_1.assert_called_once()
        remove_fn_2.assert_called_once()

    def test_remove_function_returns_none(self) -> None:
        """Test that remove function can return None."""
        registry = ListenerRegistry()
        remove_fn = MagicMock(return_value=None)

        registry.track("listener", remove_fn)
        registry.cleanup()

        remove_fn.assert_called_once()

    def test_count_property_accurate(self) -> None:
        """Test that count property is always accurate."""
        registry = ListenerRegistry()

        assert registry.count == 0

        registry.track("l1", MagicMock())
        assert registry.count == 1

        registry.track("l2", MagicMock())
        assert registry.count == 2

        registry.cleanup()
        assert registry.count == 0

    def test_listeners_called_in_registration_order(self) -> None:
        """Test that listeners are called in registration order."""
        registry = ListenerRegistry()
        call_order = []

        def make_callback(name: str):
            def callback():
                call_order.append(name)
            return callback

        registry.track("first", make_callback("first"))
        registry.track("second", make_callback("second"))
        registry.track("third", make_callback("third"))

        registry.cleanup()

        assert call_order == ["first", "second", "third"]

    def test_long_listener_name(self) -> None:
        """Test tracking listener with very long name."""
        registry = ListenerRegistry()
        long_name = "x" * 1000
        registry.track(long_name, MagicMock())
        assert registry.count == 1

    def test_special_characters_in_name(self) -> None:
        """Test tracking listener with special characters in name."""
        registry = ListenerRegistry()
        names = [
            "listener_with_underscore",
            "listener-with-dash",
            "listener.with.dot",
            "listener:with:colon",
            "listener|with|pipe",
        ]

        for name in names:
            registry.track(name, MagicMock())

        assert registry.count == len(names)
        registry.cleanup()
        assert registry.count == 0
