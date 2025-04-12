"""
Ingestor implementations for various data sources.
""" 

from ici.adapters.ingestors.telegram import TelegramIngestor
from ici.adapters.ingestors.whatsapp import WhatsAppIngestor
from ici.adapters.ingestors.github import GitHubIngestor

__all__ = ["TelegramIngestor", "WhatsAppIngestor", "GitHubIngestor"] 