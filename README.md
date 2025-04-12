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
- Python 3.10 or higher
- pip package manager
- Git (if cloning the repository)
- NodeJS 18+

Note: If you face any issue while installing, check out [troubleshoot](./troubleshoot.md) file for known issues that might arise.


### Installation and Setup

Choose ONE of the following installation methods based on your operating system and preference:

Note: For Windows users, use Option C. Other options are experimental for Windows Users.

<details>
<summary>Option A: Quick Setup (Recommended for Most Users)</summary>

##### For macOS/Linux:
```bash
# 1. Clone the repository
git clone https://github.com/sidetrip-ai/ici-core.git
cd ici-core

# 2. Run the setup script
chmod +x setup.sh
./setup.sh

# 3. Activate venv
source venv/bin/activate

# 4. Create and configure your environment file
cp .env.example .env
# Edit .env with your API keys and configuration
```

##### For Windows:
```powershell
# 1. Clone the repository
git clone https://github.com/sidetrip-ai/ici-core.git
cd ici-core

# 2. Run the setup script
setup.bat

# 3. Activate venv
venv\Scripts\activate

# 4. Create and configure your environment file
copy .env.example .env
# Edit .env with your API keys and configuration
```
</details>

<details>
<summary>Option B: One-line Installation (Experimental)</summary>

##### For macOS/Linux:
```bash
# This will automatically clone the repo, set up dependencies, and prompt for configuration
curl -s https://raw.githubusercontent.com/sidetrip-ai/ici-core/main/install.sh | bash

# Activate venv
source venv/bin/activate

# After installation, edit your .env file
cp .env.example .env
# Edit .env with your API keys and configuration
```

##### For Windows:
```powershell
# Download and run the install script
Invoke-WebRequest https://raw.githubusercontent.com/sidetrip-ai/ici-core/main/install.bat -OutFile install.bat
.\install.bat

# Activate venv
venv\Scripts\activate

# After installation, edit your .env file
copy .env.example .env
# Edit .env with your API keys and configuration
```
</details>

<details>
<summary>Option C: Manual Installation (For Advanced Users)</summary>

##### For macOS/Linux:
```bash
# 1. Clone the repository
git clone https://github.com/sidetrip-ai/ici-core.git
cd ici-core

# 2. Create virtual environment
python3 -m venv venv

# 3. Activate virtual environment
source venv/bin/activate

# 4. Install dependencies
python3 -m pip install -r requirements.txt

# 5. Create and configure your environment file
cp .env.example .env
# Edit .env with your API keys and configuration
```

##### For Windows:
```powershell
# 1. Clone the repository
git clone https://github.com/sidetrip-ai/ici-core.git
cd ici-core

# 2. Create virtual environment
python3 -m venv venv

# 3. Activate virtual environment
venv\Scripts\activate

# 4. Install dependencies
python3 -m pip install -r requirements.txt

# 5. Create and configure your environment file
copy .env.example .env
# Edit .env with your API keys and configuration
```
</details>

### Setting Up WhatsApp Integration

To enable WhatsApp functionality, you'll need to run the WhatsApp service separately. Follow these steps:

1. Open a new terminal window
2. Navigate to the WhatsApp service directory:
   ```bash
   cd services/whatsapp-service
   ```
3. Install the required Node.js dependencies:
   ```bash
   npm install
   ```
4. Start the WhatsApp service:
   ```bash
   npm run start
   ```
5. Once the service is running:
   - Open http://localhost:3006 in your web browser
   - You'll see a QR code on the page
   - Open WhatsApp on your phone
   - Go to Settings > WhatsApp Web/Desktop
   - Scan the QR code with your phone's camera
   - Wait for authentication to complete

The WhatsApp service is now connected and ready to use with the main application.

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

Once installed and configured, run the application:

##### For macOS/Linux:
```bash
# Ensure virtual environment is activated if not already
source venv/bin/activate

# Run the application
python3 main.py
```

##### For Windows:
```powershell
# Ensure virtual environment is activated if not already
venv\Scripts\activate

# Run the application
python3 main.py
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
