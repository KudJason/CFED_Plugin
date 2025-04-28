# CFED Development Environment

This development container provides a complete environment for CFED development and testing.

## Prerequisites

1. Install Docker Desktop
2. Install Visual Studio Code
3. Install the "Remote - Containers" extension in VS Code
4. Have a GitLab account with SSH key access

## Setup

1. Clone this repository
2. Open the repository in VS Code
3. When prompted, click "Reopen in Container"
4. Wait for the container to build and initialize

## GitLab Configuration

### SSH Key Setup

1. Generate an SSH key if you don't have one:
   ```bash
   ssh-keygen -t ed25519 -C "your.email@example.com"
   ```

2. Copy your public key:
   ```bash
   cat ~/.ssh/id_ed25519.pub
   ```

3. Add the SSH key to your GitLab account:
   - Go to GitLab > Settings > SSH Keys
   - Paste your public key
   - Give it a title (e.g., "CFED Development Container")
   - Click "Add key"

4. Test your SSH connection:
   ```bash
   ssh -T git@gitlab.kuleuven.be
   ```

### Git Configuration

1. Set your Git identity:
   ```bash
   git config --global user.name "Your Name"
   git config --global user.email "your.email@example.com"
   ```

2. Configure Git to use SSH for GitLab:
   ```bash
   git config --global url."git@gitlab.kuleuven.be:".insteadOf "https://gitlab.kuleuven.be/"
   ```

## Directory Structure

```
/workspace/
├── cfed_basic/           # Basic CFED development environment
│   ├── generic/         # Generic compilation template
│   ├── algorithms/      # Algorithm implementations
│   └── BuildGeneric.sh # Build script
├── toolchains/         # ARM toolchain
├── cfed_plugin/        # CFED GCC plugin
└── academiccasestudies/ # Case studies
```

## Features

### Command Line Interface

The container includes a customized bash shell that provides:
- Git status and branch information
- Directory navigation
- Various development tools pre-installed

### Python Environment

The container includes a Python virtual environment with:
- NumPy, Pandas, Matplotlib for data analysis
- Jupyter notebook for interactive development
- IPython kernel for interactive Python sessions

## Usage

1. Navigate to the cfed_basic directory:
   ```bash
   cd /workspace/cfed_basic
   ```

2. Add your algorithm implementation to the algorithms directory

3. Build your algorithm:
   ```bash
   ./BuildGeneric.sh your_algorithm
   ```

4. For protected builds:
   ```bash
   ./BuildGeneric.sh your_algorithm output_name CFED=1
   ```

## Environment Variables

The following environment variables are set automatically:
- `ARMGCC_DIR`: Path to ARM toolchain
- `ARMGCC7`: Path to ARM toolchain
- `CFED_PLUGIN_PATH`: Path to CFED plugin

## Troubleshooting

1. If you encounter permission issues:
   ```bash
   sudo chown -R developer:developer /workspace
   ```

2. If the container fails to build:
   - Check Docker logs
   - Ensure all prerequisites are installed
   - Try rebuilding the container 