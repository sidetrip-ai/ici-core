"""
Chat interface for interacting with gamer profiles and Discord communities.
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich import box
from rich.markdown import Markdown
from rich.status import Status
import random
from collections import defaultdict

from ici.adapters.ingestors.discord_ingestor import DiscordIngestor, display_status, _console

class GamerProfileChat:
    def __init__(self):
        """Initialize the chat interface."""
        self.ingestor = DiscordIngestor()
        self.user_data = None
        self.guilds_data = None
        self.message_cache = defaultdict(list)  # Store messages for creative mashups

    def _format_user_profile(self, user: Dict[str, Any]) -> Panel:
        """Format user profile data into a rich Panel."""
        content = [
            f"[bold cyan]Username:[/] {user.get('username', 'N/A')}#{user.get('discriminator', '0000')}",
            f"[bold cyan]ID:[/] {user.get('id', 'N/A')}",
            f"[bold cyan]Email:[/] {user.get('email', 'N/A')}",
            f"[bold cyan]Created At:[/] {datetime.fromisoformat(user.get('created_at', '')).strftime('%Y-%m-%d') if user.get('created_at') else 'N/A'}",
            f"[bold cyan]Nitro Type:[/] {user.get('premium_type', 'None')}",
            "",
            "[bold green]Status:[/] " + ("🟢 Online" if user.get('status') == 'online' else "⚫ Offline"),
        ]
        
        if user.get('activities'):
            content.append("\n[bold magenta]Current Activities:[/]")
            for activity in user.get('activities', []):
                content.append(f"• {activity.get('name', 'Unknown Activity')}")
                
        return Panel("\n".join(content), title="[bold]Gamer Profile[/]", border_style="cyan")

    def _format_guilds_table(self, guilds: List[Dict[str, Any]]) -> Table:
        """Format guilds data into a rich Table."""
        table = Table(title="[bold]Gaming Communities[/]", box=box.ROUNDED, show_lines=True)
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Members", style="green", justify="right")
        table.add_column("Role", style="yellow")
        table.add_column("Features", style="magenta")
        
        for guild in guilds:
            role = "👑 Owner" if guild.get('owner') else "👤 Member"
            members = str(guild.get('approximate_member_count', 'N/A'))
            features = ", ".join(guild.get('features', [])) or "Standard"
            table.add_row(
                guild.get('name', 'Unknown'),
                members,
                role,
                features
            )
            
        return table

    def _format_messages(self, channel: Dict[str, Any]) -> Panel:
        """Format channel messages into a rich Panel."""
        messages = channel.get('recent_messages', [])
        if not messages:
            return Panel("No recent messages", title=f"[bold]#{channel.get('name', 'unknown')}[/]", border_style="blue")
            
        content = []
        for msg in messages:
            timestamp = datetime.fromisoformat(msg.get('timestamp')).strftime('%Y-%m-%d %H:%M')
            author = msg.get('author', {}).get('username', 'Unknown')
            content.append(f"[bold cyan]{author}[/] [dim]{timestamp}[/]")
            content.append(f"{msg.get('content', 'No content')}\n")
            
        return Panel(
            "\n".join(content),
            title=f"[bold]#{channel.get('name', 'unknown')}[/]",
            border_style="blue"
        )

    async def initialize(self) -> None:
        """Initialize the chat interface and Discord connection."""
        try:
            _console.print("[bold blue]🎮 Welcome to Discord Gaming Hub![/]")
            
            with display_status("[bold blue]🔄 Connecting to Discord...[/]"):
                await self.ingestor.initialize()
            
            with display_status("[bold blue]📥 Loading your Discord data...[/]"):
                await self.refresh_data()
            
            _console.print("[bold green]✓ Ready to chat![/]")
            
        except Exception as e:
            _console.print(f"[bold red]✗ Failed to connect: {str(e)}[/]")
            raise

    async def refresh_data(self) -> None:
        """Refresh user and guilds data."""
        try:
            with display_status("[bold yellow]Refreshing Discord data..."):
                data = await self.ingestor.fetch_full_data()
                self.user_data = data.get('user', {})
                self.guilds_data = data.get('guilds', [])
                
                # Show summary of fetched data
                _console.print("\n[bold green]✓ Data refresh complete:[/]")
                _console.print(f"[dim]• Profile loaded: {self.user_data.get('username', 'Unknown')}[/]")
                _console.print(f"[dim]• Servers available: {len(self.guilds_data)}[/]")
                
        except Exception as e:
            _console.print(f"[bold red]✗ Error refreshing data: {str(e)}[/]")
            raise

    async def show_profile(self) -> None:
        """Display the user's gaming profile."""
        if not self.user_data:
            with display_status("Refreshing profile data..."):
                await self.refresh_data()
        
        _console.print(self._format_user_profile(self.user_data))
        
    async def show_communities(self) -> None:
        """Display the user's gaming communities."""
        if not self.guilds_data:
            with display_status("Refreshing server data..."):
                await self.refresh_data()
            
        _console.print(self._format_guilds_table(self.guilds_data))

    async def show_guild_messages(self, guild_id: Optional[str] = None) -> None:
        """Display messages from a specific guild or let user choose one."""
        if not self.guilds_data:
            with display_status("Loading server data..."):
                await self.refresh_data()
            
        if not self.guilds_data:
            _console.print("[bold red]No servers available to display.[/]")
            return
            
        if not guild_id:
            # Show guild selection menu
            _console.print("\n[bold cyan]Available servers:[/]")
            for i, guild in enumerate(self.guilds_data, 1):
                _console.print(f"{i}. {guild.get('name', 'Unknown')}")
            
            choice = Prompt.ask(
                "\nSelect a server number",
                choices=[str(i) for i in range(1, len(self.guilds_data) + 1)]
            )
            guild = self.guilds_data[int(choice) - 1]
        else:
            guild = next((g for g in self.guilds_data if g['id'] == guild_id), None)
            if not guild:
                _console.print(f"[bold red]Server with ID {guild_id} not found.[/]")
                return
        
        with display_status(f"Loading messages for {guild['name']}..."):
            channels = guild.get('channels', [])
            if not channels:
                _console.print("[bold yellow]No accessible channels in this server.[/]")
                return
            
            for channel in channels:
                _console.print(self._format_messages(channel))

    def _create_poetic_mashup(self, messages: List[Dict[str, Any]], style: str = "random") -> str:
        """Create a poetic mashup from cached messages."""
        if not messages:
            return "No messages available for creative mashup."

        # Extract message contents
        contents = [msg.get('content', '') for msg in messages if msg.get('content')]
        if not contents:
            return "No message contents available for mashup."

        # Different mashup styles
        if style == "haiku":
            # Create a simple haiku-like structure
            lines = random.sample(contents, min(3, len(contents)))
            return "\n".join(f"> {line[:30]}" for line in lines)
        elif style == "conversation":
            # Create a back-and-forth conversation
            selected = random.sample(contents, min(4, len(contents)))
            return "\n".join(f"{'A' if i % 2 == 0 else 'B'}: {line[:40]}..." for i, line in enumerate(selected))
        else:  # random style
            # Create a random arrangement
            selected = random.sample(contents, min(5, len(contents)))
            return "\n".join(f"✨ {line[:35]}..." for line in selected)

    async def create_chat_mashup(self) -> None:
        """Create and display a creative mashup of chat messages."""
        if not self.guilds_data:
            with display_status("Loading server data..."):
                await self.refresh_data()

        # Let user choose a server
        _console.print("\n[bold cyan]Choose a server for creative mashup:[/]")
        for i, guild in enumerate(self.guilds_data, 1):
            _console.print(f"{i}. {guild.get('name', 'Unknown')}")
        
        choice = Prompt.ask(
            "\nSelect a server number",
            choices=[str(i) for i in range(1, len(self.guilds_data) + 1)]
        )
        guild = self.guilds_data[int(choice) - 1]

        # Choose mashup style
        style = Prompt.ask(
            "\nChoose mashup style",
            choices=["random", "haiku", "conversation"],
            default="random"
        )

        with display_status(f"Creating {style} mashup from {guild['name']}..."):
            # Collect messages from all channels
            all_messages = []
            for channel in guild.get('channels', []):
                messages = channel.get('recent_messages', [])
                all_messages.extend(messages)

            # Create and display mashup
            mashup = self._create_poetic_mashup(all_messages, style)
            _console.print(Panel(
                Markdown(mashup),
                title=f"[bold]Creative Mashup ({style})[/]",
                border_style="magenta"
            ))

    async def chat_loop(self) -> None:
        """Main chat interface loop."""
        try:
            await self.initialize()
            
            while True:
                _console.print("\n[bold cyan]What would you like to do?[/]")
                _console.print("1. View your gaming profile")
                _console.print("2. Browse your communities")
                _console.print("3. View server messages")
                _console.print("4. Create chat mashup")
                _console.print("5. Refresh data")
                _console.print("6. Exit")
                
                choice = Prompt.ask("Select an option", choices=["1", "2", "3", "4", "5", "6"])
                
                if choice == "1":
                    await self.show_profile()
                elif choice == "2":
                    await self.show_communities()
                elif choice == "3":
                    await self.show_guild_messages()
                elif choice == "4":
                    await self.create_chat_mashup()
                elif choice == "5":
                    await self.refresh_data()
                elif choice == "6":
                    break
                
        except KeyboardInterrupt:
            _console.print("\n[yellow]Shutting down gracefully...[/]")
        except Exception as e:
            _console.print(f"\n[bold red]Error: {str(e)}[/]")
        finally:
            if hasattr(self.ingestor, 'close'):
                await self.ingestor.close()

async def main():
    """Main entry point."""
    chat = GamerProfileChat()
    await chat.chat_loop()

if __name__ == "__main__":
    asyncio.run(main()) 