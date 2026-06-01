import os
import zipfile
import tempfile
import magic
from pathlib import Path
from fastapi import HTTPException

def validate_zip_file(file_path: Path, max_size_mb: int = 100) -> bool:
    """
    Performs security check on the uploaded file:
    - Real file size check
    - Real MIME magic bytes verification (checking ZIP signature PK\x03\x04)
    - Zip extraction safety checks (prevent Zip Slip vulnerability)
    """
    # 1. Size checking
    size_bytes = file_path.stat().st_size
    if size_bytes > max_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413, 
            detail=f"File exceeds absolute capacity restriction of {max_size_mb}MB"
        )
    
    # 2. Magic byte check (Real MIME verification)
    mime = magic.from_file(str(file_path), mime=True)
    if mime not in ["application/zip", "application/x-zip-compressed"]:
        # double-check binary signature just in case of odd system MIME databases
        with open(file_path, "rb") as f:
            sig = f.read(4)
            if sig != b"PK\x03\x04":
                raise HTTPException(
                    status_code=400, 
                    detail="Invalid archive. File is not a valid ZIP file."
                )
    return True

def safe_extract_zip(zip_path: Path, extract_dir: Path) -> Path:
    """
    Safely extract zip files preventing Directory Traversal attacks (Zip Slip).
    Ensure extracted paths resolve strictly within the target directory.
    """
    with zipfile.ZipFile(zip_path) as z:
        for member in z.infolist():
            # Resolve target path and check if it starts with the destination path prefix
            target_path = Path(os.path.abspath(extract_dir / member.filename))
            resolved_dest = Path(os.path.abspath(extract_dir))
            
            if not str(target_path).startswith(str(resolved_dest)):
                raise HTTPException(
                    status_code=400, 
                    detail="Illegal path detected inside ZIP archive (Directory Traversal attempt)."
                )
            
        # Secure extraction
        z.extractall(extract_dir)
        
    return extract_dir
