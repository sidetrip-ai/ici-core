# Using Environment Variables with Config

This project supports loading sensitive configuration values from environment variables to avoid storing secrets in plain text within `config.yaml`.

## How It Works

The configuration system automatically replaces variable references in the `config.yaml` file with values from your environment variables at runtime. You can use either of these formats:

- `$VARIABLE_NAME` - Simple format
- `${VARIABLE_NAME}` - Braced format (useful when the variable name is adjacent to other text)

## Setup Instructions

1. Copy the `.env.example` file to a new file called `.env`:

   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file and replace the placeholder values with your actual credentials:

   ```
   TELEGRAM_API_ID=12345678
   TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
   ```

3. Load the environment variables before running the application:

   ```bash
   # Linux/macOS
   source .env && python your_script.py
   
   # Windows (cmd)
   set /p VARS=<.env && python your_script.py
   
   # Windows (PowerShell)
   Get-Content .env | ForEach-Object { $var = $_.Split('='); if($var[0] -and $var[1]) { [System.Environment]::SetEnvironmentVariable($var[0], $var[1]) } }
   python your_script.py
   ```

   Alternatively, use a package like `python-dotenv` to load variables automatically:

   ```bash
   pip install python-dotenv
   ```

   And in your script:

   ```python
   from dotenv import load_dotenv
   
   load_dotenv()  # Load .env file
   ```

## Example Config with Environment Variables

Here's an example of how to use environment variables in your `config.yaml`:

```yaml
generator:
  api_key: ${GENERATOR_API_KEY}
  model: deepseek-r1:7b
  provider: ollama
  type: langchain

ingestors:
  telegram:
    api_hash: ${TELEGRAM_API_HASH}
    api_id: ${TELEGRAM_API_ID}
    phone_number: ${TELEGRAM_PHONE_NUMBER}
    session_string: ${TELEGRAM_SESSION_STRING}
    request_delay: 0.5

loggers:
  structured_logger:
    console_output: true
    host: ${INGESTION_HOST}
    level: DEBUG
    source_token: ${SOURCE_TOKEN}
```

## Security Best Practices

1. **Never commit your `.env` file to version control**. Ensure it's listed in your `.gitignore` file.
2. Limit environment variable access to only the necessary applications and users.
3. Regularly rotate your API keys and secrets.
4. Consider using a secrets management service for production environments. 