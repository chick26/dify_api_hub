import fitz  # PyMuPDF
import pytesseract
from PIL import Image, ImageOps
import os
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def orient_image(image_path: str):
    """
    Detects orientation of an image and rotates it to be upright.
    Overwrites the original image file.
    """
    try:
        logger.info(f"Checking orientation for {image_path}...")
        osd = pytesseract.image_to_osd(image_path)
        angle_match = re.search(r'Rotate: (\d+)', osd)
        
        if angle_match:
            angle = int(angle_match.group(1))
            logger.info(f"Detected rotation angle: {angle} for {image_path}")
            if angle != 0:
                with Image.open(image_path) as img:
                    # The angle from Tesseract is counter-clockwise,
                    # Pillow's rotate is also counter-clockwise.
                    rotated_img = img.rotate(360 - angle, expand=True)
                    # Use ImageOps.exif_transpose to handle EXIF orientation tag
                    final_img = ImageOps.exif_transpose(rotated_img)
                    final_img.save(image_path)
                    logger.info(f"Rotated {image_path} by {360-angle} degrees.")
        else:
            logger.info(f"No rotation needed for {image_path}.")

    except Exception as e:
        logger.error(f"Could not process orientation for {image_path}: {e}")


def convert_pdf_to_images(pdf_path: str, dpi: int, output_folder: str) -> list[str]:
    """
    Converts each page of a PDF file to a PNG image, corrects its orientation,
    and saves it to the output folder.

    Returns a list of paths to the generated images.
    """
    image_paths = []
    try:
        pdf_document = fitz.open(pdf_path)
        base_filename = os.path.splitext(os.path.basename(pdf_path))[0]

        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            
            # Render page to a pixmap (a raster image)
            pix = page.get_pixmap(dpi=dpi)
            
            image_filename = f"{base_filename}_page_{page_num + 1}.png"
            image_path = os.path.join(output_folder, image_filename)
            
            # Save the pixmap as a PNG file
            pix.save(image_path)
            logger.info(f"Saved page {page_num + 1} to {image_path}")

            # Correct the orientation of the newly created image
            orient_image(image_path)
            
            image_paths.append(image_path)
            
    except Exception as e:
        logger.error(f"An error occurred during PDF to image conversion: {e}")
        # Clean up created images if conversion fails midway
        for path in image_paths:
            if os.path.exists(path):
                os.remove(path)
        return []
    finally:
        if 'pdf_document' in locals() and pdf_document:
            pdf_document.close()
            
    return image_paths 