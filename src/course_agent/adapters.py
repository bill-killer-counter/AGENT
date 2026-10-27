"""Stable seams for replacing A's mock modules with B/C implementations."""
from .mock_memory import MockMemory
from .mock_processor import process_document

PROCESSOR = process_document
MEMORY = MockMemory()
