"""
Utility functions for handling the mapping between UUID strings and integer IDs.
This helps resolve the mismatch between frontend (which uses UUIDs) and 
the database (which uses integer IDs).
"""

import os
import json
from typing import Union, Tuple, Optional
import glob
from config import settings
from supabase import create_client

def get_db_id_for_uuid(uuid_str: str) -> Optional[int]:
    """
    Get the database integer ID for a given UUID string.
    
    Args:
        uuid_str: The UUID string to look up
        
    Returns:
        The corresponding database integer ID, or None if not found
    """
    # First, check the local mapping file
    report_dir = os.path.join(settings.UPLOAD_DIR, uuid_str)
    mapping_path = os.path.join(report_dir, "id_mapping.json")
    
    if os.path.exists(mapping_path):
        try:
            with open(mapping_path, "r") as f:
                mapping = json.load(f)
                return mapping.get("db_id")
        except Exception as e:
            print(f"Error reading ID mapping file: {str(e)}")
    
    # If no local mapping, try to search all mapping files
    # This is a fallback mechanism
    all_report_dirs = glob.glob(os.path.join(settings.UPLOAD_DIR, "*"))
    for dir_path in all_report_dirs:
        mapping_path = os.path.join(dir_path, "id_mapping.json")
        if os.path.exists(mapping_path):
            try:
                with open(mapping_path, "r") as f:
                    mapping = json.load(f)
                    if mapping.get("uuid") == uuid_str:
                        return mapping.get("db_id")
            except Exception:
                pass
    
    # No mapping found
    return None

def ensure_id_is_int(id_value: Union[str, int]) -> int:
    """
    Ensure the ID is an integer, converting from UUID if necessary.
    
    Args:
        id_value: Either a UUID string or an integer ID
        
    Returns:
        The integer ID (or raises an exception if conversion fails)
        
    Raises:
        ValueError: If the ID cannot be converted to an integer
    """
    # If it's already an integer, return it
    if isinstance(id_value, int):
        return id_value
    
    # If it's a string that looks like an integer, convert it
    if isinstance(id_value, str) and id_value.isdigit():
        return int(id_value)
    
    # If it's a UUID string, look up the mapping
    if isinstance(id_value, str) and "-" in id_value:
        db_id = get_db_id_for_uuid(id_value)
        if db_id is not None:
            return db_id
    
    # If we can't determine an integer ID, raise an error
    raise ValueError(f"Could not convert ID {id_value} to integer") 