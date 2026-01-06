"""
版面解析接口路由模块
"""

from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
import os
import uuid
import shutil
import logging

from app.services.layout_parsing_service import call_layout_parsing_api, extract_full_markdown

router = APIRouter()
logger = logging.getLogger(__name__)

UPLOADS_DIR = "uploads"
STATIC_DIR = "static"



class LayoutParsingRequest(BaseModel):
    """版面解析请求模型"""
    file: str = Field(
        ..., 
        description="服务器可访问的图像文件或PDF文件的URL，或文件内容的Base64编码结果。默认对于超过10页的PDF文件，只有前10页会被处理。"
    )
    api_url: Optional[str] = Field(
        default=None,
        description="版面解析 API 服务地址（可选，默认从环境变量 LAYOUT_PARSING_API_URL 读取）"
    )
    file_type: Optional[int] = Field(
        default=None,
        description="文件类型。0 表示 PDF 文件，1 表示图像文件。若不提供则根据 URL 自动推断文件类型。"
    )
    visualize: bool = Field(
        default=False,
        description="是否返回可视化结果图"
    )
    prettify_markdown: bool = Field(
        default=True,
        description="是否美化 Markdown 输出"
    )
    use_layout_detection: Optional[bool] = Field(
        default=None,
        description="是否使用版面检测"
    )
    use_chart_recognition: Optional[bool] = Field(
        default=None,
        description="是否使用图表识别"
    )
    merge_layout_blocks: Optional[bool] = Field(
        default=None,
        description="是否合并版面块"
    )


class MarkdownResult(BaseModel):
    """单页 Markdown 结果"""
    text: str = Field(..., description="Markdown 文本")
    is_start: bool = Field(default=True, description="当前页第一个元素是否为段开始")
    is_end: bool = Field(default=True, description="当前页最后一个元素是否为段结束")


class LayoutParsingResponse(BaseModel):
    """版面解析响应模型"""
    log_id: str = Field(..., description="请求 UUID")
    markdown_results: list[MarkdownResult] = Field(default=[], description="每页的 Markdown 结果")
    data_info: dict = Field(default={}, description="输入数据信息")
    full_markdown: Optional[str] = Field(default=None, description="完整的 Markdown 文本")


@router.post("/layout-parsing/", response_model=LayoutParsingResponse)
async def layout_parsing_endpoint(request: LayoutParsingRequest):
    """
    版面解析接口（JSON 请求方式）
    
    接收图像/PDF 的 URL 或 Base64 编码内容，返回版面解析结果（Markdown 格式）。
    """
    try:
        result = call_layout_parsing_api(
            file=request.file,
            api_url=request.api_url,
            file_type=request.file_type,
            visualize=request.visualize,
            prettify_markdown=request.prettify_markdown,
            use_layout_detection=request.use_layout_detection,
            use_chart_recognition=request.use_chart_recognition,
            merge_layout_blocks=request.merge_layout_blocks,
        )
        
        # 提取完整 Markdown
        full_markdown = extract_full_markdown(result["markdown_results"])
        
        return LayoutParsingResponse(
            log_id=result["log_id"],
            markdown_results=result["markdown_results"],
            data_info=result["data_info"],
            full_markdown=full_markdown,
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Layout Parsing processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"版面解析处理失败: {str(e)}")


@router.post("/layout-parsing/upload/")
async def layout_parsing_upload_endpoint(
    request: Request,
    file: UploadFile = File(...),
    api_url: Optional[str] = Form(default=None),
    visualize: bool = Form(default=False),
    prettify_markdown: bool = Form(default=True),
    use_layout_detection: Optional[bool] = Form(default=None),
    use_chart_recognition: Optional[bool] = Form(default=None),
    merge_layout_blocks: Optional[bool] = Form(default=None),
    keep_file: bool = Form(default=False),
):
    """
    版面解析接口（文件上传方式）
    
    上传图像或 PDF 文件，保存到服务器后通过 URL 调用版面解析 API。
    
    注意：服务需要部署在远程 API 可访问的服务器上（如 http://10.120.78.61:8000）。
    
    Args:
        file: 上传的图像或 PDF 文件
        api_url: 版面解析 API 服务地址（可选）
        visualize: 是否返回可视化结果图
        prettify_markdown: 是否美化 Markdown 输出
        use_layout_detection: 是否使用版面检测
        use_chart_recognition: 是否使用图表识别
        merge_layout_blocks: 是否合并版面块
        keep_file: 是否保留上传的文件（默认处理完后删除）
    """
    # 验证文件类型
    allowed_types = [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/bmp",
        "image/tiff",
    ]
    
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的文件类型: {file.content_type}。支持的类型: {', '.join(allowed_types)}"
        )

    # 根据文件类型设置 file_type
    file_type = 0 if file.content_type == "application/pdf" else 1
    
    # 创建唯一文件名
    unique_id = uuid.uuid4()
    original_filename = os.path.splitext(file.filename)[0]
    file_ext = os.path.splitext(file.filename)[1]
    saved_filename = f"{original_filename}_{unique_id}{file_ext}"
    saved_path = os.path.join(STATIC_DIR, saved_filename)
    
    try:
        # 保存文件到 static 目录
        with open(saved_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"File saved to: {saved_path}")
        
        # 生成可访问的 URL（自动从请求获取 base_url）
        base_url = str(request.base_url)
        file_url = f"{base_url}{STATIC_DIR}/{saved_filename}"
        
        logger.info(f"File URL: {file_url}")
        
        # 调用版面解析 API
        result = call_layout_parsing_api(
            file=file_url,
            api_url=api_url,
            file_type=file_type,
            visualize=visualize,
            prettify_markdown=prettify_markdown,
            use_layout_detection=use_layout_detection,
            use_chart_recognition=use_chart_recognition,
            merge_layout_blocks=merge_layout_blocks,
        )
        
        # 提取完整 Markdown
        full_markdown = extract_full_markdown(result["markdown_results"])
        
        response_content = {
            "message": "版面解析成功",
            "log_id": result["log_id"],
            "markdown_results": result["markdown_results"],
            "data_info": result["data_info"],
            "full_markdown": full_markdown,
        }
        
        # 如果保留文件，返回文件 URL
        if keep_file:
            response_content["file_url"] = file_url
        
        return JSONResponse(status_code=200, content=response_content)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Layout Parsing processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"版面解析处理失败: {str(e)}")
    
    finally:
        # 关闭文件
        file.file.close()
        # 如果不保留文件，则删除
        if not keep_file and os.path.exists(saved_path):
            os.remove(saved_path)
            logger.info(f"Cleaned up file: {saved_path}")


@router.post("/layout-parsing/markdown-only/")
async def layout_parsing_markdown_only_endpoint(request: LayoutParsingRequest):
    """
    版面解析接口 - 仅返回 Markdown
    
    简化版接口，只返回提取的 Markdown 文本内容。
    """
    try:
        result = call_layout_parsing_api(
            file=request.file,
            api_url=request.api_url,
            file_type=request.file_type,
            visualize=request.visualize,
            prettify_markdown=request.prettify_markdown,
            use_layout_detection=request.use_layout_detection,
            use_chart_recognition=request.use_chart_recognition,
            merge_layout_blocks=request.merge_layout_blocks,
        )
        
        # 提取完整 Markdown
        full_markdown = extract_full_markdown(result["markdown_results"])
        
        # 按页提取 Markdown
        page_markdowns = []
        for i, md in enumerate(result["markdown_results"]):
            page_markdowns.append({
                "page_index": i,
                "markdown": md.get("text", ""),
            })
        
        return JSONResponse(
            status_code=200,
            content={
                "log_id": result["log_id"],
                "full_markdown": full_markdown,
                "page_markdowns": page_markdowns,
                "total_pages": len(page_markdowns),
            }
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Layout Parsing processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"版面解析处理失败: {str(e)}")

