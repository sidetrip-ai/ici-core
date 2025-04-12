import logging
import os
from dotenv import load_dotenv
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    load_dotenv()  # Load environment variables from .env file
    
    logging.info("Starting LinkedIn data fetching application...")
    
    # Check if required environment variables are set
    if not os.getenv('LINKEDIN_CLIENT_ID') or not os.getenv('LINKEDIN_CLIENT_SECRET'):
        logging.error("Error: LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET must be set in the .env file.")
        return

    try:
        # Dynamically import the ingestor to avoid circular dependencies if run directly
        from ici.ingestors.linkedin_ingestor import LinkedInIngestor
        
        logging.info("Initializing LinkedIn Ingestor...")
        # Configuration dictionary (can be empty for now or load from config.yaml if needed)
        config = {} 
        ingestor = LinkedInIngestor(config)
        
        logging.info("Authentication successful. Fetching profile data...")
        # Fetch data (which is now just the profile via OpenID Connect)
        data = ingestor.fetch_full_data()
        
        if data and 'profile' in data:
            logging.info("Profile data fetched successfully:")
            # Pretty print the profile dictionary
            print("\n--- User Profile ---")
            print(json.dumps(data['profile'], indent=4))
            print("--------------------")
        else:
            logging.warning("No profile data was fetched.")
            
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        # Optionally print traceback for debugging
        # import traceback
        # traceback.print_exc()

if __name__ == "__main__":
    main() 