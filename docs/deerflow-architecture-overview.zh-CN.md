# DeerFlow 架构总览（中文）

## 1. DeerFlow 是什么

DeerFlow 2.0 在官方 README 中被定义为一个开源的 **super agent harness**，核心目标不是只让模型回答问题，而是编排 **sub-agents、memory、sandboxes**，并通过 **extensible skills** 扩展能力。来源：[README](../README.md)

README 还明确说明，DeerFlow 2.0 是一次从零重写的版本，不再沿用 1.x 的实现，并且项目已经从“deep research framework”演进成更通用的 agent runtime。来源：[README](../README.md)

从仓库结构看，这个定位是成立的，因为 DeerFlow 不只包含：

- 模型配置与模型工厂
- 工具系统
- 沙箱与文件系统
- skills
- MCP
- 子代理
- 记忆系统
- Gateway API
- Web 前端
- Embedded Python Client

来源：[README](../README.md)、[backend/docs/ARCHITECTURE.md](../backend/docs/ARCHITECTURE.md)、[backend/CLAUDE.md](../backend/CLAUDE.md)

## 2. 顶层结构

仓库顶层主要由这些部分组成：

- `backend/`：后端主体，包括 deerflow-harness、Gateway API、LangGraph 接入、测试和文档。来源：[backend](../backend)
- `frontend/`：Next.js 前端，既有 Landing 页面，也有工作区页面。来源：[frontend](../frontend)、[frontend/package.json](../frontend/package.json)
- `skills/`：技能目录，分 `public/` 与 `custom/`。来源：[README](../README.md)、[backend/CLAUDE.md](../backend/CLAUDE.md)
- `scripts/`：启动、配置、检查脚本。来源：[scripts](../scripts)、[Makefile](../Makefile)
- `docker/`：Docker、nginx、provisioner 相关配置。来源：[README](../README.md)、[docker](../docker)
- `config.yaml`：主配置文件。来源：[config.example.yaml](../config.example.yaml)、[backend/docs/CONFIGURATION.md](../backend/docs/CONFIGURATION.md)
- `extensions_config.json`：MCP 与 skills 扩展配置。来源：[extensions_config.example.json](../extensions_config.example.json)、[backend/CLAUDE.md](../backend/CLAUDE.md)

如果只看后端，仓库又被分成两层：

- `packages/harness/deerflow/`：harness 层，负责 agent、tools、sandbox、models、skills、mcp、config
- `app/`：应用层，负责 Gateway API 和 IM channels

这个边界不是口头约定，而是有测试约束 `deerflow.*` 不能反向依赖 `app.*`。来源：[backend/CLAUDE.md](../backend/CLAUDE.md)

## 3. 运行形态

### 3.1 标准模式

标准模式下 DeerFlow 会启动四个核心服务：

- LangGraph Server：`2024`
- Gateway API：`8001`
- Frontend：`3000`
- Nginx：`2026`

Nginx 是统一入口，负责把：

- `/api/langgraph/*` 代理到 LangGraph
- `/api/*` 代理到 Gateway
- 前端页面代理到 Frontend

来源：[README](../README.md)、[backend/docs/ARCHITECTURE.md](../backend/docs/ARCHITECTURE.md)、[Makefile](../Makefile)

### 3.2 Gateway 模式

Gateway 模式是实验性模式。此时不再单独运行 LangGraph Server，而是把 agent runtime 嵌入 Gateway，由运行时组件管理执行和流式输出。来源：[README](../README.md)、[backend/CLAUDE.md](../backend/CLAUDE.md)

### 3.3 前端入口

DeerFlow 的前端不是“是：

- `frontend/src/app/page.tsx`：Landing Page
- `frontend/src/app/workspace/page.tsx`：工作区入口

所以访问根路径时看到的是官网式首页，进入工作区需要走 `/workspace` 路径。来源：[frontend/src/app/page.tsx](../frontend/src/app/page.tsx)、[frontend/src/app/workspace/page.tsx](../frontend/src/app/workspace/page.tsx)

## 4. 请求流转

根据官方架构文档，一次典型请求的主流程是：

1. 浏览器向 `/api/langgraph/threads/{thread_id}/runs` 发请求
2. Nginx 将其转发给 LangGraph Server
3. LangGraph 读取或创建线程状态
4. 依次执行中间件链
5. 调用模型、工具、子代理
6. 通过 SSE 把增量结果返回给前端

来源：[backend/docs/ARCHITECTURE.md](../backend/docs/ARCHITECTURE.md)

## 5. 线程状态与工作区

`ThreadState` 在 LangGraph 的基础上额外维护了这些关键信息：

- `sandbox`
- `thread_data`
- `title`
- `artifacts`
- `todos`
- `uploaded_files`
- `viewed_images`

这说明 DeerFlow 的线程上下文不是只有 `messages`，还显式带着文件系统、任务和产物状态。来源：[backend/packages/harness/deerflow/agents/thread_state.py](../backend/packages/harness/deerflow/agents/thread_state.py)

每个线程都会拥有隔离的物理目录，例如：

- `backend/.deer-flow/threads/{thread_id}/user-data/workspace`
- `backend/.deer-flow/threads/{thread_id}/user-data/uploads`
- `backend/.deer-flow/threads/{thread_id}/user-data/outputs`

而 agent 看到的是虚拟路径：

- `/mnt/user-data/workspace`
- `/mnt/user-data/uploads`
- `/mnt/user-data/outputs`
- `/mnt/skills`

来源：[backend/docs/ARCHITECTURE.md](../backend/docs/ARCHITECTURE.md)、[backend/CLAUDE.md](../backend/CLAUDE.md)、[backend/packages/harness/deerflow/sandbox/tools.py](../backend/packages/harness/deerflow/sandbox/tools.py)

## 6. 中间件链

Lead agent 的执行不是直接“拿消息调模型”，而是先经过一条明确的中间件链。当前仓库中能看到的核心顺序包括：

1. `ThreadDataMiddleware`
2. `UploadsMiddleware`
3. `SandboxMiddleware`
4. `DanglingToolCallMiddleware`
5. `GuardrailMiddleware`
6. `SummarizationMiddleware`
7. `TodoMiddleware`
8. `TitleMiddleware`
9. `MemoryMiddleware`
10. `ViewImageMiddleware`
11. `SubagentLimitMiddleware`
12. `ClarificationMiddleware`

这些中间件分别负责工作目录初始化、上传注入、沙箱获取、上下文压缩、计划模式、记忆更新、视觉注入、澄清打断等逻辑。来源：[backend/packages/harness/deerflow/agents/lead_agent/agent.py](../backend/packages/harness/deerflow/agents/lead_agent/agent.py)、[backend/CLAUDE.md](../backend/CLAUDE.md)

## 7. 核心子系统

### 7.1 Lead Agent 与系统提示词

Lead agent 的入口是 `make_lead_agent`，由 `backend/langgraph.json` 注册。系统提示词通过 `apply_prompt_template()` 组装，会把 soul、memory、skills、subagent 说明、工作目录约束等拼进去。来源：[backend/langgraph.json](../backend/langgraph.json)、[backend/packages/harness/deerflow/agents/lead_agent/agent.py](../backend/packages/harness/deerflow/agents/lead_agent/agent.py)、[backend/packages/harness/deerflow/agents/lead_agent/prompt.py](../backend/packages/harness/deerflow/agents/lead_agent/prompt.py)

一个很关键的点是，skills 不是全量塞进 prompt，而是以“先识别、再按需 `read_file` 加载 `SKILL.md`”的方式使用，这有助于控制上下文长度。来源：[backend/packages/harness/deerflow/agents/lead_agent/prompt.py](../backend/packages/harness/deerflow/agents/lead_agent/prompt.py)

### 7.2 模型工厂

`create_chat_model()` 会读取 `config.yaml` 中的模型定义，并通过反射解析 `use:` 字段来实例化实际模型类，同时处理：

- 默认模型回退
- `thinking_enabled`
- `when_thinking_enabled`
- vLLM / OpenAI-compatible / Anthropic 差异
- Codex 特殊逻辑
- tracing callbacks

来源：[backend/packages/harness/deerflow/models/factory.py](../backend/packages/harness/deerflow/models/factory.py)、[backend/docs/CONFIGURATION.md](../backend/docs/CONFIGURATION.md)

### 7.3 工具系统

`get_available_tools()` 会组合：

- `config.yaml` 中定义的工具
- 内置工具
- MCP 工具
- ACP agent 工具
- 子代理工具

来源：[backend/packages/harness/deerflow/tools/tools.py](../backend/packages/harness/deerflow/tools/tools.py)

除了内置的 `present_file`、`ask_clarification`、`view_image`、`task` 外，真正承担开发工作能力的还有沙箱工具：

- `bash`
- `ls`
- `read_file`
- `write_file`
- `str_replace`

来源：[backend/packages/harness/deerflow/tools/tools.py](../backend/packages/harness/deerflow/tools/tools.py)、[backend/packages/harness/deerflow/sandbox/tools.py](../backend/packages/harness/deerflow/sandbox/tools.py)

### 7.4 Sandbox

README 里强调 DeerFlow “has its own computer”，对应到实现层面就是：

- agent 有工作目录、上传目录、输出目录、技能目录
- agent 可读写文件
- 在特定配置下可执行 shell
- 支持本地沙箱与容器沙箱

来源：[README](../README.md)、[backend/docs/CONFIGURATION.md](../backend/docs/CONFIGURATION.md)、[backend/docs/ARCHITECTURE.md](../backend/docs/ARCHITECTURE.md)

项目同时明确说明本地 host bash 默认关闭，因为本地 host bash 不是安全隔离边界。若需要更可信的执行边界，应优先使用容器沙箱。来源：[README](../README.md)、[backend/docs/CONFIGURATION.md](../backend/docs/CONFIGURATION.md)

### 7.5 Skills

Skill 是 DeerFlow 的核心扩展单元。每个 skill 以 `SKILL.md` 为主文件，描述某一类工作流的步骤、规范和参考资源。来源：[README](../README.md)、[backend/CLAUDE.md](../backend/CLAUDE.md)

当前仓库自带的公开 skills 已覆盖：

- 深度研究
- 代码文档
- 前端设计
- GitHub 研究
- Claude Code 集成
- skill 创建

来源：[skills/public](../skills/public)

### 7.6 Subagents

子代理由 `task` 工具驱动，并由 `SubagentExecutor` 负责后台执行。当前内置至少包括：

- `general-purpose`
- `bash`

其特点包括：

- 独立上下文
- 可过滤工具
- 线程池执行
- 超时控制
- 向前端发送 `task_started`、`task_running`、`task_completed` 等事件

来源：[README](../README.md)、[backend/packages/harness/deerflow/tools/builtins/task_tool.py](../backend/packages/harness/deerflow/tools/builtins/task_tool.py)、[backend/packages/harness/deerflow/subagents/executor.py](../backend/packages/harness/deerflow/subagents/executor.py)

### 7.7 MCP

DeerFlow 使用 `extensions_config.json` 管理 MCP servers，并通过 `MultiServerMCPClient` 接入 stdio、SSE、HTTP 等传输方式，同时支持基于 mtime 的变更重载。来源：[backend/docs/ARCHITECTURE.md](../backend/docs/ARCHITECTURE.md)、[backend/CLAUDE.md](../backend/CLAUDE.md)

### 7.8 ACP

ACP 用于把外部 agent 当成 DeerFlow 的工具来调用。仓库支持在 `config.yaml` 中声明 ACP agents，并生成 `invoke_acp_agent` 工具。项目也明确指出，标准 `codex` CLI 本身不是 ACP-compatible，如需接入，需要 ACP adapter。来源：[README](../README.md)、[backend/CLAUDE.md](../backend/CLAUDE.md)、[backend/packages/harness/deerflow/config/acp_config.py](../backend/packages/harness/deerflow/config/acp_config.py)

### 7.9 Memory

长期记忆系统由 `MemoryMiddleware`、queue、updater、prompt 等组成，用于：

1. 过滤对话中的用户消息和最终 AI 回复
2. 入队、去抖和批处理
3. 用模型提取事实与上下文
4. 写入记忆文件
5. 在后续对话中注入 memory

来源：[backend/CLAUDE.md](../backend/CLAUDE.md)

### 7.10 Embedded Client

`DeerFlowClient` 允许你在 Python 进程中直接使用 DeerFlow，而不依赖 HTTP 服务。它支持：

- `chat()`
- `stream()`
- 模型查询
- skills / MCP 管理
- 上传管理
- artifact 读取

并且返回结构被设计成与 Gateway API 对齐。来源：[backend/packages/harness/deerflow/client.py](../backend/packages/harness/deerflow/client.py)、[backend/CLAUDE.md](../backend/CLAUDE.md)

### 7.11 IM Channels

应用层还支持 Feishu、Slack、Telegram 等渠道适配，它们通过统一 message bus 与 DeerFlow runtime 通信。来源：[backend/app/gateway/app.py](../backend/app/gateway/app.py)、[backend/CLAUDE.md](../backend/CLAUDE.md)

## 8. 为什么它和一般 agent 不一样

从仓库实现看，DeerFlow 和一般“模型 + 几个工具”的 agent 项目相比，差异主要在这里：

- 它有线程级工作区，而不只是消息上下文
- 它把 skills 作为高层工作流模块，而不只是 tool list
- 它把子代理编排做成一等公民
- 它同时提供 Web、API、IM、embedded client 多种入口
- 它的 harness / app 边界相对清晰，工程化程度较高

来源：[README](../README.md)、[backend/docs/ARCHITECTURE.md](../backend/docs/ARCHITECTURE.md)、[backend/CLAUDE.md](../backend/CLAUDE.md)

## 9. 推荐阅读顺序

如果你是第一次研究 DeerFlow，建议按这个顺序读：

1. [README.md](../README.md)
2. [backend/docs/ARCHITECTURE.md](../backend/docs/ARCHITECTURE.md)
3. [backend/docs/CONFIGURATION.md](../backend/docs/CONFIGURATION.md)
4. [backend/CLAUDE.md](../backend/CLAUDE.md)
5. [backend/langgraph.json](../backend/langgraph.json)
6. [backend/packages/harness/deerflow/agents/lead_agent/agent.py](../backend/packages/harness/deerflow/agents/lead_agent/agent.py)
7. [backend/packages/harness/deerflow/agents/lead_agent/prompt.py](../backend/packages/harness/deerflow/agents/lead_agent/prompt.py)
8. [backend/packages/harness/deerflow/tools/tools.py](../backend/packages/harness/deerflow/tools/tools.py)
9. [backend/packages/harness/deerflow/sandbox/tools.py](../backend/packages/harness/deerflow/sandbox/tools.py)
10. [backend/packages/harness/deerflow/client.py](../backend/packages/harness/deerflow/client.py)

