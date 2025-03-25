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

## 2. Getting Started

### Prerequisites
- Python 3.8 or higher
- pip package manager
- Git (if cloning the repository)

### Installation and Setup

Choose ONE of the following installation methods based on your preference:

#### Option A: Quick Setup (Recommended for Most Users)
```bash
# 1. Clone the repository
git clone https://github.com/sidetrip-ai/ici-core.git
cd ici-core

# 2. Run the setup script
chmod +x setup.sh
./setup.sh

# 3. Create and configure your environment file
cp .env.example .env
# Edit .env with your API keys and configuration
```

#### Option B: One-line Installation (Experimental)
```bash
# This will automatically clone the repo, set up dependencies, and prompt for configuration
curl -s https://raw.githubusercontent.com/sidetrip-ai/ici-core/main/install.sh | bash

# After installation, edit your .env file
cp .env.example .env
# Edit .env with your API keys and configuration
```

#### Option C: Manual Installation (For Advanced Users)
```bash
# 1. Clone the repository
git clone https://github.com/yourusername/ici-core.git
cd ici-core

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Create and configure your environment file
cp .env.example .env
# Edit .env with your API keys and configuration
```

### Configuration

After installation, you need to configure your environment variables in the `.env` file:

#### Required API Keys

1. **Telegram API Credentials** (needed for Telegram ingestion):
   - `TELEGRAM_API_ID`: Your Telegram API ID
   - `TELEGRAM_API_HASH`: Your Telegram API hash
   - `TELEGRAM_PHONE_NUMBER`: Your phone number with country code

2. **Generator API Key** (needed for AI model access):
   - `GENERATOR_API_KEY`: Your OpenAI or Anthropic API key

#### Getting Required API Keys

**For Telegram:**
1. Visit https://my.telegram.org/apps
2. Log in with your phone number
3. Create a new application
4. Note your API ID and API hash
5. The session string will be generated automatically on first run

**For OpenAI:**
1. Visit https://platform.openai.com/
2. Sign up or log in to your account
3. Navigate to API keys section
4. Create a new secret key
5. Copy the key (it won't be shown again)

### Running the Application

Once installed and configured, run the application with:

```bash
python main.py
```

This will start the CLI interface where you can interact with your AI assistant.

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
