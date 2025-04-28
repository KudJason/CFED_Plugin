# CFED Plugin Compilation System Guide

## 1. System Overview

The CFED (Control Flow Error Detection) plugin compilation system is a toolchain designed to generate both protected and unprotected code. This document provides a detailed explanation of the system's functionality, component structure, and how to create a general compilation template.

### 1.1 Core Components

The system consists of the following key files:

- **`compile_cfed.py`**: The main script responsible for compiling algorithms with CFED protection.
- **`makefile`**: The project-specific build rules and configurations.
- **`plugin_commands.mak`**: Configuration file for CFED protection parameters.
- **Source code files**: Includes algorithm implementations and other necessary components.

### 1.2 Workflow Overview

1. The user initiates the compilation process through the `compile_cfed.py` script.
2. The script checks the environment and verifies the existence of necessary files and tools.
3. It inspects the source code to ensure the specified function exists.
4. The script executes the compilation, linking, and disassembly processes to generate the final output.

## 2. Key File Descriptions

### 2.1 `compile_cfed.py`

This script serves as the entry point for the compilation process. It handles the following tasks:

- **Environment Checks**: Verifies the presence of required files, such as the `makefile` and plugin commands.
- **Function Inspection**: Checks if the specified function exists in the source file.
- **Compilation Execution**: Runs the `make` commands to compile the code with CFED protection.

### 2.2 `makefile`

The `makefile` defines the build process for the project. Key sections include:

- **Project Configuration**: Defines project-specific variables such as `PROJECT`, `ALGORITHM`, and `FUNCTION`.
- **Compiler Flags**: Sets common compiler flags for ARM cross-compilation, including include paths and optimization settings.
- **Build Rules**: Specifies how to compile source files, link them, and generate output files (ELF, binary, disassembly).

### 2.3 `plugin_commands.mak`

This file contains configuration parameters for CFED protection, including:

- **CFED Type**: Specifies the type of protection to be applied.
- **Technique and Level**: Defines the technique used for protection and its selective level.

## 3. Compilation Process

### 3.1 Compiling with Protection

To compile a project with CFED protection, the following command is used:

```bash
python compile_cfed.py <algorithm_path> <function_name> --project-name <project_name>
```

- **`<algorithm_path>`**: Path to the source file containing the algorithm.
- **`<function_name>`**: Name of the function to protect.
- **`<project_name>`**: Optional project name (defaults to the algorithm filename).

### 3.2 Compiling without Protection

To compile the project without CFED protection, simply omit the protection parameters in the command.

## 4. General Compilation Template Design

### 4.1 Directory Structure

```
project_root/
├── build_scripts/
│   ├── compile.sh              # General compilation script
│   ├── compiler_config.mak      # Compiler configuration
│   └── protection_config.mak    # Protection configuration
├── common/
│   ├── startup/                 # Startup files
│   └── lib/                     # Common libraries
└── applications/
    ├── app1/
    │   ├── makefile
    │   └── src/
    └── app2/
        ├── makefile
        └── src/
```

### 4.2 General Compilation Script

```bash
#!/bin/bash
set -e

# Parameters: project name, dataset, [protection type], [additional parameters]
PROJECT=$1
DATASET=$2
PROTECTION=$3
EXTRA_ARGS=$4

# Build command
if [ -n "$PROTECTION" ]; then
    # Protected version
    make clean -C applications/$PROJECT CROSS=SIJIE dataSet=$DATASET
    make -C applications/$PROJECT $PROJECT.disasm CROSS=SIJIE dataSet=$DATASET \
         PLUGIN_COMMAND="-DTECHNIQUE=$PROTECTION" $EXTRA_ARGS
else
    # Unprotected version
    make clean -C applications/$PROJECT CROSS=SIJIE dataSet=$DATASET
    make -C applications/$PROJECT $PROJECT.disasm CROSS=SIJIE dataSet=$DATASET $EXTRA_ARGS
fi
```

### 4.3 General Compiler Configuration

```makefile
# Compiler configuration for multiple target architectures
ifeq ($(CROSS), SIJIE)
    CROSS_CC := $(ARMGCC_DIR)/bin/arm-none-eabi-gcc
    CROSS_CXX := $(ARMGCC_DIR)/bin/arm-none-eabi-g++
    # Additional configurations...
endif
```

### 4.4 General Protection Configuration

```makefile
# Protection configuration
ifeq ($(TECHNIQUE), RACFED)
    CFED_TYPE = RACFED
    # Additional parameters...
endif
```

## 5. Common Issues and Solutions

### 5.1 Compiler Path Issues

Ensure that the `ARMGCC_DIR` environment variable is correctly set:

```bash
export ARMGCC_DIR=/path/to/arm/gcc
```

### 5.2 Missing Linker Script

Adjust the linker script path as necessary in the `makefile`.

### 5.3 Protection Technique Conflicts

Ensure that only one protection technique is enabled at a time to avoid conflicts.

## 6. Conclusion

This guide provides a comprehensive overview of the CFED plugin compilation system. By following the outlined steps, users can easily compile both protected and unprotected versions of their code. The modular design allows for flexibility in adapting to different projects and protection requirements.

---

Feel free to modify any sections or add additional details as needed!
