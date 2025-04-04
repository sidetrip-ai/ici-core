"""
Orchestrator module.

This package provides concrete implementations of the Orchestrator interface
for coordinating the processing of user queries from validation to response generation.

The DefaultOrchestrator uses the DefaultIngestionPipeline, supporting both
Telegram and WhatsApp data sources.
"""

from ici.adapters.orchestrators.default_orchestrator import DefaultOrchestrator

__all__ = ["DefaultOrchestrator"] 