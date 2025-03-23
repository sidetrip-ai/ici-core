"""
Preprocessor adapters for the ICI framework.

This module contains implementations of the Preprocessor interface for
different data sources, transforming raw data into a standardized format.
"""

from ici.adapters.preprocessors.telegram import TelegramPreprocessor

__all__ = [
    "TelegramPreprocessor",
] 