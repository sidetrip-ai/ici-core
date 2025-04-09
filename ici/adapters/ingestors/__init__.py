"""
Ingestor implementations for various data sources.
""" 

from ici.adapters.ingestors.telegram import TelegramIngestor
from ici.adapters.ingestors.whatsapp import WhatsAppIngestor

__all__ = ["TelegramIngestor", "WhatsAppIngestor"] 