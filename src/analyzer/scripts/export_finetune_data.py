"""
Script to export analysis results from MongoDB into a Parquet
format suitable for fine-tuning language models.

Generates samples for different analysis tasks:
- Graph Analysis
- Protection Determination
- Rule Verification

Example Usage (run as module from workspace root):
python -m src.analyzer.scripts.export_finetune_data \\
    --input-collection distillation_outputs \\
    --rules-file dev_docs/rules.md \\
    --output-file data/finetune_data.parquet
"""

import argparse
import json
import sys
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add pandas and pyarrow imports
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# Assuming these utilities are accessible via relative paths
# when run as a module (python -m ...)
try:
    from ..service.db_service import DBService
    from ..data_util.file_utils import load_rules
    # Import the same decoding function used during data prep
    from .distillation_data_prep import decode_rtl_content 
except ImportError as e:
    # Provide specific feedback if imports fail
    logging.basicConfig(level=logging.ERROR)
    logger = logging.getLogger(__name__)
    logger.error(f"Error importing necessary modules: {e}")
    logger.error("Please ensure this script is run as a module from the workspace root,")
    logger.error("and that DBService, load_rules, and decode_rtl_content are available.")
    logger.error("Also ensure 'pandas' and 'pyarrow' are installed (pip install pandas pyarrow).")
    logger.error("Example: python -m src.analyzer.scripts.export_finetune_data ...")
    sys.exit(1)

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Constants for Fine-tuning Instructions ---
INSTRUCTIONS = {
    "graph_analysis": "分析提供的 RTL 代码片段，并以 JSON 格式生成一个简化的控制/数据流图。",
    "protection_determination": "基于提供的图 JSON，判断代码中存在的保护类型 (CFE, RACFE, BOTH, NONE)，并给出置信度。",
    "rule_verification": "根据提供的代码、图 JSON、已判断的保护类型以及规则文本，验证代码是否符合规则，并以 JSON 格式输出验证结果。"
}

# --- Helper Function to Safely Get Data ---
def get_nested(data: Optional[Dict], keys: List[str], default=None) -> Any:
    """Safely access nested dictionary keys."""
    if data is None:
        return default
    temp = data
    for key in keys:
        if isinstance(temp, dict) and key in temp:
            temp = temp[key]
        else:
            return default
    return temp

# --- Main Export Function ---
def export_data(input_collection_name: str, rules_file_path: str, output_file_path: str):
    """Connects to DB, processes documents, and exports data to Parquet."""
    logger.info("Starting fine-tuning data export process...")

    db_service: Optional[DBService] = None
    all_samples = []
    processed_docs = 0
    generated_samples = 0
    error_docs = 0
    skipped_missing_data = 0

    try:
        # 1. Initialize DB and Load Rules
        logger.info(f"Connecting to MongoDB...")
        db_service = DBService()
        db = db_service.get_db() # Check connection early
        logger.info(f"Connected to DB: {db.name}")

        logger.info(f"Loading rules from: {rules_file_path}")
        rules_text = load_rules(rules_file_path)
        if not rules_text:
            logger.error("Failed to load rules text. Exiting.")
            sys.exit(1)

        # Get collection handles
        input_coll = db_service.get_collection(input_collection_name)
        plugin_outputs_coll = db_service.get_collection("plugin_outputs")
        augmented_outputs_coll = db_service.get_collection("augmented_plugin_outputs")
        logger.info(f"Accessing input collection: '{input_collection_name}'")
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_file_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # 3. Process Documents
        logger.info(f"Querying documents from '{input_collection_name}'...")
        total_docs = input_coll.count_documents({})
        logger.info(f"Found {total_docs} documents to process.")

        for doc in input_coll.find():
            processed_docs += 1
            doc_samples = 0
            has_error = False
            
            analysis_doc_id = doc.get("_id")
            original_id = doc.get("original_id")
            augmented_id = doc.get("augmented_id")
            
            if not original_id or not augmented_id:
                 logger.warning(f"Skipping doc {analysis_doc_id}: Missing original_id or augmented_id.")
                 skipped_missing_data += 1
                 continue

            logger.debug(f"Processing doc {analysis_doc_id} (Original: {original_id}, Augmented: {augmented_id})")

            # Fetch related documents and RTL content
            original_doc = plugin_outputs_coll.find_one({"_id": original_id})
            augmented_doc = augmented_outputs_coll.find_one({"_id": augmented_id})

            if not original_doc:
                logger.warning(f"Skipping doc {analysis_doc_id}: Original document {original_id} not found.")
                skipped_missing_data += 1
                continue
            if not augmented_doc:
                logger.warning(f"Skipping doc {analysis_doc_id}: Augmented document {augmented_id} not found.")
                skipped_missing_data += 1
                continue

            # Decode Original RTL
            original_rtl = None
            plugin_files = original_doc.get("plugin_files", {})
            target_suffix = "RTL_Protected.txt" 
            for filename, file_data in plugin_files.items():
                if filename.endswith(target_suffix):
                    original_rtl = decode_rtl_content(file_data.get("content"))
                    break
            if not original_rtl:
                 logger.warning(f"Skipping doc {analysis_doc_id}: Could not find/decode original RTL content for {original_id}.")
                 skipped_missing_data += 1
                 # Continue processing augmented if possible, but flag doc as having issues
                 has_error = True 

            # Decode Augmented RTL
            augmented_content = augmented_doc.get("augmented_content")
            augmented_rtl = decode_rtl_content(augmented_content)
            if not augmented_rtl:
                logger.warning(f"Skipping doc {analysis_doc_id}: Could not decode augmented RTL content for {augmented_id}.")
                skipped_missing_data += 1
                has_error = True 
                # If both RTLs failed, skip entirely for samples
                if not original_rtl: continue 

            # Extract analysis results safely
            original_analysis = doc.get("original_analysis")
            augmented_analysis = doc.get("augmented_analysis")

            orig_graph = get_nested(original_analysis, ['graph'])
            orig_prot = get_nested(original_analysis, ['protection'])
            orig_verif = get_nested(original_analysis, ['verification'])

            aug_graph = get_nested(augmented_analysis, ['graph'])
            aug_prot = get_nested(augmented_analysis, ['protection'])
            aug_verif = get_nested(augmented_analysis, ['verification'])
            
            # --- Generate Samples ---
            
            # Task 1: Graph Analysis (Original)
            if original_rtl and orig_graph:
                sample = {
                    "instruction": INSTRUCTIONS["graph_analysis"],
                    "input": original_rtl,
                    "output": json.dumps(orig_graph, ensure_ascii=False) # Output is the graph JSON string
                }
                all_samples.append(sample)
                generated_samples += 1
                doc_samples += 1

            # Task 1: Graph Analysis (Augmented)
            if augmented_rtl and aug_graph:
                sample = {
                    "instruction": INSTRUCTIONS["graph_analysis"],
                    "input": augmented_rtl,
                    "output": json.dumps(aug_graph, ensure_ascii=False) 
                }
                all_samples.append(sample)
                generated_samples += 1
                doc_samples += 1

            # Task 2: Protection Determination (Original)
            if orig_graph and orig_prot:
                sample = {
                    "instruction": INSTRUCTIONS["protection_determination"],
                    "input": json.dumps(orig_graph, ensure_ascii=False), # Input is the graph JSON string
                    "output": json.dumps(orig_prot, ensure_ascii=False) # Output is protection JSON string
                }
                all_samples.append(sample)
                generated_samples += 1
                doc_samples += 1

            # Task 2: Protection Determination (Augmented)
            if aug_graph and aug_prot:
                sample = {
                    "instruction": INSTRUCTIONS["protection_determination"],
                    "input": json.dumps(aug_graph, ensure_ascii=False), 
                    "output": json.dumps(aug_prot, ensure_ascii=False) 
                }
                all_samples.append(sample)
                generated_samples += 1
                doc_samples += 1

            # Task 3: Rule Verification (Original)
            protection_type_orig = get_nested(orig_prot, ['protection_type'])
            if original_rtl and orig_graph and protection_type_orig and orig_verif:
                input_data = {
                    "code": original_rtl,
                    "graph_json": orig_graph,
                    "protection_type": protection_type_orig,
                    "rules_text": rules_text
                }
                sample = {
                    "instruction": INSTRUCTIONS["rule_verification"],
                    "input": json.dumps(input_data, ensure_ascii=False), # Combined input JSON string
                    "output": json.dumps(orig_verif, ensure_ascii=False) # Output is verification JSON string
                }
                all_samples.append(sample)
                generated_samples += 1
                doc_samples += 1
            
            # Task 3: Rule Verification (Augmented)
            protection_type_aug = get_nested(aug_prot, ['protection_type'])
            if augmented_rtl and aug_graph and protection_type_aug and aug_verif:
                input_data = {
                    "code": augmented_rtl,
                    "graph_json": aug_graph,
                    "protection_type": protection_type_aug,
                    "rules_text": rules_text
                }
                sample = {
                    "instruction": INSTRUCTIONS["rule_verification"],
                    "input": json.dumps(input_data, ensure_ascii=False), 
                    "output": json.dumps(aug_verif, ensure_ascii=False) 
                }
                all_samples.append(sample)
                generated_samples += 1
                doc_samples += 1

            if doc_samples == 0:
                logger.warning(f"Doc {analysis_doc_id} yielded 0 samples due to missing data.")
                # Increment skip count if we didn't already for missing docs/RTL
                if not has_error: skipped_missing_data += 1
            
            if has_error: error_docs +=1

            if processed_docs % 100 == 0:
                logger.info(f"Processed {processed_docs}/{total_docs} documents...")
                
        # 4. Write collected data to Parquet file
        if all_samples:
            logger.info(f"Converting {len(all_samples)} samples to Parquet format...")
            try:
                df = pd.DataFrame(all_samples)
                table = pa.Table.from_pandas(df)
                logger.info(f"Writing Parquet table to: {output_file_path}")
                pq.write_table(table, output_file_path)
                logger.info("Successfully wrote Parquet file.")
            except Exception as write_e:
                logger.error(f"Failed to write Parquet file: {write_e}", exc_info=True)
        else:
            logger.warning("No samples were generated, skipping Parquet file creation.")
                
    except Exception as e:
        logger.error(f"An unexpected critical error occurred during processing: {e}", exc_info=True)
    finally:
        logger.info("--- Export Summary ---")
        logger.info(f"Documents processed from '{input_collection_name}': {processed_docs}")
        logger.info(f"Fine-tuning samples generated: {generated_samples}")
        logger.info(f"Documents skipped due to missing data/errors: {skipped_missing_data + error_docs}")
        logger.info(f"(Breakdown: Missing linked docs/RTL: {skipped_missing_data}, Other processing errors: {error_docs})")
        if all_samples:
        logger.info(f"Output written to: {output_file_path}")
        logger.info("Export process finished.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export MongoDB analysis results to Parquet for fine-tuning.")
    parser.add_argument(
        "--input-collection", 
        default="distillation_outputs", 
        help="Name of the MongoDB collection containing analysis results (default: distillation_outputs)."
    )
    parser.add_argument(
        "--rules-file", 
        required=True, 
        help="Path to the rules.md file."
    )
    parser.add_argument(
        "--output-file", 
        required=True, 
        help="Path to the output Parquet file (e.g., data/finetune_data.parquet)."
    )
    args = parser.parse_args()

    # Validate rules file exists before starting
    if not Path(args.rules_file).is_file():
        logger.error(f"Error: Rules file not found: {args.rules_file}")
        sys.exit(1)

    export_data(
        input_collection_name=args.input_collection,
        rules_file_path=args.rules_file,
        output_file_path=args.output_file
    ) 