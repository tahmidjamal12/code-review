import base64
import os
import re
from typing import List
import fitz
from PIL import Image
import io
from procopt.server.prompt_models import TranscriptionOutputModel

def encode_image(path_to_image: str):
    with open(path_to_image, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def remove_markdown(text: str):
    # Remove Markdown links
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Remove Markdown bold and italics
    text = re.sub(r'(\*{1,2}|_{1,2})(.*?)\1', r'\2', text)
    # Remove Markdown headings
    text = re.sub(r'#{1,6}\s*', '', text)
    # Remove any remaining markdown characters like ` or ~
    text = re.sub(r'(`+|~+)', '', text)
    return text

def convert_pdf_to_png(path_to_pdf: str) -> str:
    """Convert first page of PDF to PNG and return the path to the PNG file"""
    # Open the PDF
    doc = fitz.open(path_to_pdf)
    # Get the first page
    page = doc[0]
    # Convert to PNG
    pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))  # 300 DPI
    
    # Create PNG path
    path_to_png = os.path.splitext(path_to_pdf)[0] + '.png'
    
    # Save as PNG
    pix.save(path_to_png)
    
    # Close the PDF
    doc.close()
    
    return path_to_png

def split_image_into_blocks(image_bytes: bytes, block_size: int = 500) -> List[Image.Image]:
    """Split image into blocks of specified size"""
    # Open image from bytes
    img = Image.open(io.BytesIO(image_bytes))
    
    # Convert to RGB if necessary
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    width, height = img.size
    blocks = []
    
    # Calculate number of blocks in each dimension
    num_blocks_w = (width + block_size - 1) // block_size
    num_blocks_h = (height + block_size - 1) // block_size
    
    for i in range(num_blocks_h):
        for j in range(num_blocks_w):
            # Calculate block coordinates
            left = j * block_size
            upper = i * block_size
            right = min(left + block_size, width)
            lower = min(upper + block_size, height)
            
            # Crop block and add to list
            block = img.crop((left, upper, right, lower))
            blocks.append(block)
    
    return blocks