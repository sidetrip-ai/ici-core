## MacOS

### Upgrade Python Version on MacOS (Only if your version is less than 3.10)

This repository requires Python 3.10 or higher. By default, MacOS comes with Python 3.9 pre-installed. To upgrade to Python 3.12 or any version 3.10 or later and ensure it's set in your PATH, follow these step-by-step instructions. We'll use **Homebrew**, a popular package manager for MacOS, to install and manage Python.

```
python3 --version
```

If the output is 3.10 or greater, than you can move on to [Setup section](#installation-and-setup)

#### Step 1: Install Homebrew (if not already installed)

Homebrew simplifies the installation of software like Python on MacOS. If you don’t have it installed yet, follow these steps:

1. Open **Terminal**.
2. Run the following command to install Homebrew:

   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

3. Follow the on-screen instructions to complete the installation. The script may prompt you to install Xcode Command Line Tools if they’re not already present—just follow the prompts to do so.

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

   - This installs the latest stable Python version (e.g., 3.11 or 3.12, depending on Homebrew’s current formula), which will be 3.10 or higher.
   - **Optional**: If you specifically need Python 3.12 and it’s available, you can try `brew install python@3.12`. Check available versions with `brew search python` if needed.

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
   - If it doesn’t, add the appropriate line to your shell configuration file (e.g., `~/.zshrc` for zsh, which is default on macOS Catalina and later, or `~/.bash_profile` for bash):
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

### \<iostream\> header not found

This issue is likely related to `xcode-select` command line tools—such as errors during package installation that involve compiling C++ code—this guide will help you check for `clang++`, install the necessary tools if needed, and verify your setup.

### Steps to Resolve the Issue

1. **Check if `clang++` is installed**
   - Open your terminal and run:
     ```bash
     which clang++
     ```
   - If this returns a path (e.g., `/usr/bin/clang++`), `clang++` is already installed, and you can skip to step 3.
   - If nothing is returned, `clang++` is not installed, and you’ll need to proceed to the next step.

2. **Install Xcode Command Line Tools**
   - To install the Xcode Command Line Tools (which include `clang++`), run:
     ```bash
     xcode-select --install
     ```
   - A dialog will pop up asking you to install the tools. Follow the prompts to complete the installation.
   - **Note**: This provides the C++ compiler and standard library headers required for compiling C++ code on macOS.

3. **Verify `clang++` installation**
   - After installation, check again by running:
     ```bash
     which clang++
     ```
   - You should now see a path (e.g., `/usr/bin/clang++`), confirming that `clang++` is installed.

4. **Update Homebrew and run `brew doctor`**
   - Update Homebrew to ensure you have the latest package definitions:
     ```bash
     brew update
     ```
   - Then, check your Homebrew setup for issues:
     ```bash
     brew doctor
     ```
   - Follow any instructions from `brew doctor` to fix reported problems, ensuring a clean development environment.

### Next Steps

After completing these steps, your system should have the necessary tools to compile C++ code. If you were troubleshooting a specific package installation error, try reinstalling it now—for example:

```bash
python3 -m pip install -r requirements.txt
```
