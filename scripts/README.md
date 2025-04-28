# CFED Plugin Scripts

This directory contains scripts for the CFED Plugin compilation system:

- `build.sh`: Main script for building algorithms with CFED protection
- `analyze_rtl.py`: Script for analyzing RTL disassembly and generating analysis files

## Usage

### Building an Algorithm

To build a specific algorithm with CFED protection:

```bash
./build.sh PROJECT_NAME ALGORITHM_PATH FUNCTION_NAME [PROTECTION_TYPE]
```

Parameters:
- `PROJECT_NAME`: Name for the output directory (usually algorithm_function)
- `ALGORITHM_PATH`: Path to the algorithm file relative to the C-Plus-Plus directory (e.g., sorting/bubble_sort)
- `FUNCTION_NAME`: Name of the function to protect
- `PROTECTION_TYPE`: Protection type (RACFED or NONE, optional)

Example:
```bash
./build.sh bubble_sort_bubble_sort sorting/bubble_sort bubble_sort RACFED
```

### Analyzing RTL

To analyze RTL disassembly and generate analysis files:

```bash
./analyze_rtl.py --rtl RTL_FILE --function FUNCTION_NAME --output-dir OUTPUT_DIR
```

Parameters:
- `RTL_FILE`: Path to the RTL disassembly file
- `FUNCTION_NAME`: Name of the function to analyze
- `OUTPUT_DIR`: Directory to save the analysis files

Example:
```bash
./analyze_rtl.py --rtl ../data/GCC_Plugin_Output/bubble_sort_bubble_sort/RTL.txt --function bubble_sort --output-dir ../data/GCC_Plugin_Output/bubble_sort_bubble_sort
```

This will generate the following files:
- `Edges.txt`: List of control flow edges
- `Analysis.txt`: Statistical analysis of the code
- `CFG.xml`: XML representation of the control flow graph 