# CFED Plugin Automation Plan

## Overview

This document outlines the plan for creating a universal makefile template and Jupyter notebook integration to automate the CFED Plugin compilation process for different algorithms in the `data/C-Plus-Plus` directory, generating both protected and unprotected versions along with required analysis files.

## Objectives

1. Create a universal makefile template that works with any algorithm
2. Develop a Jupyter notebook to automate the compilation process
3. Generate both unprotected (RTL.txt) and protected (RTL_Protected.txt) versions
4. Generate analysis files (Edges.txt, Analysis.txt, CFG.xml)
5. Organize outputs in algorithm-specific directories matching the GCC_Plugin_Output structure

## Implementation Plan

### 1. Universal Makefile Template

Create a modular makefile system with the following components:

#### 1.1 `template/universal.mak`

```makefile
# Universal makefile template for CFED Plugin compilation

# Project configuration - these will be overridden by calling script
ALGORITHM ?= defaultAlgorithm
FUNCTION ?= defaultFunction
PROJECT ?= defaultProject
DATA_DIR ?= ../data

# Protection configuration
PROTECTION ?= NONE
TECHNIQUE ?= RACFED
TECH_TYPE ?= "SigMon"
SEL_LEVEL ?= 0

# Include compiler configuration
-include compiler_config.mak

# Output directory structure matching GCC_Plugin_Output
OUTPUT_DIR = $(DATA_DIR)/GCC_Plugin_Output/$(PROJECT)

# Common compiler flags
COMMON_FLAGS = -I$(INCLUDE_DIR) -O2 -g -std=c++11 -c

# Protection-specific configuration
ifeq ($(PROTECTION), RACFED)
    COMMON_FLAGS += -DTECHNIQUE=$(TECHNIQUE) -DTECH_TYPE=$(TECH_TYPE) -DSEL_LEVEL=$(SEL_LEVEL)
endif

# Define rules
all: compile disassemble

# Creates the output directory
setup:
	@echo "Setting up output directory for $(PROJECT)"
	@mkdir -p $(OUTPUT_DIR)

# Compiles both protected and unprotected versions
compile: setup
	@echo "Compiling $(PROJECT) ($(ALGORITHM)::$(FUNCTION))"
	
	# Unprotected version
	$(CROSS_CXX) $(COMMON_FLAGS) -o $(OUTPUT_DIR)/$(PROJECT)_unprotected.o $(SRC_DIR)/$(ALGORITHM).cpp
	$(CROSS_LINKXX) -o $(OUTPUT_DIR)/$(PROJECT)_unprotected.elf $(OUTPUT_DIR)/$(PROJECT)_unprotected.o
	
	# Protected version (if enabled)
ifeq ($(PROTECTION), RACFED)
	$(CROSS_CXX) $(COMMON_FLAGS) -DTECHNIQUE=$(TECHNIQUE) -o $(OUTPUT_DIR)/$(PROJECT)_protected.o $(SRC_DIR)/$(ALGORITHM).cpp
	$(CROSS_LINKXX) -o $(OUTPUT_DIR)/$(PROJECT)_protected.elf $(OUTPUT_DIR)/$(PROJECT)_protected.o
endif

# Generates disassembly files
disassemble: setup
	@echo "Generating disassembly for $(PROJECT)"
	
	# Unprotected version
	$(CROSS_OBJDUMP) -d -f -M reg-names-std --demangle $(OUTPUT_DIR)/$(PROJECT)_unprotected.elf > $(OUTPUT_DIR)/RTL.txt
	
	# Protected version (if enabled)
ifeq ($(PROTECTION), RACFED)
	$(CROSS_OBJDUMP) -d -f -M reg-names-std --demangle $(OUTPUT_DIR)/$(PROJECT)_protected.elf > $(OUTPUT_DIR)/RTL_Protected.txt
endif

clean:
	@echo "Cleaning build files for $(PROJECT)"
	@rm -f $(OUTPUT_DIR)/*.o $(OUTPUT_DIR)/*.elf
```

#### 1.2 `template/compiler_config.mak`

```makefile
# Compiler configuration for CFED Plugin

# ARM GCC configuration
ARMGCC_DIR ?= /usr/local/arm-none-eabi
CROSS_CC := $(ARMGCC_DIR)/bin/arm-none-eabi-gcc -mlittle-endian -mthumb -mcpu=cortex-m3 -march=armv7-m
CROSS_CXX := $(ARMGCC_DIR)/bin/arm-none-eabi-g++ -mlittle-endian -mthumb -mcpu=cortex-m3 -march=armv7-m
CROSS_OBJCOPY := $(ARMGCC_DIR)/bin/arm-none-eabi-objcopy
CROSS_OBJDUMP := $(ARMGCC_DIR)/bin/arm-none-eabi-objdump

# Linker configuration
LINKER_SCRIPT ?= -T $(SCRIPT_DIR)/Imperas_withISR.ld
CROSS_LINKXX := $(ARMGCC_DIR)/bin/arm-none-eabi-g++ $(LINKER_SCRIPT) -specs=nosys.specs

# Directory configuration
SRC_DIR ?= ../data/C-Plus-Plus
INCLUDE_DIR ?= ../include
SCRIPT_DIR ?= ../scripts
```

### 2. Jupyter Notebook Integration

Create a Jupyter notebook (`CFED_Compilation.ipynb`) that:

1. Scans the `data/C-Plus-Plus` directory for algorithm files
2. For each algorithm, identifies functions that need protection
3. Executes the makefile template to generate protected and unprotected versions
4. Generates all required analysis files

#### 2.1 Notebook Structure

```python
# CFED_Compilation.ipynb

# Imports
import os
import subprocess
import glob
import re
import json

# Configuration
SRC_DIR = "../../data/C-Plus-Plus"
DATA_DIR = "../../data"
TEMPLATE_DIR = "../template"
OUTPUT_DIR = f"{DATA_DIR}/GCC_Plugin_Output"

# Function to extract algorithm names and their functions
def scan_algorithms():
    algorithms = {}
    
    for cpp_file in glob.glob(f"{SRC_DIR}/*.cpp"):
        algo_name = os.path.basename(cpp_file).replace(".cpp", "")
        algorithms[algo_name] = []
        
        # Parse the file to extract function names
        with open(cpp_file, 'r') as f:
            content = f.read()
            # Use regex to find function declarations
            functions = re.findall(r'(?:void|int|char\*|float|double)\s+(\w+)\s*\([^)]*\)', content)
            algorithms[algo_name].extend(functions)
    
    return algorithms

# Function to compile an algorithm with protection
def compile_algorithm(algorithm, function):
    project_name = f"{algorithm}_{function}"
    
    # Create output directory
    os.makedirs(f"{OUTPUT_DIR}/{project_name}", exist_ok=True)
    
    cmd = [
        "make", 
        "-f", f"{TEMPLATE_DIR}/universal.mak",
        f"ALGORITHM={algorithm}",
        f"FUNCTION={function}",
        f"PROJECT={project_name}",
        f"DATA_DIR={DATA_DIR}",
        f"PROTECTION=RACFED"  # Enable RACFED protection
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"ERROR: Compilation failed with return code {result.returncode}")
        print(f"STDERR: {result.stderr}")
        return False
    
    print(f"SUCCESS: Compilation completed successfully")
    print(f"Output saved to: {OUTPUT_DIR}/{project_name}")
    return True

# Save compilation metadata
def save_metadata(algorithms):
    metadata = {
        "compilation_date": datetime.datetime.now().isoformat(),
        "algorithms": {}
    }
    
    for algo_name, functions in algorithms.items():
        metadata["algorithms"][algo_name] = {
            "functions": functions,
            "output_dirs": [f"{OUTPUT_DIR}/{algo_name}_{func}" for func in functions]
        }
    
    with open(f"{OUTPUT_DIR}/compilation_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

# Main execution
import datetime
print(f"Starting CFED Plugin compilation at {datetime.datetime.now().isoformat()}")

# Create output directory
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Scan algorithms
algorithms = scan_algorithms()
print(f"Found {len(algorithms)} algorithms:")
for algo_name, functions in algorithms.items():
    print(f"  - {algo_name}: {', '.join(functions)}")

# Compile each algorithm
successful = 0
failed = 0

for algo_name, functions in algorithms.items():
    print(f"\nProcessing algorithm: {algo_name}")
    
    for func in functions:
        print(f"  Compiling function: {func}")
        
        if compile_algorithm(algo_name, func):
            successful += 1
        else:
            failed += 1

# Save metadata
save_metadata(algorithms)

# Summary
print(f"\nCompilation complete: {successful} successful, {failed} failed")
print(f"All outputs are saved in: {OUTPUT_DIR}")
```

### 3. Directory Structure

The automation will create the following directory structure:

```
project_root/
├── data/
│   ├── C-Plus-Plus/                    # Source algorithms
│   │   ├── sortingAlgorithms.cpp
│   │   └── ...
│   └── GCC_Plugin_Output/              # Compilation outputs
│       ├── sortingAlgorithms_bubbleSort/
│       │   ├── RTL.txt                 # Unprotected RTL
│       │   ├── RTL_Protected.txt       # Protected RTL
│       │   ├── Edges.txt               # Control flow edges (Generated by compiler plugin)
│       │   ├── Analysis.txt            # Analysis summary (Generated by compiler plugin)
│       │   └── CFG.xml                 # Control flow graph in XML (Generated by compiler plugin)
│       ├── sortingAlgorithms_quickSort/
│       │   └── ...
│       └── compilation_metadata.json   # Metadata about compilation
├── src/
│   └── algorithm_compiler/             # Algorithm compiler source code
│       ├── template/                   # Makefile templates
│       │   ├── universal.mak
│       │   └── compiler_config.mak
└── notebooks/                  # Jupyter notebooks
│    └── CFED_Compilation.ipynb
```

## Implementation Steps

1. **Setup Directory Structure**
   - Create necessary directories for templates and outputs

2. **Create Makefile Templates**
   - Implement `universal.mak` and `compiler_config.mak`
   - Configure them to generate outputs matching the GCC_Plugin_Output format

3. **Create Jupyter Notebook**
   - Implement the notebook to automate the compilation process
   - Add functionality to scan algorithms and execute make commands

4. **Testing**
   - Test with a single algorithm to ensure outputs match the expected format
   - Validate both protected and unprotected outputs
   - Verify analysis files are correctly generated by the compiler plugin

5. **Full Implementation**
   - Run the notebook on all algorithms in `data/C-Plus-Plus`
   - Ensure each algorithm and function gets its own directory
   - Verify all required files are generated for each algorithm/function

## Expected Output

For each algorithm and function, the automation will generate a directory with these files:

1. `RTL.txt`: Unprotected disassembly output
2. `RTL_Protected.txt`: Protected disassembly output with RACFED protection
3. `Edges.txt`: List of control flow edges
4. `Analysis.txt`: Statistical analysis of the code
5. `CFG.xml`: XML representation of the control flow graph

## Conclusion

This automation plan provides a comprehensive approach to compiling multiple algorithms with CFED protection, generating outputs that match the format observed in the GCC_Plugin_Output/crc32 example. The modular design allows for easy extension to support additional protection techniques or algorithms in the future. 