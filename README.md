# Intelligent Consciousness Interface (ICI) Core

A modular framework for creating a personal AI assistant that is context-aware, style-aware, personality-aware, and security-aware. The system processes data through an Ingestion Pipeline and responds to queries via a Query Pipeline, leveraging vector databases for efficient retrieval.

## 1. Introduction

ICI Core is an extensible framework designed to create AI assistants that are:

- **Context-aware**: Uses vector databases to retrieve relevant information
- **Style-aware**: Adapts response style based on configuration
- **Personality-aware**: Customizable through prompt templates
- **Security-aware**: Validates all user input against configurable security rules

The system is architecturally divided into two primary pipelines:
- **Ingestion Pipeline**: Processes and stores data from various sources (Telegram, Twitter, YouTube, etc.)
- **Query Pipeline**: Handles user interactions, retrieves relevant context, and generates responses

Key features include:
- Modular components with well-defined interfaces
- Support for multiple data sources
- Flexible model selection (OpenAI, Anthropic, Ollama, etc.)
- Configurable vector storage backends
- Comprehensive logging and error handling

## 2. How to Use

Simple command to get started:
```
bash setup.sh && cp .env.example .env
```

### Installation

#### Prerequisites
- Python 3.8 or higher
- pip package manager
- Git (if cloning the repository)

#### Setup Scripts

We provide two setup scripts to help you get started quickly:

- `setup.sh` for macOS/Linux users

These scripts will:
1. Check if a virtual environment is active
2. Create and activate a virtual environment if needed
3. Install all required dependencies from `requirements.txt`

```bash
# For macOS/Linux
chmod +x setup.sh
./setup.sh
```

#### One-line Installation (Experimental)

You can also install the framework with a single command which will automatically clone the repository and set up the environment:

```bash
curl -s https://raw.githubusercontent.com/yourusername/ici-core/main/install.sh | bash
```

This command will:
1. Check if git and Python are installed
2. Find or clone the repository
3. Set up a virtual environment
4. Install all dependencies automatically

Note: This installation method is new and experimental. If you encounter any issues, please use the manual setup method below.

Alternatively, you can set up manually:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

#### Environment Variables

Copy the `.env.example` file to `.env` and update the values:

```bash
cp .env.example .env
```

Then edit the `.env` file with your credentials:

1. **Telegram API Credentials** (required for Telegram ingestion):
   - `TELEGRAM_API_ID`: Your Telegram API ID
   - `TELEGRAM_API_HASH`: Your Telegram API hash
   - `TELEGRAM_PHONE_NUMBER`: Your phone number with country code
   - `TELEGRAM_SESSION_STRING`: Your Telegram session string

2. **Generator API Key** (required for OpenAI/Anthropic models):
   - `GENERATOR_API_KEY`: Your OpenAI/Anthropic API key

#### Getting Telegram API Credentials

1. Visit https://my.telegram.org/apps
2. Log in with your phone number
3. Create a new application
4. Note your API ID and API hash
5. The session string will automatically be generated on first run.

#### Getting OpenAI API Key

1. Visit https://platform.openai.com/
2. Sign up or log in to your account
3. Navigate to API keys section
4. Create a new secret key
5. Copy the key (it won't be shown again)

### Running the Application

Once configured, run the application using:

```bash
python main.py
```

## 3. How to Change AI Model

### Configuring the Model in config.yaml

The AI model is configured in the `generator` section of `config.yaml`:

```yaml
generator:
  api_key: $GENERATOR_API_KEY
  model: gpt-4o
  provider: openai
  type: langchain
  default_options:
    temperature: 0.7
    max_tokens: 1024
    frequency_penalty: 0.0
    presence_penalty: 0.0
    top_p: 1.0
```

### Available OpenAI Models

You can change the `model` parameter to any of these OpenAI models:
- `gpt-4o` (default)
- `gpt-4-turbo`
- `gpt-4`
- `gpt-3.5-turbo`

### Using Anthropic Claude Models

To switch to Claude models:

```yaml
generator:
  api_key: $GENERATOR_API_KEY
  model: claude-3-opus-20240229
  provider: anthropic
  type: langchain
  default_options:
    temperature: 0.7
    max_tokens: 1024
```

Available Claude models:
- `claude-3-opus-20240229`
- `claude-3-sonnet-20240229`
- `claude-3-haiku-20240307`

### Using Ollama Models

To use locally hosted Ollama models:

1. Install Ollama (https://ollama.com/)
2. Pull your preferred model (e.g., `ollama pull llama3`)
3. Update your configuration:

```yaml
generator:
  model: llama3
  provider: ollama
  type: langchain
  default_options:
    temperature: 0.7
    max_tokens: 1024
```

Available Ollama models depend on what you've pulled, but common options include:
- `llama3`
- `mistral`
- `mixtral`
- `vicuna`
- `gemma`

## 4. Documentation

Comprehensive documentation is available in the `docs` directory:

- [Functional Requirements](docs/functional-requirements.md): Detailed requirements for the ICI framework
- [Technical Specifications](docs/tech-specs.md): In-depth technical details of components and architecture
- [Project Structure](docs/project-structure.md): Overview of the codebase organization

## 5. License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 6. How to Contribute

We welcome contributions to ICI Core! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on how to contribute to the project.

For quick reference:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
