# AI Agent Support Service

为 AI Agent 提供各种实用工具的 FastAPI 服务。目前支持 PDF 处理和版面解析功能。

## 功能特性

### PDF 处理
- **PDF 转图像**：将 PDF 每页转换为高质量 PNG 图像
- **OCR 方向校正**：自动检测并校正图像中文字的方向
- **自定义 DPI**：支持指定输出图像的分辨率
- **图像拼接**：支持将多页 PDF 拼接为长图

### 版面解析
- **多格式支持**：支持图像（JPEG、PNG、GIF、WebP、BMP、TIFF）和 PDF 文件
- **Markdown 输出**：将文档内容解析为结构化的 Markdown 格式
- **表格识别**：支持复杂表格的识别和转换
- **多种输入方式**：支持 URL、Base64 编码和文件上传
- **自动 Base64 转换**：URL 输入会自动下载并转换为 Base64，避免网络访问问题

## 项目结构

```
AIAgentSupportService/
├── app/
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── pdf.py              # PDF 处理路由
│   │   └── layout_parsing.py   # 版面解析路由
│   ├── services/
│   │   ├── __init__.py
│   │   ├── pdf_converter.py    # PDF 转换服务
│   │   └── layout_parsing_service.py  # 版面解析服务
│   ├── __init__.py
│   └── main.py
├── static/              # 生成的图像存储目录
├── uploads/             # 上传的文件临时存储目录
├── docker-compose.yml
├── docker-compose.yml.example
├── Dockerfile
├── openapi.yaml         # OpenAPI 规范文档
├── requirements.txt
└── README.md
```

## 环境要求

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

## 快速开始

### 1. 克隆项目

```sh
cd AIAgentSupportService
```

### 2. 配置环境变量

复制示例配置文件并修改：

```sh
cp docker-compose.yml.example docker-compose.yml
```

编辑 `docker-compose.yml`，配置版面解析 API 地址：

```yaml
environment:
  - LAYOUT_PARSING_API_URL=http://your-api-server:port/v2/models/layout-parsing/infer
```

### 3. 启动服务

```sh
docker-compose up --build
```

服务将在 `http://localhost:8000` 启动。

### 4. 查看 API 文档

访问 `http://localhost:8000/docs` 查看 Swagger UI 文档。

## API 使用指南

### PDF 处理

#### 处理 PDF 并返回图片 URL

```sh
curl -X POST "http://localhost:8000/api/v1/process-pdf/" \
     -F "file=@/path/to/document.pdf" \
     -F "dpi=300"
```

响应示例：
```json
{
  "message": "PDF processed successfully",
  "image_urls": [
    "http://localhost:8000/static/document_page_1.png",
    "http://localhost:8000/static/document_page_2.png"
  ]
}
```

#### 处理 PDF 并返回拼接长图

```sh
curl -X POST "http://localhost:8000/api/v1/process-pdf-stitched/" \
     -F "file=@/path/to/document.pdf" \
     -F "dpi=300"
```

### 版面解析

#### 方式一：JSON 请求（推荐）

通过 URL 或 Base64 编码调用：

```sh
curl -X POST "http://localhost:8000/api/v1/layout-parsing/" \
     -H "Content-Type: application/json" \
     -d '{
       "file": "http://example.com/document.png",
       "prettify_markdown": true
     }'
```

响应示例：
```json
{
  "log_id": "550e8400-e29b-41d4-a716-446655440000",
  "markdown_results": [
    {
      "text": "# 文档标题\n\n这是文档内容...",
      "is_start": true,
      "is_end": true
    }
  ],
  "data_info": {
    "width": 2481,
    "height": 3508,
    "type": "image"
  },
  "full_markdown": "# 文档标题\n\n这是文档内容..."
}
```

#### 方式二：文件上传

直接上传文件进行解析：

```sh
curl -X POST "http://localhost:8000/api/v1/layout-parsing/upload/" \
     -F "file=@/path/to/document.png"
```

#### 方式三：仅返回 Markdown

简化版接口，只返回 Markdown 文本：

```sh
curl -X POST "http://localhost:8000/api/v1/layout-parsing/markdown-only/" \
     -H "Content-Type: application/json" \
     -d '{"file": "http://example.com/document.png"}'
```

响应示例：
```json
{
  "log_id": "550e8400-e29b-41d4-a716-446655440000",
  "full_markdown": "# 文档标题\n\n这是文档内容...",
  "page_markdowns": [
    {
      "page_index": 0,
      "markdown": "# 文档标题\n\n这是文档内容..."
    }
  ],
  "total_pages": 1
}
```

### 版面解析参数说明

| 参数 | 类型 | 说明 |
|------|------|------|
| `file` | string | 图像/PDF 的 URL 或 Base64 编码内容（必填） |
| `api_url` | string | 版面解析 API 地址（可选，默认从环境变量读取） |
| `file_type` | integer | 文件类型：0=PDF，1=图像（可选，自动推断） |
| `visualize` | boolean | 是否返回可视化结果（默认 false） |
| `prettify_markdown` | boolean | 是否美化 Markdown 输出（默认 true） |
| `use_layout_detection` | boolean | 是否使用版面检测 |
| `use_chart_recognition` | boolean | 是否使用图表识别 |
| `merge_layout_blocks` | boolean | 是否合并版面块 |

## 停止服务

```sh
docker-compose down
```

## 本地开发

不使用 Docker 运行：

```sh
# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export LAYOUT_PARSING_API_URL="http://your-api-server:port/v2/models/layout-parsing/infer"

# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 注意事项

1. **版面解析 API 配置**：需要配置 `LAYOUT_PARSING_API_URL` 环境变量指向远程版面解析服务
2. **文件大小限制**：PDF 文件默认只处理前 10 页
3. **支持的图像格式**：JPEG、PNG、GIF、WebP、BMP、TIFF
4. **自动 Base64 转换**：传入 URL 时，服务会自动下载并转换为 Base64，避免远程 API 网络访问问题
