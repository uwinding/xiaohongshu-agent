class CollectorError(Exception):
    """Base collector exception."""


class LoginExpired(CollectorError):
    """Login state is invalid or expired."""


class NoteNotFound(CollectorError):
    """Note not found or has been removed."""


class RateLimitError(CollectorError):
    """Rate limited by XHS."""


class DataFetchError(CollectorError):
    """Generic data fetch failure."""
