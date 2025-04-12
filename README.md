# Atlas AI (Built on Sidetrip.ai)

## Overview

Atlas AI is a web-based application designed to assist with travel planning for crypto conferences. It leverages the Perplexity API to generate personalized travel plans based on user input and context.

## Important Note

The Telegram ingestor is currently not functioning as expected, possibly due to Telegram detecting a high number of logins. As a result, you need to manually start the application to ensure it runs correctly.

## Setup Instructions

1. **Clone the Repository**:
   ```bash
   git clone <repository-url>
   cd atlas_travel_app
   ```

2. **Run the Application**: To start the application, run the following command:
   ```bash
   python3 direct_app.py
   ```
   This step is necessary to bypass the issue with the Telegram ingestor and ensure the application initializes properly.

3. **Access the Application**:
   - Open your web browser and navigate to `http://127.0.0.1:5002`.

## Features

- **AI-Powered Travel Planning**: Generates travel plans using the Perplexity API.
- **Web3/Crypto-Styled UI**: Offers a modern, tech-focused user interface.
- **Voice and Text Input**: Accepts both voice and text input for travel requests.

## Troubleshooting

If you encounter any issues while running the application, please refer to the `troubleshoot.md` file for common solutions.