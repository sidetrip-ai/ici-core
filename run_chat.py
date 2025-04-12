#!/usr/bin/env python
"""
Simple launcher for the Discord Gamer Profile Chat interface.
"""

import asyncio
from ici.adapters.chat.gamer_profile_chat import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting chat interface...")
    except Exception as e:
        print(f"\nError: {str(e)}")
        print("If this is an authentication error, please verify your Discord application settings.")
        print("Make sure the redirect URI is set to: http://localhost:8001/callback") 