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


def stitch_images_vertically(image_paths: list[str], output_folder: str, base_filename: str) -> str:
    """
    将多个图片按照最大宽度为基准进行上下拼接，保留原分辨率。
    
    Args:
        image_paths: 图片文件路径列表
        output_folder: 输出文件夹
        base_filename: 基础文件名
        
    Returns:
        拼接后的图片路径
    """
    try:
        if not image_paths:
            raise ValueError("No images to stitch")
            
        # 打开所有图片并获取尺寸信息
        images = []
        max_width = 0
        total_height = 0
        
        logger.info(f"Opening {len(image_paths)} images for stitching...")
        
        for image_path in image_paths:
            img = Image.open(image_path)
            images.append(img)
            
            width, height = img.size
            max_width = max(max_width, width)
            total_height += height
            
            logger.info(f"Image {os.path.basename(image_path)}: {width}x{height}")
        
        logger.info(f"Max width: {max_width}, Total height: {total_height}")
        
        # 创建新的画布
        stitched_image = Image.new('RGB', (max_width, total_height), color='white')
        
        # 依次粘贴图片
        current_y = 0
        for i, img in enumerate(images):
            width, height = img.size
            
            # 如果图片宽度小于最大宽度，居中放置
            x_offset = (max_width - width) // 2
            
            stitched_image.paste(img, (x_offset, current_y))
            logger.info(f"Pasted image {i+1} at position ({x_offset}, {current_y})")
            
            current_y += height
        
        # 保存拼接后的图片
        output_filename = f"{base_filename}_stitched.png"
        output_path = os.path.join(output_folder, output_filename)
        stitched_image.save(output_path, "PNG")
        
        logger.info(f"Stitched image saved to {output_path}")
        
        # 关闭所有打开的图片
        for img in images:
            img.close()
            
        return output_path
        
    except Exception as e:
        logger.error(f"Error during image stitching: {e}")
        # 清理已打开的图片
        for img in images:
            if img:
                img.close()
        raise


def convert_pdf_to_stitched_image(pdf_path: str, dpi: int, output_folder: str) -> str:
    """
    将PDF转换为图片，应用旋转规则，然后拼接成一张长图。
    
    Args:
        pdf_path: PDF文件路径
        dpi: 图片分辨率
        output_folder: 输出文件夹
        
    Returns:
        拼接后图片的路径
    """
    try:
        # 首先转换为单独的图片
        image_paths = convert_pdf_to_images(pdf_path, dpi, output_folder)
        
        if not image_paths:
            raise ValueError("Failed to convert PDF to images")
        
        # 获取基础文件名
        base_filename = os.path.splitext(os.path.basename(pdf_path))[0]
        
        # 拼接图片
        stitched_image_path = stitch_images_vertically(image_paths, output_folder, base_filename)
        
        # 清理临时的单独图片文件
        logger.info("Cleaning up individual image files...")
        for image_path in image_paths:
            if os.path.exists(image_path):
                os.remove(image_path)
                logger.info(f"Removed temporary file: {image_path}")
        
        return stitched_image_path
        
    except Exception as e:
        logger.error(f"Error during PDF to stitched image conversion: {e}")
        raise 