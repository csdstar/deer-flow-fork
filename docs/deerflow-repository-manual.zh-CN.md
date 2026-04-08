# DeerFlow 仓库说明书（面向二次开发与架构研究）

> 适用范围：本文只基于当前仓库中的 README、架构文档、配置文档和源码入口整理，不引入仓库外的推测性信息。若后续版本变更，请以源码为准。  
> 主要出处见文末“来源索引”。

## 1. 先给结论

DeerFlow 2.0 不是“只有一个 agent 加几个工具”的轻量框架，而是一个完整的 **super agent harness**：它把模型选择、线程状态、文件系统、沙箱执行、技能系统、MCP、子代理、记忆、网关 API、Web 前端、IM 渠道和嵌入式 Python 客户端都做成了现成能力。来源：[README](../README.md)、[ARCHITECTURE.md](../backend/docs/ARCHITECTURE.md)、[backend/CLAUDE.md](../backend/CLAUDE.md)

如果你关心“它能不能像 Codex / Claude Code 一样做本地开发工作”，答案是：

- **能做相当一部分“对话式开发工作”**：它有文件读写、bash、子代理、技能、沙箱、上传、产物输出、代码相关 skills，也支持把 Codex / Claude Code 当作模型提供方接入。来源：[README](../README.md)、[CONFIGURATION.md](../backend/docs/CONFIGURATION.md)、[tools.py](../backend/packages/harness/deerflow/tools/tools.py)
- **但它默认不是一个现成的终端型 coding assistant 产品**：仓库当前官方主入口是 Web UI、Gateway / LangGraph API 和嵌入式 Python Client，而不是一个类似 `codex` 或 `claude` 的单体 CLI 程序。来源：[README](../README.md)、[Makefile](../Makefile)、[backend/packages/harness/pyproject.toml](../backend/packages/harness/pyproject.toml)、[client.py](../backend/packages/harness/deerflow/client.py)
- **它更像“可扩展的 agent 运行底座”**：你可以把它当应用直接用，也可以把它当可嵌入 runtime 改造成更接近本地开发助手的形态。来源：[README](../README.md)、[backend/CLAUDE.md](../backend/CLAUDE.md)

## 2. 回答你最关心的问题：它能否像 Codex / Claude Code 一样做本地开发？

### 2.1 可以做到的部分

- 用对话方式驱动代码、文件和任务处理：内置工具系统包含 `read_file`、`write_file`、`str_replace`、`ls`、`bash`、`present_file`、`task` 等能力；子代理可并发拆分复杂任务。来源：[README](../README.md)、[tools.py](../backend/packages/harness/deerflow/tools/tools.py)、[task_tool.py](../backend/packages/harness/deerflow/tools/builtins/task_tool.py)
- 以“开发工作区”的方式运行：每个线程有独立的 `workspace`、`uploads`、`outputs` 目录，agent 可以在这些目录中工作并输出交付物。来源：[ARCHITECTURE.md](../backend/docs/ARCHITECTURE.md)、[backend/CLAUDE.md](../backend/CLAUDE.md)
- 使用 Codex / Claude Code 作为底层模型提供方：配置文档和 README 都给出了 `CodexChatModel` 与 `ClaudeChatModel` 的示例。来源：[README](../README.md)、[CONFIGURATION.md](../backend/docs/CONFIGURATION.md)
- 从 Claude Code 直接操作一个正在运行的 DeerFlow：仓库自带 `claude-to-deerflow` skill，可以让 Claude Code 通过 DeerFlow 的 HTTP 接口与之协作。来源：[README](../README.md)、[skills/public/claude-to-deerflow](../skills/public/claude-to-deerflow)
- 通过嵌入式 Python Client 在本地进程中直接调用 DeerFlow，而不依赖 LangGraph Server / Gateway HTTP 服务。来源：[client.py](../backend/packages/harness/deerflow/client.py)、[backend/CLAUDE.md](../backend/CLAUDE.md)
- 通过 ACP 把外部 agent 作为工具接入 DeerFlow，例如用 ACP 适配器包装的 Codex agent。来源：[README](../README.md)、[backend/CLAUDE.md](../backend/CLAUDE.md)、[acp_config.py](../backend/packages/harness/deerflow/config/acp_config.py)

### 2.2 目前不是的部分

- 仓库没有把 DeerFlow 做成一个“官方主打的终端交互式 CLI 应用”。主运行方式是启动 Nginx + Frontend + Gateway + LangGraph，访问浏览器入口；或在 Python 中嵌入调用。来源：[README](../README.md)、[Makefile](../Makefile)、[langgraph.json](../backend/langgraph.json)、[client.py](../backend/packages/harness/deerflow/client.py)
- `deerflow-harness` 的打包配置是库包形态，没有声明面向最终用户的 console script 入口。这意味着它当前更像“框架/运行时”而不是“单命令终端产品”。来源：[backend/packages/harness/pyproject.toml](../backend/packages/harness/pyproject.toml)
- 在本地沙箱模式下，host `bash` 默认关闭，因为项目明确认为本地 host bash 不是安全隔离边界；如果你要做更接近 Codex 的本地命令执行体验，通常要显式开启 host bash 或切到容器沙箱。来源：[README](../README.md)、[CONFIGURATION.md](../backend/docs/CONFIGURATION.md)、[tools.py](../backend/packages/harness/deerflow/tools/tools.py)

### 2.3 最准确的定位

如果用一句话概括：

**DeerFlow 已经具备很多“coding agent runtime”能力，但它当前更像一个面向 Web / API / 集成场景的 agent harness，而不是默认就长成 Codex / Claude Code 那种终端产品。**

## 3. 项目定位：它到底是什么

README 对 DeerFlow 2.0 的官方定义是：

- 它是一个开源的 **super agent harness**
- 核心是编排 **sub-agents、memory、sandboxes**
- 通过 **extensible skills** 做能力扩展
- 2.0 是一次“ground-up rewrite”，不再是旧版 deep research 框架的延续实现

来源：[README](../README.md)

README 还明确写了 DeerFlow 的转向逻辑：社区把它从“Deep Research 工具”用成了数据流水线、PPT、网站、内容工作流等通用 agent 平台，因此 2.0 被重构成“带电池的 harness”，而不是让你从零拼装的框架。来源：[README](../README.md)

这也是理解 DeerFlow 的关键：  
**它的重点不只是“让模型回答问题”，而是提供一整套能把任务真正做完的运行基础设施。**

## 4. 仓库的顶层结构

当前仓库顶层主要分成这些部分：

- `backend/`：后端主体，包括 deerflow-harness 包、Gateway API、LangGraph 接入、测试与后端文档。来源：[backend](../backend)
- `frontend/`：Next.js 前端，既包含 Landing 页面，也包含实际工作区页面、设置、对话、任务、产物等模块。来源：[frontend](../frontend)、[frontend/package.json](../frontend/package.json)
- `skills/`：技能目录，分 `public/` 与 `custom/`，每个 skill 以 `SKILL.md` 为主文件。来源：[README](../README.md)、[backend/CLAUDE.md](../backend/CLAUDE.md)
- `scripts/`：启动、配置、辅助脚本，例如 `serve.sh`、`configure.py`、`check.py`。来源：[scripts](../scripts)、[Makefile](../Makefile)
- `docs/`：仓库内补充文档。来源：[docs](../docs)
- `docker/`：Docker / nginx / provisioner 相关配置。来源：[README](../README.md)、[docker](../docker)
- `config.yaml`：主配置文件，定义模型、工具、沙箱、记忆、子代理、技能路径等。来源：[config.example.yaml](../config.example.yaml)、[CONFIGURATION.md](../backend/docs/CONFIGURATION.md)
- `extensions_config.json`：MCP 与技能启停状态等扩展配置。来源：[extensions_config.example.json](../extensions_config.example.json)、[backend/CLAUDE.md](../backend/CLAUDE.md)

如果只看后端，项目又被故意分成两层：

- `packages/harness/deerflow/`：可发布的 harness 层，负责 agent、tools、sandbox、skills、mcp、models、config 等核心机制
- `app/`：应用层，负责 FastAPI Gateway 和 IM channels

而且这个边界不是口头约定，而是有测试强制保证 `deerflow.*` 不反向 import `app.*`。来源：[backend/CLAUDE.md](../backend/CLAUDE.md)

## 5. 运行形态与访问入口

### 5.1 标准模式

标准模式下有 4 个进程 / 服务：

- LangGraph Server：`2024`
- Gateway API：`8001`
- Frontend：`3000`
- Nginx：`2026`

Nginx 是统一入口，会把：

- `/api/langgraph/*` 代理到 LangGraph
- `/api/*` 代理到 Gateway
- 其他前端路径代理到 Frontend

来源：[README](../README.md)、[ARCHITECTURE.md](../backend/docs/ARCHITECTURE.md)、[Makefile](../Makefile)

### 5.2 Gateway 模式

Gateway 模式是实验性形态。此时不再单独跑 LangGraph Server，而是把 agent runtime 嵌入 Gateway，由 `RunManager` 等运行时组件管理执行与流式输出。来源：[README](../README.md)、[backend/CLAUDE.md](../backend/CLAUDE.md)

### 5.3 Web 入口

- `frontend/src/app/page.tsx` 是 Landing Page，也就是“官网式首页”
- 真正的工作区入口在 `frontend/src/app/workspace/page.tsx`，它会进一步重定向到 `/workspace/chats/new` 或 demo 线程

所以 DeerFlow 前端是“官网 + 工作区”双结构，不是根路径直接进聊天区。来源：[frontend/src/app/page.tsx](../frontend/src/app/page.tsx)、[frontend/src/app/workspace/page.tsx](../frontend/src/app/workspace/page.tsx)

## 6. 一次请求的完整工作流程

这是理解 DeerFlow 最重要的一节。

### 6.1 从浏览器到 agent runtime

官方架构文档给出的链路是：

1. 浏览器向 `/api/langgraph/threads/{thread_id}/runs` 发请求
2. Nginx 把它转发给 LangGraph Server
3. LangGraph 读取 / 创建线程状态
4. 依次执行中间件链
5. 调用模型、工具、子代理
6. 通过 SSE 把增量结果流回前端

来源：[ARCHITECTURE.md](../backend/docs/ARCHITECTURE.md)

### 6.2 中间件链在做什么

Lead agent 的中间件链是 DeerFlow 的关键设计之一。`backend/packages/harness/deerflow/agents/lead_agent/agent.py` 和 `backend/CLAUDE.md` 给出的顺序大体包括：

1. `ThreadDataMiddleware`：初始化该线程的工作目录
2. `UploadsMiddleware`：把上传文件注入上下文
3. `SandboxMiddleware`：获取沙箱
4. `DanglingToolCallMiddleware`：修补不完整工具消息
5. `GuardrailMiddleware`：可选的工具调用授权
6. `SummarizationMiddleware`：上下文压缩
7. `TodoMiddleware`：计划模式任务追踪
8. `TitleMiddleware`：自动命名线程
9. `MemoryMiddleware`：把对话入队到长期记忆更新
10. `ViewImageMiddleware`：视觉模型时注入图像
11. `SubagentLimitMiddleware`：限制每轮并发子代理数量
12. `ClarificationMiddleware`：需要澄清时打断执行

来源：[agent.py](../backend/packages/harness/deerflow/agents/lead_agent/agent.py)、[backend/CLAUDE.md](../backend/CLAUDE.md)

### 6.3 线程状态保存了什么

`ThreadState` 在 LangGraph 原始 `AgentState` 基础上增加了：

- `sandbox`
- `thread_data`
- `title`
- `artifacts`
- `todos`
- `uploaded_files`
- `viewed_images`

这说明 DeerFlow 的对话状态不是“只有 messages”，而是把文件系统、任务、视觉、产物等都纳入线程上下文。来源：[thread_state.py](../backend/packages/harness/deerflow/agents/thread_state.py)

### 6.4 实际文件落在哪里

每个线程有独立目录，例如：

- `backend/.deer-flow/threads/{thread_id}/user-data/workspace`
- `backend/.deer-flow/threads/{thread_id}/user-data/uploads`
- `backend/.deer-flow/threads/{thread_id}/user-data/outputs`

而 agent 在提示词里看到的是虚拟路径：

- `/mnt/user-data/workspace`
- `/mnt/user-data/uploads`
- `/mnt/user-data/outputs`
- `/mnt/skills`

这层虚拟路径映射是 DeerFlow 让 agent 拥有“像一台电脑一样的工作区”的基础。来源：[ARCHITECTURE.md](../backend/docs/ARCHITECTURE.md)、[backend/CLAUDE.md](../backend/CLAUDE.md)、[sandbox/tools.py](../backend/packages/harness/deerflow/sandbox/tools.py)

## 7. 核心子系统逐项说明

### 7.1 Lead Agent 与系统提示词

Lead agent 的入口是 `make_lead_agent`，由 `backend/langgraph.json` 注册为 LangGraph graph 入口。系统提示词由 `apply_prompt_template()` 组装，里面会插入：

- agent identity / soul
- memory
- skills section
- deferred tools section
- subagent section
- 工作目录与输出要求
- 澄清规则、引用规则等

来源：[backend/langgraph.json](../backend/langgraph.json)、[agent.py](../backend/packages/harness/deerflow/agents/lead_agent/agent.py)、[prompt.py](../backend/packages/harness/deerflow/agents/lead_agent/prompt.py)

一个很有代表性的设计是：skills 不是整批塞进上下文，而是通过系统提示词告诉 agent “先识别是否匹配 skill，再用 `read_file` 去读 skill 的 `SKILL.md`，需要时再读同目录引用资源”。这是 DeerFlow 控制上下文膨胀的重要方式。来源：[prompt.py](../backend/packages/harness/deerflow/agents/lead_agent/prompt.py)

### 7.2 模型工厂

`create_chat_model()` 会根据 `config.yaml` 中的模型配置，通过反射解析 `use:` 字段，动态创建具体的 LangChain chat model，并处理：

- 默认模型回退
- 是否支持 thinking
- `when_thinking_enabled` 覆盖逻辑
- vLLM / OpenAI-compatible / Anthropic 等差异
- Codex 特殊逻辑
- tracing callbacks

来源：[factory.py](../backend/packages/harness/deerflow/models/factory.py)、[CONFIGURATION.md](../backend/docs/CONFIGURATION.md)

这也是 DeerFlow 能同时支持：

- 常规 OpenAI / Anthropic / DeepSeek 类 API
- Codex CLI
- Claude Code OAuth
- vLLM
- OpenAI-compatible 网关

的原因。来源：[README](../README.md)、[CONFIGURATION.md](../backend/docs/CONFIGURATION.md)

### 7.3 工具系统

`get_available_tools()` 会组合多类工具：

- `config.yaml` 中声明的工具
- 内置工具
- MCP 工具
- ACP agent 工具
- 运行时可选的子代理工具

来源：[tools.py](../backend/packages/harness/deerflow/tools/tools.py)

内置工具至少包括：

- `present_file`
- `ask_clarification`
- `view_image`（模型支持视觉时）
- `task`（启用子代理时）

而沙箱层还提供了真正用于开发工作的文件与命令工具：

- `bash`
- `ls`
- `read_file`
- `write_file`
- `str_replace`

来源：[tools.py](../backend/packages/harness/deerflow/tools/tools.py)、[sandbox/tools.py](../backend/packages/harness/deerflow/sandbox/tools.py)

### 7.4 Sandbox：DeerFlow 为什么不像普通聊天机器人

README 的一个核心说法是：DeerFlow “has its own computer”。这不是修辞，而是实现层面的：

- agent 能看到自己的工作目录、上传目录、输出目录、技能目录
- 可以读写文件
- 可以在合适配置下执行 shell
- 可以在本地沙箱或容器沙箱里运行

来源：[README](../README.md)、[CONFIGURATION.md](../backend/docs/CONFIGURATION.md)、[ARCHITECTURE.md](../backend/docs/ARCHITECTURE.md)

同时项目也明确承认本地 host bash 不是真正安全边界，所以：

- `LocalSandboxProvider` 适合开发便利
- `AioSandboxProvider` 才是隔离更强的容器方案

来源：[README](../README.md)、[CONFIGURATION.md](../backend/docs/CONFIGURATION.md)

### 7.5 Skills：工作流模块化

技能系统是 DeerFlow 的一大特色。skill 本质上是一个目录 + `SKILL.md`，可带 frontmatter，描述一个专业工作流的最佳实践、步骤和资源。来源：[README](../README.md)、[backend/CLAUDE.md](../backend/CLAUDE.md)

仓库当前公开技能目录中已经可以看到很多方向，例如：

- `deep-research`
- `code-documentation`
- `frontend-design`
- `github-deep-research`
- `claude-to-deerflow`
- `skill-creator`

来源：[skills/public](../skills/public)

这说明 DeerFlow 的“能力扩展”不是只靠加工具，也靠把高层工作流打包成 skill。  
相比一般 agent，这更接近“让 agent 会一门门手艺”。

### 7.6 Subagents：并行拆解复杂任务

`task` 工具会把任务委托给 `SubagentExecutor`。内置子代理包括：

- `general-purpose`
- `bash`

子代理具有这些特征：

- 自己独立的上下文
- 工具可按 allowlist / denylist 过滤
- 后台线程池执行
- 有超时
- 会向前端流式报告 `task_started`、`task_running`、`task_completed` 等事件
- 每轮调用数量受 `SubagentLimitMiddleware` 限制

来源：[README](../README.md)、[task_tool.py](../backend/packages/harness/deerflow/tools/builtins/task_tool.py)、[executor.py](../backend/packages/harness/deerflow/subagents/executor.py)、[registry.py](../backend/packages/harness/deerflow/subagents/registry.py)、[backend/CLAUDE.md](../backend/CLAUDE.md)

这也是 DeerFlow 从“单代理工具调用”走向“多代理任务编排”的关键分界线。

### 7.7 MCP：把外部能力接进来

DeerFlow 用 `extensions_config.json` 管理 MCP server，并通过 `langchain-mcp-adapters` 的 `MultiServerMCPClient` 接入多种传输方式：

- stdio
- SSE
- HTTP

并支持配置变化后的 mtime 失效重载。来源：[ARCHITECTURE.md](../backend/docs/ARCHITECTURE.md)、[backend/CLAUDE.md](../backend/CLAUDE.md)

这意味着它不是把所有工具都写死在仓库里，而是可以把外部系统通过 MCP 暴露给 agent。

### 7.8 ACP：把“外部 agent”当工具调用

这是 DeerFlow 很容易被忽略、但对“本地开发助手”方向非常关键的一点。

仓库支持在 `config.yaml` 中配置 ACP agents，然后生成 `invoke_acp_agent` 工具来调用这些外部 agent。官方文档还特别提醒：

- 标准 `codex` CLI 本身不是 ACP-compatible
- 如果要把 Codex 接进来，需要 ACP adapter，例如 `@zed-industries/codex-acp`

来源：[README](../README.md)、[backend/CLAUDE.md](../backend/CLAUDE.md)、[acp_config.py](../backend/packages/harness/deerflow/config/acp_config.py)

从架构上说，这让 DeerFlow 不只是“自己有 agent”，还可以把别的 agent 编排进自己的工具链。

### 7.9 Memory：长期记忆系统

记忆系统由 `MemoryMiddleware`、queue、updater、prompt 等组成。核心流程是：

1. 对话中的用户消息和最终 AI 回复进入记忆队列
2. 队列做去抖和批处理
3. 后台用模型提取事实与上下文
4. 写入 `memory.json`
5. 后续对话把压缩后的 memory 注入系统提示词

来源：[backend/CLAUDE.md](../backend/CLAUDE.md)

这和很多“一轮一轮纯临时上下文”的 agent 很不一样，它有显式的长期状态维护机制。

### 7.10 Embedded Client：不走 HTTP，也能用 DeerFlow

`DeerFlowClient` 是这套仓库非常实用的一个能力。它允许你在 Python 进程里：

- `chat()`
- `stream()`
- 列模型、技能、MCP
- 管理上传
- 读取 artifacts
- 重置 agent

而且返回结构被设计成和 Gateway API 对齐，并有 conformance tests 保证不漂移。来源：[client.py](../backend/packages/harness/deerflow/client.py)、[backend/CLAUDE.md](../backend/CLAUDE.md)

这意味着如果你以后想把 DeerFlow 嵌进自己的 CLI、IDE 插件或自动化脚本，这里是一个很好的切入点。

### 7.11 IM Channels：不仅是浏览器

应用层还有 Feishu、Slack、Telegram 等 IM 渠道适配，消息通过统一 message bus 进出，再由 LangGraph / Gateway 执行 agent 流程。来源：[backend/app/gateway/app.py](../backend/app/gateway/app.py)、[backend/CLAUDE.md](../backend/CLAUDE.md)

这再次说明 DeerFlow 的定位是“agent runtime + 多前端入口”，而不是单一聊天页面。

## 8. 它相比一般 agent 的特殊之处

这一节是我基于仓库结构和文档做的归纳，不是 README 原话逐句复述。

### 8.1 它不是“只管推理”的 agent，而是“有工作现场”的 agent

普通 agent 常停留在：模型 + 工具调用。  
DeerFlow 额外提供了：

- 线程级文件系统
- 上传与产物目录
- 路径映射
- 本地 / 容器沙箱
- Artifact 服务

所以它更像“能实际做事的运行环境”。来源：[README](../README.md)、[ARCHITECTURE.md](../backend/docs/ARCHITECTURE.md)

### 8.2 它把“高层工作流”抽象成了 skills

很多 agent 只扩展工具；DeerFlow 同时扩展 **workflow knowledge**。  
Skill 通过 `SKILL.md` 把最佳实践、步骤和参考资源变成可按需读取的模块，这是它和一般 tool-only agent 的明显差异。来源：[README](../README.md)、[prompt.py](../backend/packages/harness/deerflow/agents/lead_agent/prompt.py)、[skills/public](../skills/public)

### 8.3 它把“多代理编排”做成了一等公民

子代理不是外挂，而是：

- 有独立执行器
- 有并发限制
- 有状态事件
- 有专门的 prompt 规则
- 能被 lead agent 系统化调度

这已经不是“模型偶尔开几个并行工具调用”的程度，而是明确的 orchestration 设计。来源：[README](../README.md)、[task_tool.py](../backend/packages/harness/deerflow/tools/builtins/task_tool.py)、[executor.py](../backend/packages/harness/deerflow/subagents/executor.py)

### 8.4 它同时支持“应用模式”和“框架模式”

你可以直接跑完整站点，也可以：

- 用 `DeerFlowClient` 嵌入
- 用 MCP 扩展
- 用 ACP 接外部 agent
- 改 skill
- 改模型工厂
- 改中间件链

这让它既像产品，也像底座。来源：[README](../README.md)、[client.py](../backend/packages/harness/deerflow/client.py)、[backend/CLAUDE.md](../backend/CLAUDE.md)

### 8.5 它对“工程边界”是认真的

很多开源 agent 项目后期容易变成“大杂烩”。  
DeerFlow 当前比较难得的一点是：

- Harness / App 分层清晰
- config 与 extensions config 分开
- Gateway 与 Embedded Client 对齐
- 有边界测试和 conformance tests

这说明它在朝“可维护的 agent runtime”而不是“demo 工程”发展。来源：[backend/CLAUDE.md](../backend/CLAUDE.md)

## 9. 如果你要把它当“本地开发助手”继续研究，重点看哪里

### 9.1 最先读

- [README.md](../README.md)
- [backend/docs/ARCHITECTURE.md](../backend/docs/ARCHITECTURE.md)
- [backend/docs/CONFIGURATION.md](../backend/docs/CONFIGURATION.md)
- [backend/CLAUDE.md](../backend/CLAUDE.md)

这四个文件足够建立对项目的第一层全局认识。

### 9.2 然后读 agent 主链路

- [backend/langgraph.json](../backend/langgraph.json)
- [backend/packages/harness/deerflow/agents/lead_agent/agent.py](../backend/packages/harness/deerflow/agents/lead_agent/agent.py)
- [backend/packages/harness/deerflow/agents/lead_agent/prompt.py](../backend/packages/harness/deerflow/agents/lead_agent/prompt.py)
- [backend/packages/harness/deerflow/agents/thread_state.py](../backend/packages/harness/deerflow/agents/thread_state.py)

### 9.3 如果你关心“像 Codex 那样改代码”

重点看：

- [backend/packages/harness/deerflow/tools/tools.py](../backend/packages/harness/deerflow/tools/tools.py)
- [backend/packages/harness/deerflow/sandbox/tools.py](../backend/packages/harness/deerflow/sandbox/tools.py)
- [backend/packages/harness/deerflow/tools/builtins/task_tool.py](../backend/packages/harness/deerflow/tools/builtins/task_tool.py)
- [backend/packages/harness/deerflow/subagents/executor.py](../backend/packages/harness/deerflow/subagents/executor.py)
- [backend/packages/harness/deerflow/config/acp_config.py](../backend/packages/harness/deerflow/config/acp_config.py)

因为“本地开发工作”的关键不只是模型，而是：

- 文件能不能改
- 命令能不能跑
- 任务能不能拆
- 能不能调用外部 agent

### 9.4 如果你关心“为什么它不是一个单纯 Web demo”

看：

- [backend/packages/harness/deerflow/client.py](../backend/packages/harness/deerflow/client.py)
- [backend/app/gateway/app.py](../backend/app/gateway/app.py)
- [frontend/src/app/page.tsx](../frontend/src/app/page.tsx)
- [frontend/src/app/workspace/page.tsx](../frontend/src/app/workspace/page.tsx)

这几处会让你清楚看到：

- 它有独立 Web 应用
- 也有 API
- 也有嵌入式 client
- 根路径和工作区是分开的

## 10. 如果你想把它改得更像 Codex / Claude Code，改造方向是什么

基于当前仓库，我认为最现实的方向是：

1. 保留 DeerFlow 的 runtime、skills、subagents、sandbox、memory
2. 用 `DeerFlowClient` 做一个你自己的本地 CLI 或 IDE 插件外壳
3. 明确开启适合开发场景的文件工具、bash、ACP agents
4. 把工作区默认入口从 Landing 改成 `/workspace`
5. 做更强的 repo-aware prompt、diff review、test loop 和权限策略

这部分是基于当前架构给出的工程建议，不是仓库已有功能承诺。  
但从代码结构看，DeerFlow 是有能力往这个方向长的。来源：[client.py](../backend/packages/harness/deerflow/client.py)、[tools.py](../backend/packages/harness/deerflow/tools/tools.py)、[sandbox/tools.py](../backend/packages/harness/deerflow/sandbox/tools.py)、[task_tool.py](../backend/packages/harness/deerflow/tools/builtins/task_tool.py)

## 11. 来源索引

核心文档：

- [README.md](../README.md)
- [backend/docs/ARCHITECTURE.md](../backend/docs/ARCHITECTURE.md)
- [backend/docs/CONFIGURATION.md](../backend/docs/CONFIGURATION.md)
- [backend/CLAUDE.md](../backend/CLAUDE.md)

关键入口与核心实现：

- [Makefile](../Makefile)
- [backend/langgraph.json](../backend/langgraph.json)
- [backend/packages/harness/deerflow/agents/lead_agent/agent.py](../backend/packages/harness/deerflow/agents/lead_agent/agent.py)
- [backend/packages/harness/deerflow/agents/lead_agent/prompt.py](../backend/packages/harness/deerflow/agents/lead_agent/prompt.py)
- [backend/packages/harness/deerflow/agents/thread_state.py](../backend/packages/harness/deerflow/agents/thread_state.py)
- [backend/packages/harness/deerflow/models/factory.py](../backend/packages/harness/deerflow/models/factory.py)
- [backend/packages/harness/deerflow/tools/tools.py](../backend/packages/harness/deerflow/tools/tools.py)
- [backend/packages/harness/deerflow/sandbox/tools.py](../backend/packages/harness/deerflow/sandbox/tools.py)
- [backend/packages/harness/deerflow/tools/builtins/task_tool.py](../backend/packages/harness/deerflow/tools/builtins/task_tool.py)
- [backend/packages/harness/deerflow/subagents/executor.py](../backend/packages/harness/deerflow/subagents/executor.py)
- [backend/packages/harness/deerflow/subagents/registry.py](../backend/packages/harness/deerflow/subagents/registry.py)
- [backend/packages/harness/deerflow/config/acp_config.py](../backend/packages/harness/deerflow/config/acp_config.py)
- [backend/packages/harness/deerflow/client.py](../backend/packages/harness/deerflow/client.py)
- [backend/app/gateway/app.py](../backend/app/gateway/app.py)

前端入口：

- [frontend/src/app/page.tsx](../frontend/src/app/page.tsx)
- [frontend/src/app/workspace/page.tsx](../frontend/src/app/workspace/page.tsx)
- [frontend/src/app/workspace/layout.tsx](../frontend/src/app/workspace/layout.tsx)
- [frontend/package.json](../frontend/package.json)

技能目录：

- [skills/public](../skills/public)
