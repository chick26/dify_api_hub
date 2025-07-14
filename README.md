# AI Agent Support Service

This project provides a FastAPI-based service with various utilities for AI agents. The first feature implemented is a PDF processing service that can convert PDF files to images and automatically correct their orientation using OCR.

## Features

- **PDF to Image Conversion**: Convert each page of a PDF into a high-quality PNG image.
- **OCR-based Orientation Correction**: Automatically detects and corrects the orientation of text in the generated images.
- **Dynamic DPI**: Specify the resolution (DPI) for the output images.
- **Dockerized**: Easy to set up and run using Docker and Docker Compose.

## Project Structure

```
AIAgentSupportService/
├── app/
│   ├── routers/
│   │   ├── __init__.py
│   │   └── pdf.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── pdf_converter.py
│   ├── __init__.py
│   └── main.py
├── static/         # Generated images are stored here
├── uploads/        # Uploaded PDFs are temporarily stored here
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

## How to Run the Service

1.  **Clone the repository or have the project files ready.**

2.  **Navigate to the project directory:**
    ```sh
    cd AIAgentSupportService
    ```

3.  **Build and start the services using Docker Compose:**
    ```sh
    docker-compose up --build
    ```
    This command will build the Docker image (installing Tesseract, Python dependencies, etc.) and start the FastAPI service. The service will be available at `http://localhost:8000`.

## API Usage

### Process a PDF

- **Endpoint**: `POST /api/v1/process-pdf/`
- **Description**: Upload a PDF file to convert it into images.
- **Request**: `multipart/form-data`
  - `file`: The PDF file to upload.
  - `dpi`: (Optional) An integer for the desired resolution (dots per inch). Defaults to `300`.

- **Example using `curl`:**
  ```sh
  curl -X POST "http://localhost:8000/api/v1/process-pdf/" \
       -F "file=@/path/to/your/document.pdf" \
       -F "dpi=300"
  ```

- **Successful Response (`200 OK`):**
  ```json
  {
    "message": "PDF processed successfully",
    "image_urls": [
      "http://localhost:8000/static/document_page_1.png",
      "http://localhost:8000/static/document_page_2.png"
    ]
  }
  ```

- **Error Response (`400 Bad Request`):**
  ```json
  {
    "detail": "Invalid file type. Please upload a PDF."
  }
  ```
- **Error Response (`500 Internal Server Error`):**
  ```json
  {
    "detail": "Failed to convert PDF to images."
  }
  ```

## How to Stop the Service

To stop the running services, press `Ctrl + C` in the terminal where `docker-compose` is running, and then run:
```sh
docker-compose down
```
This will stop and remove the containers defined in the `docker-compose.yml` file. 