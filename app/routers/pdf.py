from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
import os
import uuid
import shutil
from app.services.pdf_converter import convert_pdf_to_images

router = APIRouter()

UPLOADS_DIR = "uploads"
STATIC_DIR = "static"

@router.post("/process-pdf/")
async def process_pdf_endpoint(
    request: Request,
    file: UploadFile = File(...),
    dpi: int = Form(300)
):
    """
    Accepts a PDF file and a DPI value.
    Converts the PDF to images, corrects their orientation, and returns their URLs.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF.")

    # Create a unique filename to avoid conflicts
    unique_id = uuid.uuid4()
    original_filename = os.path.splitext(file.filename)[0]
    pdf_filename = f"{original_filename}_{unique_id}.pdf"
    pdf_path = os.path.join(UPLOADS_DIR, pdf_filename)
    
    # Save the uploaded file
    try:
        with open(pdf_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    # Perform the conversion
    image_paths = convert_pdf_to_images(pdf_path, dpi, STATIC_DIR)

    # Clean up the uploaded PDF file
    if os.path.exists(pdf_path):
        os.remove(pdf_path)

    if not image_paths:
        raise HTTPException(status_code=500, detail="Failed to convert PDF to images.")

    # Generate public URLs for the images
    base_url = str(request.base_url)
    image_urls = [f"{base_url}{STATIC_DIR}/{os.path.basename(p)}" for p in image_paths]
    
    return JSONResponse(
        status_code=200,
        content={
            "message": "PDF processed successfully",
            "image_urls": image_urls
        }
    )

@router.post("/process-pdf-files/")
async def process_pdf_files_endpoint(
    request: Request,
    file: UploadFile = File(...),
    dpi: int = Form(300)
):
    """
    Accepts a PDF file and a DPI value.
    Converts the PDF to images, corrects their orientation, and returns the image files directly.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF.")

    # Create a unique filename to avoid conflicts
    unique_id = uuid.uuid4()
    original_filename = os.path.splitext(file.filename)[0]
    pdf_filename = f"{original_filename}_{unique_id}.pdf"
    pdf_path = os.path.join(UPLOADS_DIR, pdf_filename)
    
    # Save the uploaded file
    try:
        with open(pdf_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    # Perform the conversion
    image_paths = convert_pdf_to_images(pdf_path, dpi, STATIC_DIR)

    # Clean up the uploaded PDF file
    if os.path.exists(pdf_path):
        os.remove(pdf_path)

    if not image_paths:
        raise HTTPException(status_code=500, detail="Failed to convert PDF to images.")

    # Save image paths and return them as URLs for individual download
    image_filenames = []
    for image_path in image_paths:
        filename = os.path.basename(image_path)
        image_filenames.append(filename)
    
    # Generate individual file URLs
    base_url = str(request.base_url)
    file_urls = [f"{base_url}api/v1/get-image/{filename}" for filename in image_filenames]
    
    return JSONResponse(
        status_code=200,
        content={
            "message": "PDF processed successfully",
            "file_urls": file_urls,
            "total_files": len(image_filenames)
        }
    )

@router.get("/get-image/{filename}")
async def get_image_file(filename: str):
    """
    Download a specific image file by filename.
    """
    file_path = os.path.join(STATIC_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image file not found")
    
    return FileResponse(
        path=file_path,
        media_type="image/png",
        filename=filename
    ) 