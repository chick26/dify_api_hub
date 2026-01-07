"""
版面解析服务模块（Triton 风格）

调用远程版面解析 API，返回 Markdown 结果。
"""

import json
import os
import re
import base64
import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 从环境变量读取 Layout Parsing API URL
LAYOUT_PARSING_API_URL = os.getenv("LAYOUT_PARSING_API_URL", "")


def is_url(s: str) -> bool:
    """判断字符串是否为 URL"""
    return bool(re.match(r'^https?://', s, re.IGNORECASE))


def extract_local_static_path(url: str) -> Optional[str]:
    """
    检测 URL 是否指向本地 static 目录，如果是则返回本地文件路径。
    
    Args:
        url: 文件的 URL 地址
        
    Returns:
        如果是本地 static 文件，返回本地路径；否则返回 None
    """
    # 匹配 /static/ 路径
    match = re.search(r'/static/(.+)$', url)
    if match:
        filename = match.group(1)
        local_path = os.path.join("static", filename)
        if os.path.exists(local_path):
            logger.info(f"Detected local static file: {local_path}")
            return local_path
    return None


def url_to_base64(url: str) -> str:
    """
    下载 URL 对应的文件内容并转换为 Base64 编码。
    如果 URL 指向本地 static 目录，则直接从文件系统读取。
    
    Args:
        url: 文件的 URL 地址
        
    Returns:
        文件内容的 Base64 编码字符串
        
    Raises:
        ValueError: 下载失败时抛出
    """
    # 检测是否是本地 static 文件
    local_path = extract_local_static_path(url)
    if local_path:
        try:
            logger.info(f"Reading local file: {local_path}")
            with open(local_path, "rb") as f:
                file_content = f.read()
            file_base64 = base64.b64encode(file_content).decode("utf-8")
            logger.info(f"Read local file and encoded to Base64, length: {len(file_base64)}")
            return file_base64
        except IOError as e:
            logger.error(f"Failed to read local file: {local_path}, error: {e}")
            raise ValueError(f"无法读取本地文件: {e}")
    
    # 远程 URL，通过 HTTP 下载
    try:
        logger.info(f"Downloading file from URL: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        file_content = response.content
        file_base64 = base64.b64encode(file_content).decode("utf-8")
        logger.info(f"Downloaded and encoded to Base64, length: {len(file_base64)}")
        return file_base64
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download file from URL: {url}, error: {e}")
        raise ValueError(f"无法从 URL 下载文件: {e}")


def call_layout_parsing_api(
    file: str,
    api_url: Optional[str] = None,
    file_type: Optional[int] = None,
    visualize: bool = False,
    prettify_markdown: bool = True,
    use_layout_detection: Optional[bool] = None,
    use_chart_recognition: Optional[bool] = None,
    merge_layout_blocks: Optional[bool] = None,
) -> dict:
    """
    调用版面解析 API，返回 Markdown 解析结果。

    Args:
        file: 服务器可访问的图像文件或PDF文件的URL，或文件内容的Base64编码结果。
              默认对于超过10页的PDF文件，只有前10页会被处理。
        api_url: API 服务地址
        file_type: 文件类型。0 表示 PDF 文件，1 表示图像文件。若不提供则根据 URL 自动推断。
        visualize: 是否返回可视化结果图
        prettify_markdown: 是否美化 Markdown 输出
        use_layout_detection: 是否使用版面检测
        use_chart_recognition: 是否使用图表识别
        merge_layout_blocks: 是否合并版面块

    Returns:
        包含解析结果的字典，结构如下：
        {
            "log_id": str,              # 请求 UUID
            "markdown_results": [       # 每页的 Markdown 结果
                {
                    "text": str,        # Markdown 文本
                    "is_start": bool,   # 当前页第一个元素是否为段开始
                    "is_end": bool,     # 当前页最后一个元素是否为段结束
                }
            ],
            "data_info": dict,          # 输入数据信息
        }

    Raises:
        requests.HTTPError: 请求失败时抛出
        ValueError: API 返回错误时抛出
    """
    # 确定 API URL
    actual_api_url = api_url or LAYOUT_PARSING_API_URL
    if not actual_api_url:
        raise ValueError("Layout Parsing API URL 未配置，请设置环境变量 LAYOUT_PARSING_API_URL 或传入 api_url 参数")

    # 如果 file 是 URL，则下载并转换为 Base64
    if is_url(file):
        logger.info("Detected URL input, converting to Base64...")
        file_base64 = url_to_base64(file)
        # 如果未指定 file_type，根据 URL 推断
        if file_type is None:
            if file.lower().endswith(".pdf"):
                file_type = 0
                logger.info("Inferred file_type=0 (PDF) from URL")
            else:
                file_type = 1
                logger.info("Inferred file_type=1 (Image) from URL")
    else:
        # 已经是 Base64 编码
        file_base64 = file
        logger.info("Input is already Base64 encoded")

    # 构建内部请求数据
    inner_data = {
        "file": file_base64,
        "visualize": visualize,
        "prettifyMarkdown": prettify_markdown,
    }
    if file_type is not None:
        inner_data["fileType"] = file_type
    if use_layout_detection is not None:
        inner_data["useLayoutDetection"] = use_layout_detection
    if use_chart_recognition is not None:
        inner_data["useChartRecognition"] = use_chart_recognition
    if merge_layout_blocks is not None:
        inner_data["mergeLayoutBlocks"] = merge_layout_blocks

    # 构建 Triton 格式请求体
    payload = {
        "inputs": [
            {
                "name": "input",
                "shape": [1, 1],
                "datatype": "BYTES",
                "data": [json.dumps(inner_data)]
            }
        ],
        "outputs": [
            {"name": "output"}
        ]
    }

    logger.info(f"Calling Layout Parsing API: {actual_api_url}")
    logger.info(f"file_type: {file_type}, visualize: {visualize}, prettify_markdown: {prettify_markdown}")
    logger.info(f"Base64 file length: {len(file_base64)}")

    # 调用 API - 使用手动序列化的方式（更接近 curl 行为）
    headers = {
        "Content-Type": "application/json",
    }
    payload_json = json.dumps(payload, ensure_ascii=False)
    logger.info(f"Sending payload (length={len(payload_json)})")
    
    try:
        response = requests.post(actual_api_url, data=payload_json, headers=headers, timeout=120)
        logger.info(f"API Response status code: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"API Response error - status: {response.status_code}, body: {response.text[:500]}")
        
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        raise

    # 解析 Triton 格式响应
    try:
        resp_json = response.json()
        output_data = resp_json["outputs"][0]["data"][0]
        result = json.loads(output_data)
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        logger.error(f"Failed to parse API response: {e}, response: {response.text[:500]}")
        raise ValueError(f"API 响应解析失败: {e}")

    # 检查错误
    if result.get("errorCode", 0) != 0:
        error_msg = result.get("errorMsg", "Unknown error")
        error_code = result.get("errorCode")
        logger.error(f"Layout Parsing API Error - code: {error_code}, msg: {error_msg}")
        logger.error(f"Full error result: {json.dumps(result, ensure_ascii=False)[:500]}")
        raise ValueError(f"API Error [{error_code}]: {error_msg}")

    inner_result = result.get("result", {})

    # 提取 Markdown 结果（过滤掉 images 中的 base64 数据）
    markdown_results = []
    for res in inner_result.get("layoutParsingResults", []):
        markdown = res.get("markdown", {})
        markdown_results.append({
            "text": markdown.get("text", ""),
            "is_start": markdown.get("isStart", True),
            "is_end": markdown.get("isEnd", True),
        })

    logger.info(f"Layout Parsing completed, found {len(markdown_results)} pages")

    return {
        "log_id": result.get("logId", ""),
        "markdown_results": markdown_results,
        "data_info": inner_result.get("dataInfo", {}),
    }


def extract_full_markdown(markdown_results: list) -> str:
    """
    从版面解析结果中提取完整 Markdown 文本。

    Args:
        markdown_results: call_layout_parsing_api() 返回的 markdown_results 列表

    Returns:
        所有页面的 Markdown 内容，以换行符分隔
    """
    all_texts = []
    for page in markdown_results:
        text = page.get("text", "")
        if text:
            all_texts.append(text)
    return "\n\n".join(all_texts)

