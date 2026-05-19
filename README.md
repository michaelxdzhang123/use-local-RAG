# use-local-RAG

本项目提供一个本地脚本 `pretty_streamMCP.py`，用于调用 RAGFlow MCP 检索并将原始返回整理为可读 Markdown（检索摘要、Top chunks、证据片段、调试信息）。

## 项目结构

- `pretty_streamMCP.py`：主脚本，连接 MCP 并格式化输出。
- `mcp_info.json`：`CONTENT -> RAGFLOW_DATASET_IDS` 映射配置。
- `test_pretty_streamMCP.py`：针对 dataset 映射逻辑的单元测试。
- `pyproject.toml`：项目依赖与 pytest 配置。

## 快速开始

### 1) 安装依赖（推荐 uv）

```bash
uv pip install -e .
uv pip install -e .[dev]
```

或直接运行时自动创建环境：

```bash
uv run pytest
```

### 2) 配置环境变量

建议把变量写入 `.env.local`，再复制到 `.env`：

```bash
cp .env.local .env
```

关键变量示例：

```bash
RAGFLOW_MCP_URL="http://172.28.21.22:9382/mcp/"
RAGFLOW_TOOL_NAME="ragflow_retrieval"
RAGFLOW_DATASET_IDS="<dataset-id-1>,<dataset-id-2>"
# 或通过 content 映射（见下面 --content）
RAGFLOW_CONTENT="HWind"
RAGFLOW_MCP_INFO="mcp_info.json"
```

### 3) 运行脚本

直接指定问题：

```bash
python pretty_streamMCP.py "请介绍 HWind 的 generalized coordinates"
```

按 `CONTENT` 自动选择数据集（推荐）：

```bash
python pretty_streamMCP.py --content HWind "请检索 modal coordinates multi-body generalized coordinates"
```

## ChatGPT 网页版接入步骤（HWind Docs）

1. **启动 RAGFlow 主服务**（确认 `http://172.28.21.22:9380` 可访问）。
2. **启动 RAGFlow MCP Server**（确认 `http://172.28.21.22:9382/mcp` 无 connection refused）。
3. **启动 Cloudflare Tunnel**：
   ```bash
   cloudflared tunnel --url http://172.28.21.22:9382
   ```
4. 在 ChatGPT 网页版开启 **Developer Mode**：
   `Settings -> Apps / Apps & Connectors -> Advanced settings -> Developer mode`。
5. 创建 connector：
   - Name: `HWind Docs`
   - URL: `https://<your-tunnel-domain>/mcp`
   - Authentication: `No Authentication`（仅限测试）
6. 新对话中选择 `HWind Docs` 并提问：
   - “请使用 HWind Docs 检索 HWind 文档，说明 combined modal and multi-body dynamics formulation 如何组织 generalized coordinates。”

## 测试

```bash
uv run pytest
python -m py_compile pretty_streamMCP.py test_pretty_streamMCP.py
python -m json.tool mcp_info.json
```

## 注意事项

- 不要将 API key、Cloudflare token、私有凭证提交到仓库。
- 生产环境应使用固定域名 + 访问控制，不建议长期 `No Authentication`。
- 回答 HWind 问题时应优先使用 HWind 数据集，避免误用“扩展材料”等非 HWind 数据源。
