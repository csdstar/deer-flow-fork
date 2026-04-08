# DeerFlow 二次开发与改造指南（中文）

> 本文聚焦 DeerFlow 的二次开发切入点、扩展方式、能力边界，以及如何把它往“更像本地开发助手”的方向推进。  
> 如果你先想看系统结构本身，请先读 [deerflow-architecture-overview.zh-CN.md](./deerflow-architecture-overview.zh-CN.md)。  
> 完整版总说明仍保留在 [deerflow-repository-manual.zh-CN.md](./deerflow-repository-manual.zh-CN.md)。

## 1. 先回答核心问题

### 1.1 DeerFlow 能不能像 Codex / Claude Code 一样做本地开发工作

答案是：**能做很大一部分，但默认形态并不是现成的终端型 coding assistant 产品。**

它已经具备这些关键能力：

- 文件读写与目录浏览：`read_file`、`write_file`、`str_replace`、`ls`
- 命令执行：`bash`
- 子代理任务拆分：`task`
- 线程级工作区、上传目录、输出目录
- skills 驱动的高层工作流
- MCP 工具扩展
- ACP agent 接入
- Embedded Python Client
- 可直接使用 Codex / Claude Code 作为模型提供方

来源：[README](../README.md)、[backend/docs/CONFIGURATION.md](../backend/docs/CONFIGURATION.md)、[backend/packages/harness/deerflow/tools/tools.py](../backend/packages/harness/deerflow/tools/tools.py)、[backend/packages/harness/deerflow/client.py](../backend/packages/harness/deerflow/client.py)

但它当前不是：

- 一个官方主打的终端 CLI 产品
- 一个类似 `codex` / `claude` 的单命令交互式开发工具
- 一个默认打开就以“本地仓库开发”为中心的产品入口

来源：[README](../README.md)、[Makefile](../Makefile)、[backend/packages/harness/pyproject.toml](../backend/packages/harness/pyproject.toml)、[frontend/src/app/page.tsx](../frontend/src/app/page.tsx)

### 1.2 最准确的工程理解

DeerFlow 更适合被理解为：

**一个可运行、可嵌入、可扩展的 agent harness，你可以把它继续包成更像 Codex / Claude Code 的工具，而不是它天然就已经等价于它们。**

## 2. 当前仓库中，哪些能力最适合二次开发

### 2.1 模型接入与模型能力开关

模型定义来自 `config.yaml`，由 `create_chat_model()` 统一实例化。你可以通过 `use:` 字段接入：

- LangChain 标准 provider
- OpenAI-compatible provider
- Anthropic-compatible provider
- Codex CLI provider
- Claude Code provider
- vLLM provider

而 thinking、vision、reasoning effort 等能力，则由配置与模型工厂共同决定。来源：[backend/docs/CONFIGURATION.md](../backend/docs/CONFIGURATION.md)、[backend/packages/harness/deerflow/models/factory.py](../backend/packages/harness/deerflow/models/factory.py)

这意味着模型侧扩展的主入口通常不是改 agent，而是：

1. 配 `config.yaml`
2. 必要时新增 provider 实现
3. 在工厂中处理 provider 差异

### 2.2 工具扩展

工具系统是 DeerFlow 最直接的扩展点之一。`get_available_tools()` 会把多个来源的工具合并起来：

- `config.yaml` 里的显式工具
- 内置工具
- MCP 工具
- ACP 工具
- 子代理工具

来源：[backend/packages/harness/deerflow/tools/tools.py](../backend/packages/harness/deerflow/tools/tools.py)

如果你要扩展“开发相关能力”，通常可以选三条路：

- 新增 Python tool，并在 `config.yaml` 中注册
- 通过 MCP 把外部系统能力接进来
- 通过 ACP 把外部 agent 当工具挂进来

### 2.3 Skills 扩展

如果你想扩展的不是单一能力，而是一套工作流，比如：

- code review
- refactor workflow
- repo onboarding
- PR triage
- test failure diagnosis

那更适合做成 skill，而不是只做成一个工具。

DeerFlow 的 skill 以 `SKILL.md` 为主，系统提示词会引导 agent 在任务匹配时按需读取对应 skill，而不是一开始把所有 skill 内容塞进上下文。来源：[backend/packages/harness/deerflow/agents/lead_agent/prompt.py](../backend/packages/harness/deerflow/agents/lead_agent/prompt.py)、[skills/public](../skills/public)

这使得 skill 非常适合沉淀“复杂但可复用”的开发流程经验。

### 2.4 Sandbox 与文件系统行为

对于本地开发工作来说，sandbox 是关键基础设施。

DeerFlow 当前的沙箱体系至少支持：

- `LocalSandboxProvider`
- `AioSandboxProvider`

本地模式更方便开发调试，容器模式更适合安全隔离。项目也明确说明 host bash 默认关闭，因为本地 host bash 不是安全边界。来源：[README](../README.md)、[backend/docs/CONFIGURATION.md](../backend/docs/CONFIGURATION.md)

如果你要把 DeerFlow 用成更强的本地开发助手，这一层往往是最需要认真设计权限策略的地方。

### 2.5 Subagents

如果你研究的是复杂任务拆解、并行调度或“多工种协作式开发”，那子代理就是最值得看的部分。

子代理当前通过：

- `task` 工具发起
- `SubagentExecutor` 在后台执行
- `SubagentLimitMiddleware` 限制并发

来实现。来源：[backend/packages/harness/deerflow/tools/builtins/task_tool.py](../backend/packages/harness/deerflow/tools/builtins/task_tool.py)、[backend/packages/harness/deerflow/subagents/executor.py](../backend/packages/harness/deerflow/subagents/executor.py)、[backend/packages/harness/deerflow/agents/lead_agent/agent.py](../backend/packages/harness/deerflow/agents/lead_agent/agent.py)

### 2.6 Embedded Client

如果你的目标是“做自己的 CLI / IDE 插件 / 自动化工具”，`DeerFlowClient` 是非常重要的切入点。

它允许你在本地 Python 进程里直接：

- 发起聊天
- 获取流式事件
- 查模型 / 技能 / MCP
- 管理上传与 artifacts

而不必先搭一层 HTTP 服务。来源：[backend/packages/harness/deerflow/client.py](../backend/packages/harness/deerflow/client.py)、[backend/CLAUDE.md](../backend/CLAUDE.md)

## 3. 如果你想把 DeerFlow 改得更像本地开发助手，建议怎么做

下面这部分不是仓库“已经提供的功能列表”，而是基于现有结构给出的改造建议。

### 3.1 先决定你要模仿的是哪一种产品形态

“像 Codex / Claude Code”其实可能有三种不同含义：

- 像终端型 CLI：单命令进入、以当前仓库为上下文、专注本地开发
- 像 IDE 助手：侧重编辑器集成、diff、测试、补全、工作区操作
- 像多代理开发平台：强调任务分解、长任务、工具编排和产物输出

DeerFlow 现成基础最强的是第三种，其次才是第一种。来源：[README](../README.md)、[backend/CLAUDE.md](../backend/CLAUDE.md)

### 3.2 最现实的一条改造路径

如果你要做一个偏本地开发的产品形态，比较现实的路径是：

1. 保留 DeerFlow 的 runtime、skills、sandbox、subagents、memory
2. 用 `DeerFlowClient` 包一层你自己的 CLI 或 IDE bridge
3. 针对代码工作补充专门的 skill 和 tool
4. 重新设计默认入口，而不是让用户先落到 Landing Page
5. 明确本地执行权限与风险边界

来源：[backend/packages/harness/deerflow/client.py](../backend/packages/harness/deerflow/client.py)、[frontend/src/app/page.tsx](../frontend/src/app/page.tsx)

### 3.3 具体改造点

如果是做 CLI / 开发助手，优先级最高的通常是这些：

- **入口改造**：增加一个真正的 CLI 外壳，而不是只靠 `make dev` 启 Web UI
- **默认上下文改造**：把当前仓库、git 状态、工作目录、测试命令变成一等上下文
- **工具约束改造**：对 `bash`、文件写入、删除操作做更细的权限控制
- **开发技能沉淀**：把 repo onboarding、test-fix loop、review workflow 做成 skills
- **子代理策略改造**：让探索、实现、验证等任务以不同子代理模式运行
- **产物与 diff 展示改造**：让结果更偏向 patch、变更摘要、测试结果，而不只是一般文本答复

这些方向都可以在现有架构上继续长，而不需要推翻整个仓库。来源：[backend/packages/harness/deerflow/tools/tools.py](../backend/packages/harness/deerflow/tools/tools.py)、[backend/packages/harness/deerflow/sandbox/tools.py](../backend/packages/harness/deerflow/sandbox/tools.py)、[backend/packages/harness/deerflow/tools/builtins/task_tool.py](../backend/packages/harness/deerflow/tools/builtins/task_tool.py)

## 4. 推荐的源码阅读顺序

### 4.1 第一层：先建立全局认知

先读：

1. [README.md](../README.md)
2. [backend/docs/ARCHITECTURE.md](../backend/docs/ARCHITECTURE.md)
3. [backend/docs/CONFIGURATION.md](../backend/docs/CONFIGURATION.md)
4. [backend/CLAUDE.md](../backend/CLAUDE.md)

### 4.2 第二层：看核心运行链

接着读：

1. [backend/langgraph.json](../backend/langgraph.json)
2. [backend/packages/harness/deerflow/agents/lead_agent/agent.py](../backend/packages/harness/deerflow/agents/lead_agent/agent.py)
3. [backend/packages/harness/deerflow/agents/lead_agent/prompt.py](../backend/packages/harness/deerflow/agents/lead_agent/prompt.py)
4. [backend/packages/harness/deerflow/agents/thread_state.py](../backend/packages/harness/deerflow/agents/thread_state.py)

### 4.3 第三层：看最关键的扩展点

如果你主要关心本地开发、工具扩展或产品改造，优先读：

1. [backend/packages/harness/deerflow/models/factory.py](../backend/packages/harness/deerflow/models/factory.py)
2. [backend/packages/harness/deerflow/tools/tools.py](../backend/packages/harness/deerflow/tools/tools.py)
3. [backend/packages/harness/deerflow/sandbox/tools.py](../backend/packages/harness/deerflow/sandbox/tools.py)
4. [backend/packages/harness/deerflow/tools/builtins/task_tool.py](../backend/packages/harness/deerflow/tools/builtins/task_tool.py)
5. [backend/packages/harness/deerflow/subagents/executor.py](../backend/packages/harness/deerflow/subagents/executor.py)
6. [backend/packages/harness/deerflow/config/acp_config.py](../backend/packages/harness/deerflow/config/acp_config.py)
7. [backend/packages/harness/deerflow/client.py](../backend/packages/harness/deerflow/client.py)

### 4.4 第四层：如果你还关心前端

前端这几处最值得先看：

1. [frontend/src/app/page.tsx](../frontend/src/app/page.tsx)
2. [frontend/src/app/workspace/page.tsx](../frontend/src/app/workspace/page.tsx)
3. [frontend/src/app/workspace/layout.tsx](../frontend/src/app/workspace/layout.tsx)
4. [frontend/package.json](../frontend/package.json)

它们能帮你快速区分：

- Landing Page
- 工作区入口
- 工作区布局壳
- 前端技术栈与依赖

## 5. 哪些目录最值得长期跟踪

如果你准备持续研究或长期二开，建议重点盯这些目录：

- `backend/packages/harness/deerflow/agents/`
- `backend/packages/harness/deerflow/tools/`
- `backend/packages/harness/deerflow/sandbox/`
- `backend/packages/harness/deerflow/subagents/`
- `backend/packages/harness/deerflow/models/`
- `backend/packages/harness/deerflow/skills/`
- `backend/packages/harness/deerflow/mcp/`
- `backend/packages/harness/deerflow/runtime/`
- `backend/app/gateway/`
- `frontend/src/app/workspace/`
- `skills/public/`

这些目录基本就覆盖了 DeerFlow 从 runtime 到应用层的主要变化面。来源：[backend](../backend)、[frontend/src/app/workspace](../frontend/src/app/workspace)、[skills/public](../skills/public)

## 6. 哪些部分最可能成为你之后的研究重点

如果你的目标是“用它做本地开发工作”而不只是体验一下，我认为最值得深挖的是：

- `DeerFlowClient`：因为这是你做 CLI / IDE 集成最自然的起点
- `tools + sandbox`：因为本地开发能力最终落在文件与命令执行
- `task + subagents`：因为复杂开发任务会天然走向拆解和并行
- `skills`：因为开发流程的复用与固化很适合沉淀成 skill
- `ACP`：因为你很可能想把别的 agent 或外部执行器编进 DeerFlow

这些方向不是互斥的，反而很适合组合起来研究。来源：[backend/packages/harness/deerflow/client.py](../backend/packages/harness/deerflow/client.py)、[backend/packages/harness/deerflow/tools/tools.py](../backend/packages/harness/deerflow/tools/tools.py)、[backend/packages/harness/deerflow/tools/builtins/task_tool.py](../backend/packages/harness/deerflow/tools/builtins/task_tool.py)、[skills/public](../skills/public)

## 7. 一个务实的研究路线

如果你想边学边改，建议按这个顺序推进：

1. 先跑通 Web 版和你自己的模型配置
2. 再读 lead agent、tools、sandbox、subagents 主链
3. 选一个小的开发工作流做成 skill
4. 再试着用 `DeerFlowClient` 包一个最小 CLI
5. 最后再决定是否要深改前端、权限策略和 ACP 集成

这条路线的好处是：你会先掌握 DeerFlow 的“原生工作方式”，然后再决定哪里需要改造成你想要的样子。

