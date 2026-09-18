"""Structured domain exceptions for Zero Gaze."""


class ZeroGazeError(Exception):
    """Base exception for all Zero Gaze errors."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class IngestionError(ZeroGazeError):
    """Raised when arXiv ingestion or PDF markdown conversion fails."""


class DiscoveryError(ZeroGazeError):
    """Raised when code or benchmark dataset discovery fails."""


class ExtractionError(ZeroGazeError):
    """Raised when LLM extraction or structured parsing fails."""


class GraphExecutionError(ZeroGazeError):
    """Raised when graph execution encounters an unrecoverable failure."""
