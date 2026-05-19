# AGENTS.md — ChatGPT 5 + 本地 RAGFlow + HWind 文档助手

## 目标

本文件定义如何让 **ChatGPT 网页版** 通过 **MCP connector** 调用本地 **RAGFlow**，从而检索并回答 **HWind** 文档相关问题。

目标链路：

```text
ChatGPT 网页版
    ↓ HTTPS /mcp
Cloudflare Tunnel / HTTPS 反向代理
    ↓
本机 RAGFlow MCP Server
    ↓
本机 RAGFlow 主服务
    ↓
HWind 文档数据集
```

该方案对应ChatGPT 网页版中选择搜索内容并直接调用本地 RAGFlow MCP server 进行检索，和chatGPT 搜索内容一起展示。本方案式基于chatGPT网页版加上调用本地RAG MCP 服务器的方式实现。 

---

## 使用原则

### 对智能体的要求

当用户询问 HWind 文档、理论公式、输入文件、求解器结构、FAST/OpenFAST 对比、模态法、多体动力学、载荷映射、控制接口、验证算例等问题时：

1. 优先使用 HWind Docs MCP connector 检索 RAGFlow 文档。
2. 不得凭空编造 HWind 文档内容。
3. 如果检索片段不足以支持结论，明确说明
4. from mcp_info.json 选择CONTENT后得到相应的RAGFLOW_DATASET_IDS，然后使用该ID检索对应的RAGFlow文档。
5. 在chatGPT网页版中展示mcp_info.json中的CONTENT,选择后从MCP 获得数据并和网络搜索内容，并将这些内容与网络搜索结果进行对比，最终将对比结果展示在chatGPT网页版中。



   ```text
   当前检索片段不足以支持该结论。
   ```

4. 区分以下三类内容：

   ```text
   - HWind 文档明确说明的内容
   - 基于文档片段可以合理推断的内容
   - 参考 OpenFAST / Bladed / 通用气弹仿真知识给出的补充解释
   ```

5. 回答技术问题时，尽量保留文档中的术语，并使用中文做最后的输出，例如：

   ```text
   generalized coordinates
   modal coordinates
   multi-body dynamics
   nodal force
   generalized force
   blade modal DOF
   tower modal DOF
   drivetrain torsion
   aero-servo-elastic coupling
   ```

6. 若用户要求“只依据文档回答”，则不要加入未被检索片段支持的外部知识。

---

## 运行环境假设

默认假设如下：

```text

RAGFlow MCP Server 地址： http://172.28.21.22:9382/mcp
MCP transport：           Streamable HTTP /mcp
RAGFlow MCP 模式：        self-host
ChatGPT 访问方式：        HTTPS tunnel 或 HTTPS 反向代理
HWind 文档库：            已导入 RAGFlow dataset 并完成解析
```


---

## 关键安全规则

### 不要提交密钥

不要把以下内容写入 git 仓库：

```text
OPENAI_API_KEY
Cloudflare token
公司内网域名凭证
任何可访问 HWind 私有文档的认证信息
```

推荐使用环境变量、`.env.local`，所有需要export 的变量都放到这个文件，然后cp .env.local .env 

### 不要长期暴露无认证 endpoint

测试阶段可以使用：

```text
Cloudflare quick tunnel + No Authentication
```

但这只适合临时验证。只要 tunnel URL 泄露，外部用户就可能访问 RAGFlow MCP endpoint 并检索 HWind 文档。

长期使用建议：

```text
公司域名
+ HTTPS
+ Cloudflare Access / OAuth / IP allowlist
+ 只读 retrieve 工具
+ 最小权限 RAGFlow API key
```

### MCP server 仅暴露检索能力

用于 ChatGPT 的 MCP server 应只暴露只读检索工具，例如：

```text
ragflow_retrieval
retrieve
```

注意：不同 RAGFlow MCP 版本或封装方式中，工具名可能显示为 `retrieve` 或 `ragflow_retrieval`。实际以 `session.list_tools()` / ChatGPT connector 展示的工具名为准。

不要暴露删除、上传、修改 dataset、执行命令、写文件等高风险工具。

---

## 前置条件

### 1. RAGFlow 主服务已经运行

浏览器确认：

```text
http://172.28.21.22:9380
```

确认事项：

```text
- RAGFlow UI 可打开
- HWind 文档已经上传到 dataset
- 文档解析完成
- 在 RAGFlow UI 中能正常检索 HWind 内容
```

### 2. 这个版本不使用 RAGFlow API Key，具体见pretty_streamMCP.py


### 3. 准备 cloudflare 

Ubuntu / Debian：

```bash
sudo mkdir -p --mode=0755 /usr/share/keyrings

curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg \
  | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null

echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main" \
  | sudo tee /etc/apt/sources.list.d/cloudflared.list

sudo apt-get update
sudo apt-get install cloudflared
cloudflared --version
```

---

## 环境变量建议

在 shell 中设置请放到 .env.local 中：

RAGFLOW_BASE_URL="http://172.28.21.22:9380"
RAGFLOW_MCP_HOST="172.28.21.22"
RAGFLOW_MCP_PORT="9382"

--

# 方案 A 操作步骤：ChatGPT 网页版直接调用本地 RAGFlow

## Step 1 — 启动 RAGFlow 主服务

如果你用 Docker Compose 启动 RAGFlow：

```bash
cd /path/to/ragflow
docker compose -f docker/docker-compose.yml up -d
```

确认主服务可用：

```bash
curl -i http://172.28.21.22:9380
```

也可以直接在浏览器打开：

```text
http://172.28.21.22:9380
```

---

## Step 2 — 启动 RAGFlow MCP Server 这个已经启动了，略去


Windows PowerShell 一行版本：

```powershell
uv run mcp/server/server.py --host=172.28.21.22 --port=9382 --base-url=http://172.28.21.22:9380 --mode=self-host --api-key=$env:RAGFLOW_API_KEY
```

## Step 3 — 本地测试 MCP endpoint

测试端口是否打开：

```bash
curl -i http://172.28.21.22:9382/mcp

注意：

```text
/mcp 是 MCP endpoint，不一定返回普通网页。
关键是不要出现 Connection refused。
```

常见问题：

```text
Connection refused：MCP server 没启动，或端口不对。
404：路径错误、版本不支持、MCP 未启用，或访问了 / 而不是 /mcp。
401 / 403：认证配置不匹配。
```

---

## Step 4 — 通过 Cloudflare Tunnel 暴露 MCP server

在另一个终端运行：

```bash
cloudflared tunnel --url http://172.28.21.22:9382
```

成功后会输出一个 HTTPS 地址，例如：

```text
https://quiet-wind-hwind.trycloudflare.com
```

ChatGPT connector URL 应填写：

```text
https://quiet-wind-hwind.trycloudflare.com/mcp
```

注意：

```text
不要填 http://172.28.21.22:9382/mcp
不要填 https://quiet-wind-hwind.trycloudflare.com
不要填 /sse，除非你明确要用 legacy SSE transport
```

---

## Step 5 — 在 ChatGPT 中开启 Developer Mode
我的Chat GPT 是个人的Pro用户
在 ChatGPT 网页版中进入：

```text
Settings
→ Apps / Apps & Connectors
→ Advanced settings
→ Developer mode
```

---

## Step 6 — 创建 HWind Docs MCP connector

在 ChatGPT 中创建新的 connector / app。

推荐填写：

```text
Name:
HWind Docs
```

```text
Description:
Use this connector when answering questions about HWind documentation, wind turbine aeroelastic simulation, modal dynamics, multi-body dynamics, FAST/OpenFAST comparison, blade/tower DOFs, generalized coordinates, load mapping, solver equations, input files, controller interfaces, validation cases, or combined modal and multi-body dynamics formulation.
```

```text
Connector URL:
https://quiet-wind-hwind.trycloudflare.com/mcp
```

```text
Authentication:
No Authentication
```

使用 `No Authentication` 的前提是：

```text
RAGFlow MCP Server 使用 self-host 模式，RAGFlow API key 已经由 MCP server 持有。
```

```

---

## Step 7 — 在 ChatGPT 新对话中使用

新开一个 ChatGPT 对话，在工具或 connector 列表中选择：

```text
HWind Docs
```

推荐提问模板：

```text
请使用 HWind Docs 检索 HWind 文档，回答：
HWind 的 combined modal and multi-body dynamics formulation 中，广义坐标如何组织？
请分别说明：
1. 刚体自由度
2. 模态自由度
3. 节点力如何映射到广义力
4. 与 OpenFAST ElastoDyn 的差异
只依据检索到的文档回答；如果文档片段不足，请明确说明。
```

另一个模板：

```text
请先调用 HWind Docs 检索 “modal coordinates multi-body generalized coordinates load mapping”，
然后总结 HWind 的动力学方程结构。请区分文档明确说明、合理推断和外部通用知识。
```

---

# 推荐日常启动顺序

每次使用时打开三个终端。

## 终端 1：RAGFlow 主服务

```bash
cd /path/to/ragflow
docker compose -f docker/docker-compose.yml up -d
```

确认：

```text
http://172.28.21.22:9380
```

## 终端 2：RAGFlow MCP Server

```bash
cd /path/to/ragflow

uv run mcp/server/server.py \
  --host=172.28.21.22 \
  --port=9382 \
  --base-url=http://172.28.21.22:9380 \
  --mode=self-host \
  --api-key="$RAGFLOW_API_KEY"
```

确认：

```text
http://172.28.21.22:9382/mcp
```

## 终端 3：Cloudflare Tunnel

```bash
cloudflared tunnel --url http://172.28.21.22:9382
```

复制输出的 HTTPS 域名，并在 ChatGPT connector 里使用：

```text
https://<your-tunnel-domain>/mcp
```

---

# 常见问题排查

## 1. ChatGPT 无法连接 connector

检查：

```text
- Cloudflare tunnel 是否仍在运行
- Connector URL 是否以 https:// 开头
- Connector URL 是否包含 /mcp
- MCP server 是否监听 9382
- 本地 curl http://172.28.21.22:9382/mcp 是否报 Connection refused
- 公司网络是否拦截 trycloudflare.com
```

## 2. 能连接，但没有 ragflow_retrieval / retrieve 工具

检查：

```text
- RAGFlow MCP server 是否正确启动
- RAGFlow 版本是否支持 MCP server
- 是否使用了正确的 /mcp endpoint
- RAGFlow API key 是否有效
- API key 对应 tenant 是否能看到 HWind dataset
```

## 3. 检索不到 HWind 文档

检查 RAGFlow dataset：

```text
- HWind 文档是否解析完成
- dataset description 是否清楚，例如：
  “HWind wind turbine aero-servo-elastic simulation documentation, modal dynamics, multi-body dynamics, input files, solver theory.”
- 文档是否被错误切分
- 文档是否属于该 API key 可访问的 tenant
- query 是否过于宽泛
```

改用更明确的问题：

```text
请检索 “blade modal DOF tower modal DOF generalized coordinate nodal force generalized force”。
```

## 4. ChatGPT 不主动调用 HWind Docs

提问时显式要求：

```text
请使用 HWind Docs 工具回答。
```

或：

```text
请先检索 HWind 文档，再回答。
```

并检查 connector description 是否包含 HWind、modal dynamics、multi-body dynamics、OpenFAST 等关键词。

## 5.不使用 /sse 不稳定

优先使用：

```text
/mcp
```

除非明确需要 legacy SSE transport，否则不要使用：

```text
/sse
```

## 6. Tunnel URL 改变

Cloudflare quick tunnel 每次启动可能生成不同 URL。

解决办法：

```text
测试阶段：每次更新 ChatGPT connector URL。
长期使用：配置 Cloudflare Named Tunnel + 固定域名。
```

---

# 生产环境建议

测试通过后，建议改成：

```text
ChatGPT
    ↓
https://hwind-rag.company.com/mcp
    ↓
Cloudflare Zero Trust / reverse proxy / OAuth
    ↓
RAGFlow MCP Server
    ↓
RAGFlow 主服务
    ↓
HWind dataset
```

生产环境要求：

```text
- 固定 HTTPS 域名
- 访问控制
- 只读 MCP 工具
- 最小权限 API key
- 日志脱敏
- 定期轮换 API key
- 不在日志中输出完整检索内容，除非公司允许
```

---

# HWind 文档检索建议

## Dataset description 建议

在 RAGFlow 中给 HWind dataset 添加清晰描述：

```text
HWind documentation for wind turbine aero-servo-elastic simulation, including combined modal and multi-body dynamics formulation, generalized coordinates, modal DOFs, blade and tower flexibility, drivetrain torsion, aerodynamic coupling, controller interface, input files, validation cases, and FAST/OpenFAST/Bladed comparison.
```

## 文档命名建议

推荐文档名：

```text
HWind_Theory_Manual.pdf
HWind_Input_File_Reference.pdf
HWind_Solver_Architecture.md
HWind_Modal_MBD_Formulation.pdf
HWind_Aero_Coupling.md
HWind_Control_Interface.md
HWind_FAST_OpenFAST_Comparison.md
HWind_Validation_Cases.pdf
```

## 查询关键词建议

中文：

```text
模态坐标
广义坐标
多体动力学
节点力
广义力
叶片模态
塔架模态
传动链扭转
气弹耦合
控制接口
约束方程
拉格朗日乘子
```

英文：

```text
modal coordinates
generalized coordinates
multi-body dynamics
nodal force
generalized force
blade modal DOF
tower modal DOF
drivetrain torsion
aero-servo-elastic coupling
constraint equations
Lagrange multipliers
load mapping
Jacobian transpose
```

---
# MCP 输出解析与展示规范

## 为什么需要清洗 MCP 输出

RAGFlow MCP 的原始返回通常包含较多内部字段，例如：

```text
content
content_ltks
dataset_id
dataset_name
doc_type_kwd
document_id
document_keyword
document_name
document_metadata
id
image_id
important_keywords
positions
similarity
term_similarity
vector_similarity
pagination
query_info
```

这些字段对调试有用，但不适合直接展示给用户。智能体或本地脚本应将其整理为：

```text
1. 检索摘要
2. Top chunks 表格
3. 证据片段
4. 基于证据的回答
5. 可选的原始 ID / 调试信息
```

不要把完整 `response.model_dump()` 直接贴给最终用户，除非用户明确要求调试原始 MCP 返回。

## 当前本地 MCP 测试方式

本项目中的本地测试脚本可以使用 Streamable HTTP 连接 RAGFlow MCP：

```python
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

async with streamable_http_client("http://172.28.21.22:9382/mcp/") as (read_stream, write_stream, _):
    async with ClientSession(read_stream, write_stream) as session:
        await session.initialize()
        tools = await session.list_tools()
        response = await session.call_tool(
            name="ragflow_retrieval",
            arguments={
                "dataset_ids": ["c01c944642d611f1847e7fab85a8d86d"],
                "document_ids": [],
                "question": "介绍天洑工业AI底座?",
            },
        )
```

注意：

```text
- endpoint 示例：http://172.28.21.22:9382/mcp/
- 工具名示例：ragflow_retrieval
- dataset_ids 示例：c01c944642d611f1847e7fab85a8d86d
- 该 dataset 示例名称可能是“扩展材料”，不一定是 HWind 文档库
- HWind 问题必须使用 HWind 对应的 dataset_ids，不要把“扩展材料”误当成 HWind 数据集
```

如果 ChatGPT connector 中工具名显示为 `retrieve`，则使用 `retrieve`；如果显示为 `ragflow_retrieval`，则使用 `ragflow_retrieval`。

## MCP 原始输出中的关键字段

智能体应优先理解这些字段：

```text
query_info.question             原始问题
query_info.similarity_threshold 相似度阈值
query_info.vector_weight        向量权重
query_info.keyword_search       是否启用关键词检索
query_info.dataset_count        检索的数据集数量

pagination.page                 当前页
pagination.page_size            每页数量
pagination.total_chunks         命中 chunk 总数
pagination.total_pages          总页数

chunks[i].content               可引用的正文片段
chunks[i].document_name         文档名，优先展示
chunks[i].document_keyword      文档关键词/文件名，备用展示
chunks[i].dataset_name          数据集名称
chunks[i].id                    chunk id
chunks[i].document_id           文档 id
chunks[i].doc_type_kwd          chunk 类型，例如 image / text
chunks[i].important_keywords    RAGFlow 提取的重要关键词
chunks[i].similarity            综合相似度
chunks[i].term_similarity       词项相似度
chunks[i].vector_similarity     向量相似度
chunks[i].image_id              图像 chunk 的图像 id
chunks[i].positions             chunk 在文档/页面中的位置
chunks[i].document_metadata     文档元数据
```

## 展示格式 1：检索摘要

每次工具调用后，先展示一个简短摘要：

```markdown
### 检索摘要

- 问题：介绍天洑工业AI底座?
- 数据集数量：1
- 命中片段：35
- 当前页：1 / 4
- 相似度阈值：0.20
- 向量权重：0.30
- 关键词检索：false
```

如果用户不是在调试，可以进一步压缩为一句：

```text
已从 1 个数据集中检索到 35 个相关片段，当前使用前 10 个片段生成回答。
```

## 展示格式 2：Top chunks 表格

将原始 chunks 整理为表格，最多展示前 5 到 8 条：

```markdown
### Top 检索片段

| # | similarity | dataset | document | type | chunk_id | keywords |
|---|---:|---|---|---|---|---|
| 1 | 0.3215 | 扩展材料 | 天洑工业AI智能运维产品及服务手册.pdf | image | ecd9a1f400dbf0c9 | 智能预警, 故障诊断系统 |
```

字段取值规则：

```text
document = document_name || document_keyword || document_metadata.name || document_id
chunk_id = id
type     = doc_type_kwd || document_metadata.type || "unknown"
keywords = important_keywords 的前 3 到 5 个
```

相似度展示建议：

```text
similarity >= 0.60：较强相关
0.35 <= similarity < 0.60：中等相关，需要结合内容判断
0.20 <= similarity < 0.35：弱相关，只适合作为辅助证据
similarity < 0.20：一般不要用于结论
```

如果 top chunks 分数偏低，例如只有 0.32 左右，回答时应说明“检索相关性不高，以下为弱相关片段支持的初步总结”。

## 展示格式 3：证据片段

不要直接输出整段 JSON，而是按 chunk 展示：

```markdown
### 证据片段

**[1] 天洑工业AI智能运维产品及服务手册.pdf**  
chunk: `ecd9a1f400dbf0c9`，similarity: `0.3215`，type: `image`

> 设备智能预警与智能监盘系统、故障诊断系统、单一画面监盘、及时预警设备状态、智能优化控制、精确定位故障位置、少人或无人值守、全面提供决策支撑……
```

正文片段过长时：

```text
- 每个 chunk 最多展示 300 到 500 个中文字符
- 保留原文关键词
- 不展示 content_ltks，除非用户调试分词
- 不展示完整 document_metadata，除非用户追踪文档来源
```

## 展示格式 4：面向用户的最终回答

回答应基于整理后的证据，而不是基于原始 JSON。例如：

```markdown
## 结论

根据检索片段，天洑工业 AI 底座强调面向工业设备的智能预警、智能监盘、故障诊断、智能优化控制、少人或无人值守，以及决策支撑能力。

## 文档依据

- 片段 [1] 提到“设备智能预警与智能监盘系统”“故障诊断系统”“及时预警设备状态”“精确定位故障位置”等能力。
- 片段 [1] 还提到“数字专家知识库”“低代码建模”“模型运行环境”“自定义应用组态”等平台能力。

## 不确定点

当前片段主要来自产品手册中的图像/OCR chunk，且 similarity 约为 0.32，相关性偏弱；如需更准确介绍，应继续检索“工业AI底座 架构 低代码建模 数字专家知识库 模型运行环境”。
```

## 展示格式 5：调试信息，默认折叠或放最后

调试时可以在最后展示：

```markdown
### 调试信息

- dataset_id: `c01c944642d611f1847e7fab85a8d86d`
- document_id: `e1f37ca642d611f1847e7fab85a8d86d`
- image_id: `c01c944642d611f1847e7fab85a8d86d-ecd9a1f400dbf0c9`
- positions: `[[2, 75, 526, 309, 507]]`
- document update_date: `2026-04-28T15:53:15`
```

默认不要把 `content_ltks` 展示给最终用户。

## 推荐脚本：pretty_streamMCP.py

建议在项目中保留一个清洗脚本，用于把 `response.model_dump()` 转成可读 Markdown。

运行方式：

```bash
export RAGFLOW_MCP_URL="http://172.28.21.22:9382/mcp/"
export RAGFLOW_TOOL_NAME="ragflow_retrieval"
export RAGFLOW_DATASET_IDS="c01c944642d611f1847e7fab85a8d86d"

python pretty_streamMCP.py "介绍天洑工业AI底座?"
```

输出应包含：

```text
- 检索摘要
- Top chunks 表格
- 证据片段
- 调试 ID
```

## 智能体使用规则

当智能体接收 RAGFlow MCP 输出时：

```text
1. 先检查 isError。若为 true，停止生成答案并报告错误。
2. 从 response.content[*].text 中解析 JSON payload。
3. 提取 chunks、pagination、query_info。
4. 按 similarity 排序；若 RAGFlow 已排序，可以保持原顺序。
5. 过滤明显无关 chunk。
6. 对每个结论绑定至少一个 chunk 来源。
7. 若 similarity 普遍偏低，降低结论强度并提示需要继续检索。
8. 若 chunk 为 image/OCR 类型，说明证据来自图像识别片段，可能存在 OCR 噪声。
9. 不要把 content_ltks 当作正文证据。
10. 不要把 dataset_id / document_id 当成用户可读来源；用户可读来源优先使用 document_name。
```

## 针对 HWind 的额外规则

如果问题是 HWind 相关：

```text
- 只使用 HWind dataset_ids。
- 如果检索结果来自“扩展材料”“天洑工业AI底座”等非 HWind 数据集，应说明“该结果不是 HWind 文档来源”，不要用于回答 HWind 公式或代码问题。
- OpenFAST 对比必须使用本地 OpenFAST repo 或明确标注为通用知识。
- HWind 文档不足时，不要用天洑产品手册内容替代 HWind 理论手册内容。
```

---

# 回答格式建议

当使用 HWind Docs 回答时，优先采用：

```text
## 结论

## 文档依据

## 方程/接口解释

## 与 OpenFAST / FAST 的对应关系

## 文档中未明确说明的部分

## 建议后续检索关键词
```

对于 formulation 类问题，建议回答结构：

```text
1. 坐标定义
2. 自由度划分
3. 柔性体模态表示
4. MBD 约束关系
5. 外载荷到广义力的映射
6. 时间积分/求解器
7. 与 OpenFAST/Bladed 的相似与差异
8. 文档证据与不确定点
```

---

# 最小可用检查清单

在认为方案可用前，必须检查：

```text
[ ] RAGFlow UI 可访问：http://172.28.21.22:9380
[ ] HWind dataset 已解析完成
[ ] RAGFlow API key 可用
[ ] MCP server 已启动：http://172.28.21.22:9382/mcp
[ ] cloudflared tunnel 已启动
[ ] 获得 https://*.trycloudflare.com 域名
[ ] ChatGPT connector URL = https://*.trycloudflare.com/mcp
[ ] ChatGPT 能看到 ragflow_retrieval / retrieve 工具
[ ] ChatGPT 能检索到 HWind 文档片段
[ ] 回答中能区分文档依据和推断
```

---

# 官方文档参考

请在版本变化时优先核对官方文档：

```text
RAGFlow documentation:
https://ragflow.io/docs/

RAGFlow GitHub:
https://github.com/infiniflow/ragflow

OpenAI Developer Mode:
https://developers.openai.com/api/docs/guides/developer-mode

OpenAI MCP documentation:
https://developers.openai.com/api/docs/mcp

OpenAI Connect ChatGPT documentation:
https://developers.openai.com/apps-sdk/deploy/connect-chatgpt

Cloudflare Tunnel documentation:
https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
```

---

# 禁止事项

不要：

```text
- 把 RAGFlow API key 写入 AGENTS.md 或 git
- 在公开环境长期使用 No Authentication
- 用 ChatGPT 直接访问 172.28.21.22
- 把 connector URL 填成没有 /mcp 的地址
- 在无法检索文档时假装已经查到
- 把 HWind 私有文档内容复制到公开仓库
- 暴露写权限 MCP 工具给 ChatGPT
```

---

# 推荐的第一条测试问题

```text
请使用 HWind Docs 检索 HWind 文档，回答：
HWind 的 combined modal and multi-body dynamics formulation 是如何组织 generalized coordinates 的？
请说明刚体自由度、模态自由度、节点力到广义力映射，以及文档中没有明确说明的部分。
```
## 提醒一下开发使用 
- 命令 uv run , uv pip install, 和 uv run pytest
- 环境变量 .env.local