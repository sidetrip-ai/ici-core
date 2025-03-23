"""
Banner printing utility for ICI Core.

This module provides functions for displaying ASCII art banners
for the ICI Core application.
"""

def print_banner():
    """Print ASCII art banner for ICI Core"""
    banner = r"""

   _____ _     _      _        _       
  / ____(_)   | |    | |      (_)      
 | (___  _  __| | ___| |_ _ __ _ _ __  
  \___ \| |/ _` |/ _ \ __| '__| | '_ \ 
  ____) | | (_| |  __/ |_| |  | | |_) |
 |_____/|_|\__,_|\___|\__|_|  |_| .__/ 
                                | |    
                                |_|    
                                               
    Intelligent Consciousness Interface Core
    """
    print(banner)
    print("=" * 50) 