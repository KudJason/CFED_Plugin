"""Script to augment code data using LLM (Asynchronous Version with File Persistence)."""

import sys
import os
from typing import Optional, Tuple, List, Dict, Any
from bson import ObjectId
import logging
from dotenv import load_dotenv
import asyncio 
import random 
from tqdm.asyncio import tqdm # Import tqdm for asyncio

# Import service classes and models
from ..service.db_service import DBService
from ..model.data_model import DataModel, PluginFile # Use correct class name
from ..data_util.key_info_extraction import extract_core_instructions
from ..data_util.data_augment_service import DataAugmentService
from ..model.augmented_data_model import AugmentType # Correct import path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
STATE_FILE_DIR = "/workspace/data"
STATE_FILE_NAME = "augmented_ids.txt"
STATE_FILE_PATH = os.path.join(STATE_FILE_DIR, STATE_FILE_NAME)

def find_rtl_protected_content(data_model: DataModel) -> str | None:
    """Finds the content of the RTL_Protected file within a DataModel."""
    rtl_file_content = None
    if data_model.plugin_files is None:
        logging.warning(f"plugin_files is None for build ID {data_model.build_id}. Skipping.")
        return None
        
    for filename, file_data in data_model.plugin_files.items():
        logging.debug(f"  Checking file: {filename}") 
        # Use endswith check - verify this matches actual file names in record.json!
        if filename.endswith("RTL_Protected.txt") or filename.endswith("RTL.txt"): 
            logging.debug(f"    Found matching file: {filename}") 
            if file_data is None:
                logging.warning(f"Found matching file {filename} but file_data is None. Skipping.")
                continue
            rtl_file_content = file_data.content
            break

    if rtl_file_content:
        if isinstance(rtl_file_content, bytes):
            try:
                return rtl_file_content.decode('utf-8')
            except UnicodeDecodeError:
                logging.warning(f"Could not decode RTL file content for build ID {data_model.build_id}. Skipping.")
                return None
        elif isinstance(rtl_file_content, str):
            if rtl_file_content.startswith("b'") and rtl_file_content.endswith("'"):
                try:
                    import ast
                    bytes_content = ast.literal_eval(rtl_file_content)
                    return bytes_content.decode('utf-8')
                except Exception as e:
                    logging.warning(f"Could not eval/decode b'...' string for {data_model.build_id}: {e}. Skipping.")
                    return None
            else:
                 return rtl_file_content
        else:
             logging.warning(f"Unexpected content type for RTL file in build ID {data_model.build_id}: {type(rtl_file_content)}. Skipping.")
             return None
    else:
        logging.warning(f"No RTL_Protected/RTL file found for build ID {data_model.build_id}. Skipping.")
        return None

# Get all available augmentation types
ALL_AUGMENT_TYPES = list(AugmentType)

# Helper function to write to state file asynchronously and safely
async def append_to_state_file(record_id_str: str, file_path: str, lock: asyncio.Lock):
    async with lock:
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            # Use asyncio.to_thread for the blocking file I/O
            await asyncio.to_thread(
                lambda: print(record_id_str, file=open(file_path, 'a', encoding='utf-8'))
            )
        except IOError as e:
            logging.error(f"Error writing to state file {file_path}: {e}")

# --- Asynchronous Processing Function ---
async def process_record(
    record_id: ObjectId,
    db_service: DBService, # Pass instance for collection access
    augment_service: DataAugmentService, 
    semaphore: asyncio.Semaphore,
    state_file_path: str, # Path to the state file
    file_lock: asyncio.Lock # Lock for writing to the state file
) -> Dict[str, Any]:
    """Processes a single record asynchronously and logs ID to file on success."""
    async with semaphore: # Limit concurrency
        plugin_outputs_collection = db_service.get_collection("plugin_outputs")
        augmented_outputs_collection = db_service.get_collection("augmented_plugin_outputs")
        
        loop = asyncio.get_running_loop()
        record = None
        status = {"id": str(record_id), "status": "skipped", "error": None, "augment_type": None} 

        try:
            record = await asyncio.to_thread(plugin_outputs_collection.find_one, {'_id': record_id})

            if not record:
                logging.warning(f"Record {record_id} not found during async processing.")
                status["error"] = "Record not found"
                return status

            required_keys = ['algorithm_name', 'algorithm_path', 'technique', 
                             'technique_type', 'selective_level', 'plugin_files']
            if not all(key in record for key in required_keys):
                logging.warning(f"Record {record_id} missing required keys. Skipping.")
                status["error"] = "Missing required keys"
                return status
                
            data = await asyncio.to_thread(DataModel.from_dict, record)
            rtl_content = find_rtl_protected_content(data)

            if not rtl_content:
                status["error"] = "No RTL content found"
                return status 

            cleaned_code = await asyncio.to_thread(extract_core_instructions, rtl_content)
            if not cleaned_code:
                logging.warning(f"Could not extract core instructions for {record_id}. Skipping.")
                status["error"] = "Extraction failed"
                return status

            chosen_augment_type = random.choice(ALL_AUGMENT_TYPES)
            status["augment_type"] = chosen_augment_type.value 

            # Call the updated augment_service.augment_code
            # It now returns None on failure/parsing error
            augmented_content = await asyncio.to_thread(
                augment_service.augment_code, cleaned_code, chosen_augment_type 
            )

            if augmented_content is None: # Check for None explicitly
                logging.warning(f"Augmentation failed or returned None for {record_id} ({chosen_augment_type.value}). Skipping.")
                status["error"] = "Augmentation failed or produced no result"
                return status

            # Prepare the document, adding the 'label' field
            augmented_doc = {
                "original_id": record_id,
                "augmented_content": augmented_content,
                "augment_type": chosen_augment_type.value, 
                "label": "augmented" # Added label field
            }

            # Insert the augmented data (blocking I/O)
            await asyncio.to_thread(augmented_outputs_collection.insert_one, augmented_doc)
            
            # If insert succeeds, log ID to state file
            await append_to_state_file(str(record_id), state_file_path, file_lock)
            
            logging.info(f"Successfully augmented record {record_id} with type {chosen_augment_type.value} (and logged to state file)")
            status["status"] = "augmented"
            return status

        except Exception as e:
            logging.error(f"Error processing record {record_id}: {e}", exc_info=True)
            status["status"] = "error"
            status["error"] = str(e)
            return status

# Helper function to load IDs from state file
def load_ids_from_file(file_path: str) -> set:
    processed_ids = set()
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line: # Avoid adding empty lines
                        try:
                            # Attempt to convert to ObjectId to validate, store as string or ObjectId based on need
                            # Storing as ObjectId might be slightly more robust if comparing later
                            processed_ids.add(ObjectId(line))
                        except Exception:
                            logging.warning(f"Ignoring invalid ObjectId found in state file: {line}")
        except IOError as e:
            logging.error(f"Error reading state file {file_path}: {e}")
    return processed_ids

# --- Main Asynchronous Function ---
async def main():
    """Main async function to process and augment data, skipping records listed in the state file."""
    
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
    dotenv_path = os.path.join(workspace_root, 'data', '.env') 
    print(f"DEBUG: Attempting to load .env from: {dotenv_path}") 
    loaded = load_dotenv(dotenv_path=dotenv_path, override=True)
    logging.info(f"Loaded .env file from: {dotenv_path} (Loaded: {loaded})")

    db_service = None
    processed_count = 0
    augmented_count = 0
    skipped_count = 0 # Records skipped within process_record
    error_count = 0
    skipped_from_file_count = 0 # Counter for skipped records based on state file
    file_lock = asyncio.Lock() # Lock for state file writing

    try:
        # Load processed IDs from state file first 
        logging.info(f"Loading processed IDs from state file: {STATE_FILE_PATH}")
        processed_ids_from_file = load_ids_from_file(STATE_FILE_PATH)
        skipped_from_file_count = len(processed_ids_from_file)
        logging.info(f"Found {skipped_from_file_count} IDs in state file. These will be skipped.")

        db_service = DBService()
        augment_service = DataAugmentService()

        plugin_outputs_collection = db_service.get_collection("plugin_outputs")
        # augmented_outputs_collection is only needed inside process_record now
        
        logging.info("Fetching all source record IDs...")
        # Fetch all potential source IDs (run DB query in thread)
        all_plugin_ids = await asyncio.to_thread(
            lambda: [r['_id'] for r in plugin_outputs_collection.find({}, {'_id': 1})]
        )
        total_source_docs = len(all_plugin_ids)
        logging.info(f"Found {total_source_docs} total source documents.")

        # Filter out already processed IDs based *only* on the state file
        ids_to_process = [pid for pid in all_plugin_ids if pid not in processed_ids_from_file]
        total_docs_to_process = len(ids_to_process)
        
        if total_docs_to_process == 0:
             logging.info("No new documents to process (all found in state file or source is empty). Exiting.")
             return

        logging.info(f"Starting data augmentation process for {total_docs_to_process} new documents...")
        
        semaphore = asyncio.Semaphore(3) 
        
        # Create tasks only for the IDs that need processing
        tasks = [
            asyncio.create_task(
                process_record(
                    rec_id, 
                    db_service, 
                    augment_service, 
                    semaphore, 
                    STATE_FILE_PATH, # Pass state file path
                    file_lock        # Pass file lock
                )
            ) 
            for rec_id in ids_to_process # Use the filtered list
        ]
        
        results = await tqdm.gather(*tasks, desc="Augmenting Data", total=total_docs_to_process) 

        processed_count = len(results) 
        for result in results:
            if result["status"] == "augmented":
                augmented_count += 1
            elif result["status"] == "error":
                 error_count += 1
            elif result["status"] == "skipped": 
                skipped_count += 1

        logging.info("Data augmentation process finished for this run.")
        logging.info(f"Records attempted in this run: {processed_count}")
        logging.info(f"Successfully augmented in this run: {augmented_count}")
        logging.info(f"Skipped (during processing) in this run: {skipped_count}")
        logging.info(f"Errored in this run: {error_count}")
        logging.info(f"Records skipped based on state file ({STATE_FILE_NAME}): {skipped_from_file_count}")

    except Exception as e:
        logging.error(f"An critical error occurred during setup or task gathering: {e}", exc_info=True)
    finally:
        if db_service:
            db_service.close_connection()
            logging.info("MongoDB connection closed.")

if __name__ == "__main__":
    asyncio.run(main()) 