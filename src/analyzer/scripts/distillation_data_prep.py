"""
Script to prepare distillation data from original and augmented RTL code in MongoDB.
Fetches paired original/augmented RTL code from database, analyzes both with 5 concurrent threads,
and stores analysis results back to the database.

Example Usage (run as module from workspace root):
python -m src.analyzer.scripts.distillation_data_prep \
    --rules-file dev_docs/rules.md \
    --output-collection distillation_outputs \
    --limit 100
"""

import argparse
import json
import sys
import os
import ast
import concurrent.futures
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from bson import ObjectId
import logging
import time
import threading

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
# State file to track processed augmented document IDs
DISTILLATION_STATE_FILE_DIR = "/workspace/data"
DISTILLATION_STATE_FILE_NAME = "distillation_processed_ids.txt"
DISTILLATION_STATE_FILE_PATH = os.path.join(DISTILLATION_STATE_FILE_DIR, DISTILLATION_STATE_FILE_NAME)

# --- Use Real LLM Service --- 
try:
    from dotenv import load_dotenv
    # Import the function that returns the LangChain LLM instance
    from src.analyzer.service.llm_service import get_langchain_llm

    def get_llm_instance():
        logger.info("Initializing DeepSeek LLM...")
        # Load environment variables (ensure DEEPSEEK_API_KEY is set)
        load_dotenv()
        try:
            llm = get_langchain_llm()
            logger.info("DeepSeek LLM Initialized successfully.")
            return llm
        except ValueError as e:
            logger.error(f"Error initializing LLM: {e}")
            logger.error("Please ensure the DEEPSEEK_API_KEY environment variable is set correctly.")
            sys.exit(1)
        except ImportError as e:
            # Handle cases where deepseek provider isn't installed
            logger.error(f"Import Error for LLM: {e}. Is langchain-deepseek installed?")
            sys.exit(1)
        except Exception as e:
            # Catch other potential initialization errors
            logger.error(f"An unexpected error occurred during LLM initialization: {e}")
            sys.exit(1)

except ImportError as e:
    logger.error(f"Import Error: {e}. LangChain, python-dotenv or necessary provider package might be missing.")
    logger.error("Please install required packages (e.g., pip install langchain langchain-deepseek python-dotenv pydantic)")
    sys.exit(1)

# --- Service and Util Imports --- 
# Use relative imports - requires running script as module (python -m ...)
try:
    from ..service.distillation_data_prep_service import DistillationDataPrepService
    from ..service.db_service import DBService
    from ..data_util.file_utils import load_rules
    from ..data_util.key_info_extraction import extract_core_instructions
    from ..prompts.distillation.models import (
        GraphAnalysisOutput,
        ProtectionDeterminationOutput,
        RuleVerificationOutput,
    )
except ImportError as e:
    logger.error(f"Error importing service or utils: {e}")
    logger.error("Ensure the script is run as a module from the workspace root (e.g., python -m src.analyzer.scripts.distillation_data_prep)")
    sys.exit(1)
# --- End Service and Util Imports ---

# --- State File Handling --- 
def load_processed_distillation_ids(file_path: str) -> set:
    """Loads processed augmented document IDs from the state file."""
    processed_ids = set()
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            processed_ids.add(ObjectId(line)) # Store as ObjectId for easier comparison
                        except Exception:
                            logger.warning(f"Ignoring invalid ObjectId found in state file: {line}")
        except IOError as e:
            logger.error(f"Error reading state file {file_path}: {e}")
    return processed_ids

def append_to_distillation_state_file(record_id: ObjectId, file_path: str, lock: threading.Lock):
    """Appends a successfully processed augmented document ID to the state file (thread-safe)."""
    with lock:
        try:
            logger.debug(f"Attempting to write ID {record_id} to state file {file_path}")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(str(record_id) + '\n')
            logger.debug(f"Successfully wrote ID {record_id} to state file {file_path}")
        except IOError as e:
            logger.error(f"Error writing to state file {file_path}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error writing to state file {file_path} for ID {record_id}: {e}", exc_info=True)

# --- Decoding Function --- 
def decode_rtl_content(content) -> str:
    """
    Decode RTL content from various formats (bytes, string, byte string literal).
    Returns None if decoding fails.
    """
    if content is None:
        return None
        
    if isinstance(content, bytes):
        try:
            return content.decode('utf-8')
        except UnicodeDecodeError:
            logger.warning(f"Could not decode RTL content (bytes). Skipping.")
            return None
    
    elif isinstance(content, str):
        if content.startswith("b'") and content.endswith("'"):
            try:
                bytes_content = ast.literal_eval(content)
                return bytes_content.decode('utf-8')
            except Exception as e:
                logger.warning(f"Could not eval/decode b'...' string: {e}. Skipping.")
                return None
        else:
            return content
    
    else:
        logger.warning(f"Unexpected content type: {type(content)}. Skipping.")
        return None

# --- Processing Function --- 
def process_augmented_doc(
    augmented_doc: Dict[str, Any], 
    llm_instance,
    rules_text: str,
    output_collection_name: str,
    state_file_path: str,
    file_lock: threading.Lock
) -> Dict[str, Any]:
    """
    Process a single augmented document by:
    1. Fetching its original document
    2. Decoding and preprocessing both code versions
    3. Running all analysis steps on both (but not the final report)
    4. Structuring and storing the results in the output collection
    5. Logging the augmented_id to the state file upon success.
    """
    start_time = time.time()
    augmented_id = augmented_doc.get("_id")
    result = {
        "status": "skipped",
        "error": None,
        "augmented_id": str(augmented_id if augmented_id else "unknown"),
        "original_id": str(augmented_doc.get("original_id", "unknown"))
    }
    
    # Get DBService instance within the thread
    db_service: Optional[DBService] = None
    try:
        try:
            db_service = DBService() # <<< Get instance here
            logger.debug(f"[{augmented_id}] Obtained DBService instance in thread: {db_service}")
        except Exception as db_init_e:
             result["error"] = f"Failed to initialize DBService in thread: {db_init_e}"
             logger.error(result["error"], exc_info=True)
             return result

        # --- DB Connection Check --- #
        logger.debug(f"[{augmented_id}] Checking DB connection before fetching original. DBService instance: {db_service}, DB: {db_service._db}")
        # Corrected check using 'is None'
        if db_service is None or db_service._db is None: 
             result["error"] = "DB connection invalid after obtaining DBService instance."
             logger.error(result["error"])
             return result
        # --- End DB Check --- #
        
        # 1. Get the original document
        plugin_outputs_collection = db_service.get_collection("plugin_outputs")
        original_id = augmented_doc.get("original_id")
        if not original_id:
            result["error"] = "No original_id found in augmented document"
            return result
            
        original_doc = plugin_outputs_collection.find_one({"_id": original_id})
        if not original_doc:
            result["error"] = f"Original document with id {original_id} not found"
            return result
            
        # 2. Get content from both documents
        # For augmented document
        augmented_content = augmented_doc.get("augmented_content")
        augmented_rtl = decode_rtl_content(augmented_content)
        if not augmented_rtl:
            result["error"] = "Could not decode augmented RTL content"
            return result
            
        # For original document - need to extract RTL from plugin_files
        original_rtl = None
        plugin_files = original_doc.get("plugin_files", {})
        target_suffix = "RTL_Protected.txt" # <<< Define the target suffix
        for filename, file_data in plugin_files.items():
            # <<< Modify condition to check ONLY for the specific suffix >>>
            if filename.endswith(target_suffix): 
                logger.debug(f"[{original_id}] Found original RTL file: {filename}")
                original_rtl = decode_rtl_content(file_data.get("content"))
                break # Found the target file, no need to check further
                
        if not original_rtl:
            result["error"] = f"Could not find or decode original RTL content with suffix '{target_suffix}'"
            logger.warning(f"[{original_id}] Could not find key ending with '{target_suffix}' in plugin_files: {list(plugin_files.keys())}")
            return result
            
        # 3. Preprocess both code versions
        logger.info(f"Extracting core instructions from original ({len(original_rtl)} bytes) and augmented ({len(augmented_rtl)} bytes) RTL...")
        # --- Add logging for code snippets --- #
        logger.debug(f"[{augmented_id}] Original RTL (first 500 chars):\n{original_rtl[:500]}")
        logger.debug(f"[{augmented_id}] Augmented RTL (first 500 chars):\n{augmented_rtl[:500]}")
        # --- End logging --- #
        processed_original = extract_core_instructions(original_rtl)
        processed_augmented = extract_core_instructions(augmented_rtl)
        # --- Add logging for processed code snippets --- #
        logger.debug(f"[{augmented_id}] Processed Original RTL (first 500 chars):\n{processed_original[:500]}")
        logger.debug(f"[{augmented_id}] Processed Augmented RTL (first 500 chars):\n{processed_augmented[:500]}")
        # --- End logging --- #
        
        # 4. Initialize service
        service = DistillationDataPrepService(llm=llm_instance)
        
        # 5. Run analysis steps on original code
        logger.info(f"Running analysis on original code for document {original_id}...")
        try:
            # Graph analysis returns DistillationPrompt, needs .runnable
            original_graph: GraphAnalysisOutput = service.graph_runnable.runnable.invoke({"code": processed_original})
            # --- Remove logging for LLM classification result --- #
            # logger.debug(f"[{original_id}] Original code graph analysis result: is_rtl={original_graph.is_rtl}, reason={original_graph.analysis_skipped_reason}") 
            # --- End logging removal --- #
            original_graph_json = original_graph.model_dump_json() if hasattr(original_graph, 'model_dump_json') else original_graph.json()
            
            # --- REMOVE RTL Check --- 
            # Indentation adjusted - these steps now always run
            # Protection determination returns Runnable directly, NO .runnable
            original_protection = service.protection_runnable.invoke({"graph_json": original_graph_json})
            original_protection_json = original_protection.model_dump_json() if hasattr(original_protection, 'model_dump_json') else original_protection.json()
            
            # Verification returns Runnable directly, NO .runnable
            original_verification = service.verification_runnable.invoke({
                "protection_type": original_protection.protection_type,
                "code": processed_original,
                "graph_json": original_graph_json,
                "rules_text": rules_text
            })
            original_verification_json = original_verification.model_dump_json() if hasattr(original_verification, 'model_dump_json') else original_verification.json()
            
            logger.info(f"Original code analysis complete for document {original_id}")
        except Exception as e:
            result["error"] = f"Error in original code analysis: {str(e)}"
            logger.error(f"Error analyzing original code: {e}", exc_info=True)
            return result
        
        # 6. Run analysis steps on augmented code
        logger.info(f"Running analysis on augmented code for document {augmented_id}...")
        try:
            # Graph analysis returns DistillationPrompt, needs .runnable
            augmented_graph: GraphAnalysisOutput = service.graph_runnable.runnable.invoke({"code": processed_augmented})
            # --- Remove logging for LLM classification result --- #
            # logger.debug(f"[{augmented_id}] Augmented code graph analysis result: is_rtl={augmented_graph.is_rtl}, reason={augmented_graph.analysis_skipped_reason}")
            # --- End logging removal --- #
            augmented_graph_json = augmented_graph.model_dump_json() if hasattr(augmented_graph, 'model_dump_json') else augmented_graph.json()

            # --- REMOVE RTL Check --- 
            # Indentation adjusted - these steps now always run
            # Protection determination returns Runnable directly, NO .runnable
            augmented_protection = service.protection_runnable.invoke({"graph_json": augmented_graph_json})
            augmented_protection_json = augmented_protection.model_dump_json() if hasattr(augmented_protection, 'model_dump_json') else augmented_protection.json()
            
            # Verification returns Runnable directly, NO .runnable
            augmented_verification = service.verification_runnable.invoke({
                "protection_type": augmented_protection.protection_type,
                "code": processed_augmented,
                "graph_json": augmented_graph_json,
                "rules_text": rules_text
            })
            augmented_verification_json = augmented_verification.model_dump_json() if hasattr(augmented_verification, 'model_dump_json') else augmented_verification.json()
            
            logger.info(f"Augmented code analysis complete for document {augmented_id}")
        except Exception as e:
            result["error"] = f"Error in augmented code analysis: {str(e)}"
            logger.error(f"Error analyzing augmented code: {e}", exc_info=True)
            return result
            
        # 7. Structure and store results
        distillation_output = {
            "original_id": original_id,
            "augmented_id": augmented_id,
            "augment_type": augmented_doc.get("augment_type"),
            "original_analysis": {
                "graph": json.loads(original_graph_json), # Always store graph result
                "protection": json.loads(original_protection_json) if original_protection_json else None, # Handle None
                "verification": json.loads(original_verification_json) if original_verification_json else None # Handle None
            },
            "augmented_analysis": {
                "graph": json.loads(augmented_graph_json), # Always store graph result
                "protection": json.loads(augmented_protection_json) if augmented_protection_json else None, # Handle None
                "verification": json.loads(augmented_verification_json) if augmented_verification_json else None # Handle None
            },
            "timestamp": time.time()
        }
        
        # --- DB Connection Check --- #
        logger.debug(f"[{augmented_id}] Checking DB connection before inserting results. DBService instance: {db_service}, DB: {db_service._db}")
        if db_service is None or db_service._db is None: 
             result["error"] = "DB connection lost or invalid before inserting results."
             logger.error(result["error"])
             # Don't write to state file if DB insert fails
             return result 
        # --- End DB Check --- #

        # Insert into output collection
        output_collection = db_service.get_collection(output_collection_name)
        insert_result = output_collection.insert_one(distillation_output)
        logger.debug(f"[{augmented_id}] DB insert result acknowledged: {insert_result.acknowledged}")

        # 8. Log success to state file (AFTER successful DB insert)
        if augmented_id and insert_result.acknowledged: # Ensure we have an ID and insert was successful
            append_to_distillation_state_file(augmented_id, state_file_path, file_lock)
        elif not insert_result.acknowledged:
             logger.warning(f"[{augmented_id}] DB insert was not acknowledged. Skipping state file write.")
             result["status"] = "error" # Consider it an error if DB write fails
             result["error"] = "Database insert not acknowledged"
             return result # Exit before marking completed
        
        # Update result status
        result["status"] = "completed"
        processing_time = time.time() - start_time
        logger.info(f"✓ Successfully processed, stored, and logged pair (Augmented ID: {augmented_id}) in {processing_time:.2f} seconds")
        return result
        
    except Exception as e:
        error_msg = f"Unexpected error processing document {augmented_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        result["status"] = "error"
        result["error"] = error_msg
        return result

def main():
    parser = argparse.ArgumentParser(description="Run Distillation Data Preparation Pipeline with MongoDB.")
    parser.add_argument("--rules-file", required=True, help="Path to the rules.md file.")
    parser.add_argument("--output-collection", required=True, help="Name of the MongoDB collection to store results.")
    parser.add_argument("--limit", type=int, default=None, help="Optional limit on number of document pairs to process.")
    args = parser.parse_args()

    rules_file_path = Path(args.rules_file)
    output_collection_name = args.output_collection
    limit = args.limit

    # Validate rules file path
    if not rules_file_path.is_file():
        logger.error(f"Error: Rules file not found: {rules_file_path}")
        sys.exit(1)

    # Load rules text
    logger.info(f"Loading rules from: {rules_file_path}")
    rules_text = load_rules(str(rules_file_path))
    if not rules_text:
        logger.error("Failed to load rules text. Exiting.")
        sys.exit(1)

    # Verify environment variables
    workspace_root = Path.cwd()
    dotenv_path = workspace_root / 'data' / '.env'
    if dotenv_path.exists():
        load_dotenv(dotenv_path=dotenv_path)
        logger.info(f"Loaded environment variables from: {dotenv_path}")
    else:
        logger.warning(f"Warning: .env file not found at {dotenv_path}. Ensure DEEPSEEK_API_KEY is set globally.")

    # Initialize services
    db_service_main = None # Keep a reference for closing later if needed, but don't pass it
    results = []
    total_docs = 0
    completed_count = 0
    error_count = 0
    skipped_count = 0
    skipped_from_file_count = 0
    file_lock = threading.Lock()

    try:
        logger.info("Initializing services (LLM only initially)...")
        # db_service_main = DBService() # Don't necessarily need to init DB in main thread now
        llm_instance = get_llm_instance()
        
        # Check DB connection briefly for setup purposes (optional)
        try:
            logger.info("Checking initial DB connectivity...")
            temp_db_service = DBService() # Get singleton instance
            temp_db_service.get_db() # Try getting the DB object
            logger.info("Initial DB connectivity check successful.")
            # Don't close here, let threads manage
        except Exception as e:
            logger.error(f"Initial DB connectivity check failed: {e}. Exiting.", exc_info=True)
            sys.exit(1)

        # Load already processed IDs from state file
        logger.info(f"Loading processed IDs from state file: {DISTILLATION_STATE_FILE_PATH}")
        processed_ids_from_file = load_processed_distillation_ids(DISTILLATION_STATE_FILE_PATH)
        logger.info(f"Found {len(processed_ids_from_file)} IDs in state file. These will be skipped.")
        
        # Prepare output collection if needed (needs a DBService instance)
        try:
            db_service_check = DBService() # Get singleton for check
            db = db_service_check.get_db() 
            if output_collection_name not in db.list_collection_names():
                logger.info(f"Creating new collection: {output_collection_name}")
            # Don't store db_service_check, let threads get their own reference
        except Exception as e:
             logger.error(f"Failed to check/create output collection {output_collection_name}: {e}. Exiting.", exc_info=True)
             sys.exit(1)
        
        # Query for augmented documents
        try: # Add try block for initial query
            db_service_main = DBService() # <<< Get singleton instance for main query
            augmented_outputs_collection = db_service_main.get_collection("augmented_plugin_outputs")
            query = {"label": "augmented"} 
            
            # Get count of *all* matching documents in DB
            total_augmented_in_db = augmented_outputs_collection.count_documents(query)
            logger.info(f"Found {total_augmented_in_db} augmented documents with label 'augmented' in database") 
            
            # Fetch all matching documents (potential candidates)
            cursor = augmented_outputs_collection.find(query) 
            all_augmented_docs_in_db = list(cursor)
            # Don't close db_service_main here, threads might still need the connection pool
        except Exception as e:
             logger.error(f"Failed to query augmented documents: {e}. Exiting.", exc_info=True)
             sys.exit(1)
        
        # Filter out already processed docs based on state file
        docs_to_process_list = [
            doc for doc in all_augmented_docs_in_db 
            if doc.get('_id') not in processed_ids_from_file
        ]
        skipped_from_file_count = len(all_augmented_docs_in_db) - len(docs_to_process_list)
        logger.info(f"Skipped {skipped_from_file_count} document pairs based on state file.")

        # Apply limit if specified (after filtering)
        if limit is not None and len(docs_to_process_list) > limit:
            logger.info(f"Applying limit: processing {limit} out of {len(docs_to_process_list)} remaining document pairs.")
            final_docs_to_process = docs_to_process_list[:limit]
        else:
            final_docs_to_process = docs_to_process_list
            logger.info(f"Will process {len(final_docs_to_process)} new document pairs")

        # If no documents to process, exit
        if not final_docs_to_process:
            logger.info("No new augmented documents found to process. Exiting.") 
            return
            
        # Setup thread pool for concurrent processing
        logger.info(f"Starting concurrent processing with 20 threads for {len(final_docs_to_process)} document pairs...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            # Submit all tasks - *removed db_service from arguments*
            future_to_doc = {
                executor.submit(
                    process_augmented_doc, 
                    doc, 
                    # db_service, # <<< Removed argument
                    llm_instance, 
                    rules_text, 
                    output_collection_name,
                    DISTILLATION_STATE_FILE_PATH, 
                    file_lock                   
                ): doc for doc in final_docs_to_process 
            }
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_doc):
                result = future.result()
                results.append(result)
                
                # Update counters
                if result["status"] == "completed":
                    completed_count += 1
                elif result["status"] == "error":
                    error_count += 1
                elif result["status"] == "skipped":
                    skipped_count += 1
                    
                # Periodically log progress
                if len(results) % 5 == 0 or len(results) == len(final_docs_to_process):
                    logger.info(f"Progress: {len(results)}/{len(final_docs_to_process)} ({completed_count} completed, {error_count} errors, {skipped_count} internal skips)")
        
        # Final status
        logger.info("=" * 50)
        logger.info("Distillation data preparation completed")
        logger.info(f"Total document pairs processed in this run: {len(results)}")
        logger.info(f"Successfully completed: {completed_count}")
        logger.info(f"Errors: {error_count}")
        logger.info(f"Skipped (during processing): {skipped_count}")
        logger.info(f"Skipped (already processed in state file): {skipped_from_file_count}")
        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"An critical error occurred: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Close connection if main thread instance was created (optional, maybe better handled by DBService itself)
        # If DBService manages its own lifecycle, explicit closing might not be needed here.
        # try:
        #     DBService().close_connection()
        #     logger.info("Database connection closed via singleton.")
        # except Exception:
        #      pass # Ignore errors during cleanup
        pass # Let threads finish and DBService handle its connection lifecycle

if __name__ == "__main__":
    main() 