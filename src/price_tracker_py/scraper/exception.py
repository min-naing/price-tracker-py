class ScraperStructureError(Exception):
    """Raised when expected page structure is missing or invalid."""


class TooManyItemFailuresError(ScraperStructureError):
    """Raised when too many items fail on a single page."""


class RateLimitedError(Exception):
    """Raised when the server responds with HTTP 429."""
