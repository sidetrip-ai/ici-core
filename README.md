# Personality Analysis Telegram Bot

A Telegram bot that analyzes user messages and provides personality insights using MBTI assessment and message analysis.

## Features

- Message analysis for personality traits
- MBTI personality assessment
- Personalized insights and recommendations
- Message history tracking
- User data persistence

## Setup Instructions

1. **Create a Telegram Bot**
   - Message [@BotFather](https://t.me/BotFather) on Telegram
   - Use `/newbot` command to create a new bot
   - Save the bot token provided

2. **Get Telegram API Credentials**
   - Visit [my.telegram.org](https://my.telegram.org)
   - Log in with your phone number
   - Go to "API development tools"
   - Create a new application
   - Save the `api_id` and `api_hash`

3. **Environment Setup**
   ```bash
   # Clone the repository
   git clone <repository-url>
   cd personality-bot

   # Create and activate virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Install dependencies
   pip install -r requirements.txt

   # Download NLTK data
   python -c "import nltk; nltk.download('vader_lexicon')"
   ```

4. **Configure Environment Variables**
   Create a `.env` file in the project root:
   ```
   TELEGRAM_API_ID=your_api_id
   TELEGRAM_API_HASH=your_api_hash
   TELEGRAM_BOT_TOKEN=your_bot_token
   ```

## Running the Bot

1. **Local Development**
   ```bash
   python personality_bot.py
   ```

2. **Production Deployment**
   - Use a cloud service like Heroku, DigitalOcean, or AWS
   - Set up environment variables in your hosting platform
   - Deploy the code
   - Use a process manager like PM2 or Supervisor to keep the bot running

## Available Commands

- `/start` - Start the bot and see welcome message
- `/analyze` - Analyze your recent messages
- `/mbti` - Start MBTI personality assessment
- `/results` - View your latest analysis results
- `/retake` - Retake the assessment
- `/help` - Show available commands

## Data Storage

The bot stores user data in a JSON file (`personality_db.json`). For production use, consider:
- Using a proper database (PostgreSQL, MongoDB)
- Implementing data encryption
- Adding data retention policies

## Security Considerations

- Keep your API credentials secure
- Implement rate limiting
- Add user authentication if needed
- Regularly backup user data
- Follow Telegram's bot guidelines

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - See LICENSE file for details
