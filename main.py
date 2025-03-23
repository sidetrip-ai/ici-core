import asyncio
import sys
import traceback

from ici.adapters.controller import command_line_controller

if __name__ == "__main__":
    # Run the main function
    try:
        print("Starting main function...")
        exit_code = asyncio.run(command_line_controller())
        sys.exit(exit_code)
    except Exception as e:
        print(f"Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1) 