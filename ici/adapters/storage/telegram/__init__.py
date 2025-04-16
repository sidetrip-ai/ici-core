"""
Telegram conversation storage module.

This module provides tools for storing and managing Telegram conversation data
in a file-based JSON format with processing status tracking.
"""

from ici.adapters.storage.telegram.file_manager import FileManager
from ici.adapters.storage.telegram.enhanced_file_manager import EnhancedFileManager
from ici.adapters.storage.telegram.serializer import ConversationSerializer
from ici.utils.utils import (
    FileSystemLock,
    BackupManager,
    get_backup_frequency,
    atomic_write,
    batch_process_files
)
from ici.utils.conversation_utils import (
    is_personal_chat,
    is_bot_chat, 
    is_private_group,
    filter_conversations,
    get_fetch_mode_from_config,
    add_conversation_type_metadata
)
from ici.utils.incremental_utils import (
    get_latest_message_timestamp,
    update_conversation_metadata, 
    should_fetch_incrementally,
    merge_conversations,
    prepare_min_id_for_fetch
)

__all__ = [
    'FileManager',
    'EnhancedFileManager',
    'ConversationSerializer',
    'FileSystemLock',
    'BackupManager',
    'get_backup_frequency',
    'atomic_write',
    'batch_process_files',
    'is_personal_chat',
    'is_bot_chat',
    'is_private_group',
    'filter_conversations',
    'get_fetch_mode_from_config',
    'add_conversation_type_metadata',
    'get_latest_message_timestamp',
    'update_conversation_metadata',
    'should_fetch_incrementally', 
    'merge_conversations',
    'prepare_min_id_for_fetch'
] 