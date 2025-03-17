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
        
        # Special case for report IDs that are UUIDs themselves
        # Check if this is a directory in the uploads folder
        report_dir = os.path.join(settings.UPLOAD_DIR, id_value)
        if os.path.exists(report_dir) and os.path.isdir(report_dir):
            # For reports that use UUID directly, don't convert to integer
            # Instead, create a mapping if it doesn't exist
            mapping_path = os.path.join(report_dir, "id_mapping.json")
            
            # Try to create a simple mapping with the UUID itself
            try:
                # Check if Supabase is configured
                if settings.SUPABASE_URL and settings.SUPABASE_KEY:
                    # Try to get or create a record in the database
                    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                    
                    # Check if a report with this UUID already exists
                    response = supabase.table("reports").select("id").eq("uuid", id_value).execute()
                    
                    if response.data and len(response.data) > 0:
                        # Report exists, use its ID
                        db_id = response.data[0]["id"]
                    else:
                        # For now, just use a hash of the UUID as an integer ID
                        import hashlib
                        hash_int = int(hashlib.md5(id_value.encode()).hexdigest(), 16) % 10000000
                        
                        # Store the mapping for future use
                        with open(mapping_path, "w") as f:
                            json.dump({"uuid": id_value, "db_id": hash_int}, f)
                        
                        return hash_int
                else:
                    # If no Supabase configured, use hash method
                    import hashlib
                    hash_int = int(hashlib.md5(id_value.encode()).hexdigest(), 16) % 10000000
                    return hash_int
                    
            except Exception as e:
                print(f"Error creating ID mapping: {str(e)}")
                # If all else fails, just use a hash of the UUID as an integer ID
                import hashlib
                hash_int = int(hashlib.md5(id_value.encode()).hexdigest(), 16) % 10000000
                return hash_int
    
    # If we can't determine an integer ID, raise an error
    raise ValueError(f"Could not convert ID {id_value} to integer") 