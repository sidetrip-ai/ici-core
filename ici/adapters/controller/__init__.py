"""
Controller module.

This package provides controllers for managing the different components
of the system. The IngestController manages background data ingestion,
while query processing is handled directly by the QueryOrchestrator.
"""

from ici.adapters.controller.ingest_controller import IngestController
from ici.adapters.controller.api_controller import APIController
from ici.adapters.controller.command_line import command_line_controller

__all__ = ["IngestController", "APIController", "command_line_controller"]