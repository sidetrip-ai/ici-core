"""
Simple runner script for the Discord Gaming Hub chat interface.
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ici.adapters.chat.gamer_profile_chat import GamerProfileChat
from rich.console import Console

console = Console()

async def main():
    """Main entry point for the Discord Gaming Hub."""
    try:
        chat = GamerProfileChat()
        await chat.chat_loop()
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down gracefully...[/]")
    except Exception as e:
        console.print(f"\n[bold red]Error: {str(e)}[/]")
        raise
    finally:
        # Ensure we cleanup properly
        if hasattr(chat, 'ingestor') and hasattr(chat.ingestor, 'close'):
            await chat.ingestor.close()

if __name__ == "__main__":
    try:
        # Windows specific event loop policy
        if asyncio.get_event_loop_policy().__class__.__name__ == 'WindowsProactorEventLoopPolicy':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        asyncio.run(main())
    except Exception as e:
        console.print(f"[bold red]Fatal error: {str(e)}[/]")
        sys.exit(1) 