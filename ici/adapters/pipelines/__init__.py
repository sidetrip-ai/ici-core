"""
Pipeline adapter implementations for the ICI framework.

This module contains implementations of the IngestionPipeline interface,
which orchestrate the data flow between various components.
"""

from ici.adapters.pipelines.telegram import TelegramIngestionPipeline 

__all__ = ["TelegramIngestionPipeline"]