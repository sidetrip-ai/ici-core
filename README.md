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


### Upgrade Python Version on MacOS (Only if your version is less than 3.10)

This repository requires Python 3.10 or higher. By default, MacOS comes with Python 3.9 pre-installed. To upgrade to Python 3.12 or any version 3.10 or later and ensure it's set in your PATH, follow these step-by-step instructions. We'll use **Homebrew**, a popular package manager for MacOS, to install and manage Python.

### Check your python version
```
python3 --version
```

If the output is 3.10 or greater, than you can move on to [Setup section](#installation-and-setup)

#### Step 1: Install Homebrew (if not already installed)

Homebrew simplifies the installation of software like Python on MacOS. If you don't have it installed yet, follow these steps:

1. Open **Terminal**.
2. Run the following command to install Homebrew:

   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

3. Follow the on-screen instructions to complete the installation. The script may prompt you to install Xcode Command Line Tools if they're not already present—just follow the prompts to do so.

   - **Note**: After installation, Homebrew might display instructions to add it to your PATH. For example, on Apple Silicon Macs, you may need to run:
     ```bash
     echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc
     ```
     Then, restart Terminal or run `source ~/.zshrc`. On Intel Macs, this is typically not needed as `/usr/local/bin` is already in the PATH.

#### Step 2: Install Python using Homebrew

Once Homebrew is installed, you can use it to install a newer version of Python:

1. In Terminal, run the following command to install the latest versionof Python available via Homebrew:

   ```bash
   brew install python
   ```

   - This installs the latest stable Python version (e.g., 3.11 or 3.12, depending on Homebrew's current formula), which will be 3.10 or higher.
   - **Optional**: If you specifically need Python 3.12 and it's available, you can try `brew install python@3.12`. Check available versions with `brew search python` if needed.

2. Homebrew will install Python and create symlinks in `/usr/local/bin` (Intel Macs) or `/opt/homebrew/bin` (Apple Silicon Macs), typically making it the default `python3` when you run it.

#### Step 3: Verify the Python Version

After installation, confirm that the correct Python version is set up:

1. In Terminal, run:

   ```bash
   python3 --version
   ```

2. You should see output like `Python 3.x.y`, where `x` is 10 or higher (e.g., `Python 3.12.0`).

3. **Troubleshooting**: If it still shows `Python 3.9.x`, the system Python is being used instead of the Homebrew version. To fix this:
   - Check which Python is being used by running:
     ```bash
     which python3
     ```
     - If it shows `/usr/bin/python3` (system Python) instead of `/usr/local/bin/python3` (Intel) or `/opt/homebrew/bin/python3` (Apple Silicon), your PATH needs adjustment.
   - Verify your PATH by running:
     ```bash
     echo $PATH
     ```
     - Ensure `/usr/local/bin` (Intel) or `/opt/homebrew/bin` (Apple Silicon) appears **before** `/usr/bin`.
   - If it doesn't, add the appropriate line to your shell configuration file (e.g., `~/.zshrc` for zsh, which is default on macOS Catalina and later, or `~/.bash_profile` for bash):
     - For Intel Macs:
       ```bash
       export PATH="/usr/local/bin:$PATH"
       ```
     - For Apple Silicon Macs:
       ```bash
       export PATH="/opt/homebrew/bin:$PATH"
       ```
   - Save the file, then run `source ~/.zshrc` (or `source ~/.bash_profile`) or restart Terminal.
   - Run `python3 --version` again to confirm.

You now have Python 3.10 or higher installed and set as the default `python3` command. You can proceed with the repository setup using this version. If you encounter any issues, consult the Homebrew documentation or seek help from the repository maintainers.


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

3. **Google Workspace Credentials** (needed for Google Workspace integration):
   - `GOOGLE_CLIENT_ID`: Your Google OAuth client ID
   - `GOOGLE_CLIENT_SECRET`: Your Google OAuth client secret
   - `GOOGLE_REDIRECT_URI`: Your OAuth redirect URI (e.g., http://localhost:8080/oauth2callback)

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

**For Google Workspace:**
1. Visit https://console.cloud.google.com/
2. Create a new project or select an existing one
3. Enable the following APIs:
   - Google Calendar API
   - Gmail API
   - Google Docs API
   - Google Drive API
   - Google Tasks API
4. Go to Credentials
5. Create OAuth 2.0 Client ID
6. Set up OAuth consent screen
7. Note your Client ID and Client Secret
8. Add authorized redirect URIs

### Google Workspace Integration

The ICI framework includes seamless integration with Google Workspace services. You can use the following commands:

1. **Schedule Meetings**:
   ```
   /schedule [meeting details]
   ```
   Example: `/schedule Team sync tomorrow at 2pm for 1 hour`

2. **Create Email Drafts**:
   ```
   /email [email details]
   ```
   Example: `/email Send project update to team`

3. **Create Documents**:
   ```
   /doc [document details]
   ```
   Example: `/doc Create meeting notes from last chat`

4. **Create Tasks**:
   ```
   /task [task details]
   ```
   Example: `/task Review PR by EOD`

5. **Create Plans**:
   ```
   /plan [plan type] [details]
   ```
   Example: `/plan travel Create itinerary for next week`

The system will:
- Extract relevant details from your conversation
- Create the appropriate Google Workspace item
- Provide you with links and confirmation
- Handle errors gracefully with clear feedback

#### Error Handling

The Google Workspace integration includes robust error handling:

1. **Authentication Errors**:
   - If Google OAuth credentials are invalid or expired, you'll receive a clear message to update your credentials
   - The system will guide you through the OAuth flow if needed

2. **API Rate Limits**:
   - If you hit Google API rate limits, the system will automatically retry with exponential backoff
   - You'll be notified if the operation needs to be retried later

3. **Permission Issues**:
   - If the required Google Workspace permissions are missing, you'll receive specific guidance on which permissions to grant
   - The system will validate permissions before attempting operations

4. **Input Validation**:
   - The system validates meeting times, email addresses, and other inputs before making API calls
   - You'll receive immediate feedback if any required information is missing or invalid

5. **Network Issues**:
   - The system handles temporary network failures with automatic retries
   - You'll be notified if the operation needs to be retried due to connectivity issues

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
