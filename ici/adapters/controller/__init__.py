"""
Controller implementations for the ICI Framework.

This module contains adapter implementations for the Controller interface,
providing controller functionality for the ICI Framework.
"""

# Import adapters
from .command_line import command_line_controller 

__all__ = ["command_line_controller"]