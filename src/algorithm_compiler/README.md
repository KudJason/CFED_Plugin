# Algorithm Compiler

This directory contains scripts and tools related to compiling and processing C/C++ algorithms, specifically focusing on applying and managing Control Flow Enforcement Detection (CFED) techniques.

## Key Components:

*   **Compilation Pipeline:**
    *   `compile_cfed.py`: The main script to orchestrate the CFED compilation process. It handles environment checks, uses `make` with specific targets and parameters (like `CFED=1`, `FUNCTION`, `TECHNIQUE`), and verifies output files (.elf, .bin, .disasm). It integrates with a GCC plugin (`CFED_plugin64.so`).
    *   `makefile`, `plugin_commands.mak`, `plugin_config.mak`, `Sijie_compile.mak`: Makefiles defining the build rules, compiler flags, plugin paths, and specific configurations (e.g., for SIJIE cross-compiler).
    *   `CFED_compliation.ipynb`: A Jupyter notebook likely used for experimenting with or documenting the CFED compilation workflow.
*   **Preprocessing:**
    *   `algorithm_preprocess.py`: Prepares C++ source files before compilation. It uses `libclang` (or regex as a fallback) to parse the code, inject common definitions (`#define STR(x)`), and add `__attribute__((CFED(...)))` annotations to function definitions to mark them for the CFED GCC plugin.
*   **Archiving:**
    *   `build_archiver.py`: Archives build metadata and optionally build artifacts (like GCC plugin output) into a **MongoDB** database. It connects using credentials from `/workspace/data/.db_env` and stores information like algorithm name, technique, timestamp, compiler/plugin versions, and file hashes.
    *   `sqlite_archiver.py`: Provides similar archiving functionality but uses an **SQLite** database (default path: `/workspace/data/database/cfed_builds.db`). It stores build metadata and file contents (as BLOBs) in structured tables (`builds`, `build_files`, `plugin_outputs`, `plugin_files`).
*   **Build Artifacts:**
    *   `BUILD/`: The default output directory where compiled files (.o, .elf, .bin, .disasm) and GCC plugin outputs (`GCC_Plugin_Output/`) are placed.

Refer to individual scripts and notebooks for more detailed documentation and usage instructions. 