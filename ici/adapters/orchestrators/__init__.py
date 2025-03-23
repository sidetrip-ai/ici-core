"""
Orchestrator module.

This package provides concrete implementations of the Orchestrator interface
for coordinating the processing of user queries from validation to response generation.
"""

from ici.adapters.orchestrators.telegram_orchestrator import TelegramOrchestrator

__all__ = ["TelegramOrchestrator"] 