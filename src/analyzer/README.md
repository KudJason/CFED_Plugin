# Analyzer

This directory contains tools, scripts, and notebooks for analyzing CFED (Control Flow Enforcement Detection) protection patterns, particularly using Large Language Models (LLMs) for analysis and potentially knowledge distillation.

## Key Areas:

*   **LLM-Based Analysis:**
    *   `llm_analysis.py`: Core script for analyzing CFED protection records (likely loaded from `record.json` or a database). It defines Pydantic models (`ProtectionSchema`, `BlockNode`, etc.) to structure protection information. Key functions include:
        *   `extract_features_from_record`: Extracts basic metadata (algorithm name, technique).
        *   `analyze_protection_patterns`: Placeholder for deeper pattern analysis.
        *   `generate_protection_schema`: Converts raw record data into the structured `ProtectionSchema`.
        *   `create_training_data`: Generates a Pandas DataFrame from records for analysis.
        *   `visualize_protection_patterns`: Creates plots (e.g., technique distribution) using Matplotlib.
        *   `cluster_protection_patterns`: Uses TF-IDF, PCA, and K-Means (from scikit-learn) to cluster records based on textual features.
        *   `prepare_finetuning_dataset`: Formats the analyzed data into a JSONL file (`finetuning_data.jsonl`) suitable for fine-tuning an LLM, creating prompts and expected assistant responses based on CFE/RACFE patterns.
    *   `llm_analysis.ipynb`: A Jupyter notebook likely used for interactive exploration and visualization of the analysis performed by `llm_analysis.py`.
    *   `distillation_prompts_example.ipynb`: Notebook demonstrating example prompts, possibly for knowledge distillation or fine-tuning tasks related to CFED analysis.
*   **Data Handling & Preparation:**
    *   `record.json`: Example JSON file containing CFED build/analysis records.
    *   `training_data_prep.ipynb`: Notebook focused on preparing data specifically for training or fine-tuning models.
    *   `inspect_finetune_data.ipynb`: Notebook for examining the generated fine-tuning dataset.
    *   `data_util/`: Subdirectory likely containing utility functions for data loading, cleaning, or transformation.
*   **Database Interaction:**
    *   `db_walkthrough.ipynb`: Notebook demonstrating how to interact with databases (potentially MongoDB or SQLite where build data is archived) to retrieve data for analysis.
*   **Supporting Modules:**
    *   `model/`: Likely contains model definitions or configurations (perhaps related to the LLMs being used).
    *   `prompts/`: May store standardized prompt templates.
    *   `scripts/`: Contains supporting execution scripts.
    *   `service/`: Could house code related to deploying the analysis as a service.
    *   `test/`: Contains unit or integration tests.

Refer to the specific files, notebooks, and subdirectories for detailed functionality and usage. 