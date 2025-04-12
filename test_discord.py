"""
Test script for Discord ingestor.
"""

import asyncio
import logging
from ici.adapters.ingestors.discord_ingestor import DiscordIngestor

async def main():
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Create and initialize the Discord ingestor
    ingestor = DiscordIngestor()
    try:
        print("Initializing Discord ingestor...")
        await ingestor.initialize()
        
        print("\nFetching Discord data...")
        data = await ingestor.fetch_full_data()
        
        print("\nFetch successful!")
        print(f"User data: {data['user']['username']}#{data['user']['discriminator']}")
        print(f"Number of guilds: {len(data['guilds'])}")
        
    except Exception as e:
        print(f"\nError: {str(e)}")
    finally:
        print("\nCleaning up...")
        await ingestor.close()

if __name__ == "__main__":
    asyncio.run(main()) 