"""
Orchestrator module.

This package provides concrete implementations of the Orchestrator interface
for coordinating the processing of user queries from validation to response generation.

The DefaultOrchestrator uses the DefaultIngestionPipeline, supporting both
Telegram and WhatsApp data sources.

The TravelOrchestrator extends the DefaultOrchestrator to add travel planning capabilities
using Perplexity API and Telegram chat data.
"""

from ici.adapters.orchestrators.default_orchestrator import DefaultOrchestrator
from ici.adapters.orchestrators.travel_orchestrator import TravelOrchestrator

__all__ = ["DefaultOrchestrator", "TravelOrchestrator"] 