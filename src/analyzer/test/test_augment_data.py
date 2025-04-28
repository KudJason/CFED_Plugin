import sys
import os
import pytest
from unittest.mock import patch, MagicMock, call
from bson import ObjectId
import logging

# Use relative imports since we're inside the analyzer package
from ..scripts import augment_data
from ..model.data_model import DataModel, PluginFile
from ..model.augmented_data_model import AugmentType

# Need the real DBService temporarily for fetching test data
from ..service.db_service import DBService as RealDBService

# Disable logging during tests unless specifically testing logging
logging.disable(logging.CRITICAL)

# --- Fixtures and Mock Data --- 

@pytest.fixture
def mock_db_service():
    """Mocks the DBService and its collection interactions."""
    mock_service = MagicMock()
    mock_plugin_outputs_collection = MagicMock()
    mock_augmented_outputs_collection = MagicMock()

    mock_service.get_collection.side_effect = lambda name: \
        mock_plugin_outputs_collection if name == "plugin_outputs" else \
        mock_augmented_outputs_collection if name == "augmented_plugin_outputs" else \
        MagicMock()
    
    # Simulate find() returning an iterable cursor
    mock_plugin_outputs_collection.find.return_value = [] 
    mock_plugin_outputs_collection.count_documents.return_value = 0
    mock_augmented_outputs_collection.insert_one.return_value = MagicMock()

    return mock_service, mock_plugin_outputs_collection, mock_augmented_outputs_collection

@pytest.fixture
def mock_augment_service():
    """Mocks the DataAugmentService."""
    mock_service = MagicMock()
    mock_service.augment_code.return_value = "AUGMENTED CONTENT"
    return mock_service

@pytest.fixture
def mock_extract_core_instructions():
    """Mocks the extract_core_instructions function."""
    mock_func = MagicMock()
    mock_func.return_value = "CLEANED CODE"
    return mock_func

# --- Test Cases --- 

def test_successful_augmentation(mock_db_service, mock_augment_service, mock_extract_core_instructions):
    """Tests the end-to-end successful augmentation case."""
    mock_service, mock_plugin_coll, mock_augmented_coll = mock_db_service
    
    # Setup estimated_document_count mock
    mock_plugin_coll.estimated_document_count.return_value = 1
    
    # Prepare mock input data
    record_id = ObjectId()
    mock_record = {
        '_id': record_id,
        'build_id': 'test_build_123',
        'algorithm_name': 'test_algorithm',
        'algorithm_path': 'test/path',
        'technique': 'test_technique',
        'technique_type': 'test_type',
        'selective_level': 'test_level',
        'plugin_files': {
            'some_other_file.txt/function/doc': PluginFile(content='other data', function_name='function', doc_name='doc'),
            'design.RTL_Protected.txt/function/doc': PluginFile(content='original rtl content', function_name='function', doc_name='doc'),
        }
    }
    mock_plugin_coll.find.return_value = [mock_record]

    # Use hardcoded patch paths based on our observed imports
    with patch('src.analyzer.service.db_service.DBService', return_value=mock_service), \
         patch('src.analyzer.data_util.data_augment_service.DataAugmentService', return_value=mock_augment_service), \
         patch('src.analyzer.data_util.key_info_extraction.extract_core_instructions', mock_extract_core_instructions), \
         patch('src.analyzer.scripts.augment_data.load_dotenv') as mock_load_dotenv:

        augment_data.main()

        # --- Assertions ---
        print("Checking assertions...") # Debug print
        mock_load_dotenv.assert_called_once()
        mock_service.get_collection.assert_any_call("plugin_outputs")
        mock_service.get_collection.assert_any_call("augmented_plugin_outputs")
        mock_plugin_coll.find.assert_called_once_with({})
        
        # Check that estimated_document_count was called, not count_documents
        mock_plugin_coll.estimated_document_count.assert_called_once()
        mock_plugin_coll.count_documents.assert_not_called()
        
        mock_extract_core_instructions.assert_called_once_with('original rtl content')
        mock_augment_service.augment_code.assert_called_once_with("CLEANED CODE", AugmentType.DUPLICATE_BLOCKS)
        
        expected_augmented_doc = {
            "original_id": record_id,
            "augmented_content": "AUGMENTED CONTENT",
            "augment_type": AugmentType.DUPLICATE_BLOCKS.value 
        }
        mock_augmented_coll.insert_one.assert_called_once_with(expected_augmented_doc)
        mock_service.close_connection.assert_called_once()

def test_no_rtl_file(mock_db_service, mock_augment_service, mock_extract_core_instructions):
    """Tests the case where the RTL_Protected file is missing."""
    mock_service, mock_plugin_coll, mock_augmented_coll = mock_db_service
    
    record_id = ObjectId()
    mock_record = {
        '_id': record_id,
        'build_id': 'test_build_no_rtl',
        'algorithm_name': 'test_algorithm',
        'algorithm_path': 'test/path',
        'technique': 'test_technique',
        'technique_type': 'test_type',
        'selective_level': 'test_level',
        'plugin_files': {
            'some_other_file.txt/function/doc': PluginFile(content='other data', function_name='function', doc_name='doc'),
        }
    }
    mock_plugin_coll.find.return_value = [mock_record]

    with patch('src.analyzer.service.db_service.DBService', return_value=mock_service), \
         patch('src.analyzer.data_util.data_augment_service.DataAugmentService', return_value=mock_augment_service), \
         patch('src.analyzer.data_util.key_info_extraction.extract_core_instructions', mock_extract_core_instructions), \
         patch('src.analyzer.scripts.augment_data.load_dotenv'):

        augment_data.main()

        # Assertions
        mock_extract_core_instructions.assert_not_called()
        mock_augment_service.augment_code.assert_not_called()
        mock_augmented_coll.insert_one.assert_not_called()
        mock_service.close_connection.assert_called_once()

def test_rtl_decode_error(mock_db_service, mock_augment_service, mock_extract_core_instructions):
    """Tests the case where the RTL file content cannot be decoded."""
    mock_service, mock_plugin_coll, mock_augmented_coll = mock_db_service
    
    record_id = ObjectId()
    mock_record = {
        '_id': record_id,
        'build_id': 'test_build_decode_error',
        'algorithm_name': 'test_algorithm',
        'algorithm_path': 'test/path',
        'technique': 'test_technique',
        'technique_type': 'test_type',
        'selective_level': 'test_level',
        'plugin_files': {
            'design.RTL_Protected.txt/function/doc': PluginFile(content=b'\x80abc', function_name='function', doc_name='doc'),
        }
    }
    mock_plugin_coll.find.return_value = [mock_record]

    with patch('src.analyzer.service.db_service.DBService', return_value=mock_service), \
         patch('src.analyzer.data_util.data_augment_service.DataAugmentService', return_value=mock_augment_service), \
         patch('src.analyzer.data_util.key_info_extraction.extract_core_instructions', mock_extract_core_instructions), \
         patch('src.analyzer.scripts.augment_data.load_dotenv'):

        augment_data.main()

        # Assertions
        mock_extract_core_instructions.assert_not_called()
        mock_augment_service.augment_code.assert_not_called()
        mock_augmented_coll.insert_one.assert_not_called()
        mock_service.close_connection.assert_called_once()

def test_extraction_failure(mock_db_service, mock_augment_service, mock_extract_core_instructions):
    """Tests the case where extract_core_instructions returns None."""
    mock_service, mock_plugin_coll, mock_augmented_coll = mock_db_service
    mock_extract_core_instructions.return_value = None # Simulate extraction failure
    
    record_id = ObjectId()
    mock_record = {
        '_id': record_id,
        'build_id': 'test_build_extract_fail',
        'algorithm_name': 'test_algorithm',
        'algorithm_path': 'test/path',
        'technique': 'test_technique',
        'technique_type': 'test_type',
        'selective_level': 'test_level',
        'plugin_files': {
            'design.RTL_Protected.txt/function/doc': PluginFile(content='original rtl content', function_name='function', doc_name='doc'),
        }
    }
    mock_plugin_coll.find.return_value = [mock_record]

    with patch('src.analyzer.service.db_service.DBService', return_value=mock_service), \
         patch('src.analyzer.data_util.data_augment_service.DataAugmentService', return_value=mock_augment_service), \
         patch('src.analyzer.data_util.key_info_extraction.extract_core_instructions', mock_extract_core_instructions), \
         patch('src.analyzer.scripts.augment_data.load_dotenv'):

        augment_data.main()

        # Assertions
        mock_extract_core_instructions.assert_called_once_with('original rtl content')
        mock_augment_service.augment_code.assert_not_called()
        mock_augmented_coll.insert_one.assert_not_called()
        mock_service.close_connection.assert_called_once()

def test_augmentation_failure(mock_db_service, mock_augment_service, mock_extract_core_instructions):
    """Tests the case where augment_code returns None."""
    mock_service, mock_plugin_coll, mock_augmented_coll = mock_db_service
    mock_augment_service.augment_code.return_value = None # Simulate augmentation failure
    
    record_id = ObjectId()
    mock_record = {
        '_id': record_id,
        'build_id': 'test_build_augment_fail',
        'algorithm_name': 'test_algorithm',
        'algorithm_path': 'test/path',
        'technique': 'test_technique',
        'technique_type': 'test_type',
        'selective_level': 'test_level',
        'plugin_files': {
            'design.RTL_Protected.txt/function/doc': PluginFile(content='original rtl content', function_name='function', doc_name='doc'),
        }
    }
    mock_plugin_coll.find.return_value = [mock_record]

    with patch('src.analyzer.service.db_service.DBService', return_value=mock_service), \
         patch('src.analyzer.data_util.data_augment_service.DataAugmentService', return_value=mock_augment_service), \
         patch('src.analyzer.data_util.key_info_extraction.extract_core_instructions', mock_extract_core_instructions), \
         patch('src.analyzer.scripts.augment_data.load_dotenv'):

        augment_data.main()

        # Assertions
        mock_extract_core_instructions.assert_called_once_with('original rtl content')
        mock_augment_service.augment_code.assert_called_once_with("CLEANED CODE", AugmentType.DUPLICATE_BLOCKS)
        mock_augmented_coll.insert_one.assert_not_called()
        mock_service.close_connection.assert_called_once()


def test_multiple_records(mock_db_service, mock_augment_service, mock_extract_core_instructions):
    """Tests processing multiple records with mixed success/failure."""
    mock_service, mock_plugin_coll, mock_augmented_coll = mock_db_service
    
    record_id_ok = ObjectId()
    record_id_no_rtl = ObjectId()
    record_id_fail_augment = ObjectId()
    
    mock_records = [
        { # Successful
            '_id': record_id_ok,
            'build_id': 'test_build_ok',
            'algorithm_name': 'test_algorithm',
            'algorithm_path': 'test/path',
            'technique': 'test_technique',
            'technique_type': 'test_type',
            'selective_level': 'test_level',
            'plugin_files': {'design.RTL_Protected.txt/function/doc': PluginFile(content='rtl ok', function_name='function', doc_name='doc') }
        },
        { # No RTL file
            '_id': record_id_no_rtl,
            'build_id': 'test_build_no_rtl',
            'algorithm_name': 'test_algorithm',
            'algorithm_path': 'test/path',
            'technique': 'test_technique',
            'technique_type': 'test_type',
            'selective_level': 'test_level',
            'plugin_files': { 'other.file/function/doc': PluginFile(content='x', function_name='function', doc_name='doc') }
        },
        { # Augmentation fails
            '_id': record_id_fail_augment,
            'build_id': 'test_build_augment_fail',
            'algorithm_name': 'test_algorithm',
            'algorithm_path': 'test/path',
            'technique': 'test_technique',
            'technique_type': 'test_type',
            'selective_level': 'test_level',
            'plugin_files': {'design.RTL_Protected.txt/function/doc': PluginFile(content='rtl fail augment', function_name='function', doc_name='doc') }
        }
    ]
    mock_plugin_coll.find.return_value = mock_records

    # Make augmentation fail only for the specific content
    def augment_side_effect(cleaned_code, augment_type):
        if cleaned_code == "CLEANED CODE_fail_augment":
            return None
        return "AUGMENTED CONTENT"
    mock_augment_service.augment_code.side_effect = augment_side_effect

    def extract_side_effect(rtl_content):
         if rtl_content == "rtl fail augment":
             return "CLEANED CODE_fail_augment"
         return "CLEANED CODE"
    mock_extract_core_instructions.side_effect = extract_side_effect

    with patch('src.analyzer.service.db_service.DBService', return_value=mock_service), \
         patch('src.analyzer.data_util.data_augment_service.DataAugmentService', return_value=mock_augment_service), \
         patch('src.analyzer.data_util.key_info_extraction.extract_core_instructions', mock_extract_core_instructions), \
         patch('src.analyzer.scripts.augment_data.load_dotenv'):

        augment_data.main()

        # Assertions
        assert mock_extract_core_instructions.call_count == 2 # Called for ok and fail_augment records
        assert mock_augment_service.augment_code.call_count == 2 # Called for ok and fail_augment records
        
        expected_augmented_doc = {
            "original_id": record_id_ok,
            "augmented_content": "AUGMENTED CONTENT",
            "augment_type": AugmentType.DUPLICATE_BLOCKS.value
        }
        mock_augmented_coll.insert_one.assert_called_once_with(expected_augmented_doc)
        mock_service.close_connection.assert_called_once() 