"""
Image processing and OCR extraction module
Handles text extraction from image files using EasyOCR
"""

import os
from PIL import Image
import easyocr
from typing import Optional

# Initialize reader globally for performance (lazy loading)
_ocr_reader = None

def get_ocr_reader():
    """Get or initialize the OCR reader (lazy loading for performance)"""
    global _ocr_reader
    if _ocr_reader is None:
        print("[INFO] Initializing OCR reader (first use)...")
        _ocr_reader = easyocr.Reader(['en'], gpu=False)
    return _ocr_reader

def is_image_file(filepath: str) -> bool:
    """Check if file is a supported image format"""
    supported_formats = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.tiff', '.tif'}
    _, ext = os.path.splitext(filepath)
    return ext.lower() in supported_formats

def extract_text_from_image(filepath: str) -> Optional[str]:
    """
    Extract text from an image file using OCR (EasyOCR)
    
    Args:
        filepath: Path to the image file
        
    Returns:
        Extracted text or None if extraction fails
    """
    try:
        # Verify image can be opened
        with Image.open(filepath) as img:
            # Check if image is valid
            img.verify()
        
        # Extract text using OCR
        reader = get_ocr_reader()
        result = reader.readtext(filepath)
        
        # Combine all text results
        extracted_text = "\n".join([text[1] for text in result])
        
        if extracted_text.strip():
            print(f"[OK] Extracted text from image: {os.path.basename(filepath)}")
            return extracted_text
        else:
            print(f"[WARN] No text found in image: {os.path.basename(filepath)}")
            return "[Image contains no readable text]"
            
    except Exception as e:
        print(f"[ERROR] Failed to extract text from image {os.path.basename(filepath)}: {e}")
        return None

def extract_text_with_fallback(filepath: str) -> Optional[str]:
    """
    Extract text from image with enhanced error handling
    
    Args:
        filepath: Path to the image file
        
    Returns:
        Extracted text or placeholder message if extraction fails
    """
    text = extract_text_from_image(filepath)
    if text is None:
        return "[Image could not be processed for text extraction]"
    return text

