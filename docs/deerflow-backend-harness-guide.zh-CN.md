# DeerFlow 后端 Harness 说明

Calibration Level: INTERMEDIATE（中级开发者）

本文档面向准备基于本仓库设计 harness 相关论文实验的开发者。  
重点不是教你如何启动项目，而是回答两个问题：

- DeerFlow 后端的 harness 到底由哪些层组成。
- 每一层在仓库里对应哪些实现文件，适合做什么实验改造。

## 1. 先给结论：DeerFlow 的后端不是“一个 agent”

如果只看最核心的 agent 调用，DeerFlow 仍然基于 LangChain / LangGraph 的 `create_agent(...)` 工作，入口在 [agent.py](../backend/packages/harness/deerflow/agents/lead_agent/agent.py)。

因此，DeerFlow 的价值不在“提出了新的推理算法”，而在“把 agent 的后端运行面拆成了可配置、可治理、可扩展的 harness”。

对论文实验来说，这意味着你更应该把 DeerFlow 视为：

- 一个分层的 agent runtime
- 一个 orchestration（编排）系统
- 一个能力装配与执行平台
- 一个带状态、线程、流式事件和恢复能力的后端底座

## 2. 按五层理解 DeerFlow 后端

下面采用你已经整理出的五层分层，并用 DeerFlow 的实际实现文件去对齐。

### 2.1 协议与适配层

这一层解决“如何把不同模型、工具、配置和 provider 接到统一接口上”。

对应实现：

- [app_config.py](../backend/packages/harness/deerflow/config/app_config.py)
- [factory.py](../backend/packages/harness/deerflow/models/factory.py)
- [tools.py](../backend/packages/harness/deerflow/tools/tools.py)
- `deerflow/reflection/*`

这一层的关键职责有三项：

1. 统一配置入口  
   `AppConfig` 从 `config.yaml` 读取模型、工具、sandbox、memory、subagents、guardrails 等配置，并做环境变量展开。

2. 统一模型接口  
   [factory.py](../backend/packages/harness/deerflow/models/factory.py) 把配置中的 `use` 类路径解析为具体的 `BaseChatModel` 实现，并统一处理：
   - `thinking_enabled`
   - `reasoning_effort`
   - tracing callbacks
   - 针对不同 provider 的参数修正

3. 统一工具接口  
   [tools.py](../backend/packages/harness/deerflow/tools/tools.py) 负责把配置中的工具、built-in tools、MCP tools、ACP tools 统一组装成 agent 可见的 `BaseTool` 列表。

这一层更像“适配器层”，而不是模型推理 runtime 本身。  
DeerFlow 不负责像 vLLM 那样真正承载模型推理服务；它负责把外部 provider 和内部 agent 运行时接起来。

### 2.2 运行时与环境层

这一层解决“任务在哪个状态空间里运行，如何保持线程隔离、流式执行、可恢复和可取消”。

对应实现：

- [thread_state.py](../backend/packages/harness/deerflow/agents/thread_state.py)
- [worker.py](../backend/packages/harness/deerflow/runtime/runs/worker.py)
- [app.py](../backend/app/gateway/app.py)
- [middleware.py](../backend/packages/harness/deerflow/sandbox/middleware.py)
- [thread_data_middleware.py](../backend/packages/harness/deerflow/agents/middlewares/thread_data_middleware.py)
- [uploads_middleware.py](../backend/packages/harness/deerflow/agents/middlewares/uploads_middleware.py)
- [checkpointer_config.py](../backend/packages/harness/deerflow/config/checkpointer_config.py)

这一层的关键对象有：

- `thread`  
  DeerFlow 的 thread 不只是 message history。它还带有：
  - `sandbox`
  - `thread_data`
  - `artifacts`
  - `uploaded_files`
  - `viewed_images`
  - `todos`

- `run`  
  一次具体执行会被包装成 `run`，由 [worker.py](../backend/packages/harness/deerflow/runtime/runs/worker.py) 负责：
  - 注入 runtime context
  - 绑定 checkpointer / store
  - 执行 agent graph
  - 推送 stream 事件
  - 处理 cancel / interrupt / rollback

- `sandbox`  
  [middleware.py](../backend/packages/harness/deerflow/sandbox/middleware.py) 负责把线程和 sandbox provider 绑定起来。

- `thread-local filesystem`  
  [thread_data_middleware.py](../backend/packages/harness/deerflow/agents/middlewares/thread_data_middleware.py) 给每个线程计算：
  - workspace
  - uploads
  - outputs

这一层通常不是论文里最适合直接改造的对象，但它是实验成立的基础设施。  
如果你要做可复现实验，必须依赖这一层来保证：

- 线程隔离
- 输入输出路径稳定
- 状态可追踪
- run 可回放

### 2.3 编排层

这一层解决“谁来做、何时做、调用什么、失败后怎么处理”。

对应实现：

- [agent.py](../backend/packages/harness/deerflow/agents/lead_agent/agent.py)
- [prompt.py](../backend/packages/harness/deerflow/agents/lead_agent/prompt.py)
- `backend/packages/harness/deerflow/agents/middlewares/*`
- [executor.py](../backend/packages/harness/deerflow/subagents/executor.py)
- [task_tool.py](../backend/packages/harness/deerflow/tools/builtins/task_tool.py)

这层是 DeerFlow 后端最核心的 harness 层。

#### Lead agent 装配

[agent.py](../backend/packages/harness/deerflow/agents/lead_agent/agent.py) 负责：

- 解析当前 run 的模型选择
- 判断是否开启 thinking
- 判断是否开启 subagent
- 判断是否进入 plan mode
- 装配 tools
- 装配 middleware
- 生成 system prompt
- 调用 `create_agent(...)`

这里是最典型的实验入口。  
如果你要做 harness 论文实验，这通常是第一个该读、也是第一个该改的文件。

#### Prompt 编排

[prompt.py](../backend/packages/harness/deerflow/agents/lead_agent/prompt.py) 不是一份普通 system prompt。  
它是一个“prompt 组合器”，会把这些信息拼进去：

- 角色与 SOUL
- memory context
- skills section
- deferred tools section
- subagent section
- clarification 规则
- working directory 约定

也就是说，DeerFlow 的 prompt 不是静态文本，而是运行时策略的一部分。

#### Middleware 编排

middleware 是 DeerFlow 编排层最重要的技术手段。  
它们把 agent 生命周期切成多个钩子，例如：

- `before_agent`
- `wrap_model_call`
- `before_model`
- `wrap_tool_call`
- `after_model`
- `after_agent`

代表性 middleware 包括：

- [llm_error_handling_middleware.py](../backend/packages/harness/deerflow/agents/middlewares/llm_error_handling_middleware.py)
- [tool_error_handling_middleware.py](../backend/packages/harness/deerflow/agents/middlewares/tool_error_handling_middleware.py)
- [clarification_middleware.py](../backend/packages/harness/deerflow/agents/middlewares/clarification_middleware.py)
- [loop_detection_middleware.py](../backend/packages/harness/deerflow/agents/middlewares/loop_detection_middleware.py)
- [subagent_limit_middleware.py](../backend/packages/harness/deerflow/agents/middlewares/subagent_limit_middleware.py)

如果你研究的是“harness 如何诊断和修复 agent 行为”，middleware 链就是最优入口。

#### 子代理编排

DeerFlow 支持 lead agent 调度 subagent，但它不是一个抽象概念，而是由两层实现支撑：

- [task_tool.py](../backend/packages/harness/deerflow/tools/builtins/task_tool.py)  
  暴露给 lead agent 的 `task` 工具。它负责触发后台子代理任务并轮询结果。

- [executor.py](../backend/packages/harness/deerflow/subagents/executor.py)  
  真正创建并执行子代理，维护状态、线程池、超时、结果收集。

对实验来说，这一层适合做：

- 子代理开关实验
- 并发上限实验
- 调度策略实验
- 单代理 vs 多代理收益对比实验

### 2.4 能力扩展层

这一层解决“agent 到底能做什么”。

对应实现：

- [tools.py](../backend/packages/harness/deerflow/tools/tools.py)
- [cache.py](../backend/packages/harness/deerflow/mcp/cache.py)
- `backend/packages/harness/deerflow/tools/builtins/*`
- `backend/packages/harness/deerflow/skills/*`
- `backend/packages/harness/deerflow/agents/memory/*`

这一层包括四类能力来源。

#### 内置能力

例如：

- `ask_clarification`
- `present_file`
- `task`
- `view_image`

这些 built-in tools 是 DeerFlow 自带的基础操作面。

#### 配置化工具

[tools.py](../backend/packages/harness/deerflow/tools/tools.py) 会把 `config.yaml` 中配置的工具组装进来。  
这让能力扩展不必改 agent 主体逻辑。

#### MCP 工具

MCP 工具的缓存与懒加载在 [cache.py](../backend/packages/harness/deerflow/mcp/cache.py)。  
DeerFlow 支持：

- 启动时初始化
- 缓存工具
- 监听配置变化后失效重载
- 配合 `tool_search` 做 deferred tool 暴露

这部分对“能力扩展如何影响 agent 行为”的实验很有价值。

#### Skills 与 Memory

虽然它们不一定表现为普通 `tool`，但从 harness 角度看，它们属于“能力增强层”：

- skills 提供结构化工作流知识
- memory 提供持久化上下文与偏好

相关实现：

- [memory_middleware.py](../backend/packages/harness/deerflow/agents/middlewares/memory_middleware.py)
- [updater.py](../backend/packages/harness/deerflow/agents/memory/updater.py)

### 2.5 产品与集成层

这一层解决“后端如何暴露给前端、API、嵌入式调用和渠道集成”。

对应实现：

- [app.py](../backend/app/gateway/app.py)
- `backend/app/gateway/routers/*`
- [client.py](../backend/packages/harness/deerflow/client.py)
- [service.py](../backend/app/channels/service.py)

DeerFlow 在这层不是 CLI-first，而是更偏：

- Web workspace
- FastAPI Gateway
- Embedded Python client
- IM channels

#### Gateway

[app.py](../backend/app/gateway/app.py) 是后端网关入口。  
它负责：

- 启动 FastAPI
- 初始化 LangGraph runtime
- 注册各类 API router
- 启动 channel service

#### Router 层

`backend/app/gateway/routers/*` 提供模型、技能、memory、uploads、threads、runs 等 API。  
这一层是产品化接口，而不是 harness 核心逻辑本身。

#### Embedded Client

[client.py](../backend/packages/harness/deerflow/client.py) 提供“嵌入式 Python 调用”能力。  
如果你要做批量实验或离线实验，这个入口可能比前端和 Gateway 更方便。

#### 渠道集成

[service.py](../backend/app/channels/service.py) 管理 Slack、Telegram、Feishu、WeCom 等渠道。  
这属于产品集成层，通常不是 harness 论文实验的主战场。

## 3. 一次请求如何穿过这五层

理解后端最有效的方法，不是背目录，而是跟着一次请求走。

一个典型请求的大致路径如下：

1. 前端或客户端发起请求  
   Web 前端通过 Gateway API，嵌入式调用可直接走 [client.py](../backend/packages/harness/deerflow/client.py)。

2. Gateway 接收请求  
   [app.py](../backend/app/gateway/app.py) 初始化的 FastAPI 应用把请求路由到对应 router。

3. runtime 创建 run  
   [worker.py](../backend/packages/harness/deerflow/runtime/runs/worker.py) 负责创建 run、注入 thread context、绑定 checkpointer/store。

4. lead agent 被装配  
   [agent.py](../backend/packages/harness/deerflow/agents/lead_agent/agent.py) 根据 config 和 runtime 参数创建 agent。

5. middleware 链运行  
   线程目录、上传文件、sandbox、tool error handling、clarification、memory、loop detection 等逻辑依次生效。

6. tools / subagents / MCP 被调用  
   [tools.py](../backend/packages/harness/deerflow/tools/tools.py) 决定可见能力；必要时通过 [task_tool.py](../backend/packages/harness/deerflow/tools/builtins/task_tool.py) 进入 subagent。

7. 结果被流式推回  
   [worker.py](../backend/packages/harness/deerflow/runtime/runs/worker.py) 把 `values/messages/custom` 等流式事件推回前端或客户端。

这条链说明：  
DeerFlow 的后端不是单点文件，而是五层协同的系统。

## 4. 对论文实验最重要的文件

如果你的目标是设计 harness 相关实验，不需要把所有后端代码一口气读完。  
优先级建议如下。

### 第一优先级：直接决定实验行为

- [agent.py](../backend/packages/harness/deerflow/agents/lead_agent/agent.py)
- [prompt.py](../backend/packages/harness/deerflow/agents/lead_agent/prompt.py)
- [tool_error_handling_middleware.py](../backend/packages/harness/deerflow/agents/middlewares/tool_error_handling_middleware.py)
- [llm_error_handling_middleware.py](../backend/packages/harness/deerflow/agents/middlewares/llm_error_handling_middleware.py)
- [clarification_middleware.py](../backend/packages/harness/deerflow/agents/middlewares/clarification_middleware.py)
- [loop_detection_middleware.py](../backend/packages/harness/deerflow/agents/middlewares/loop_detection_middleware.py)

这些文件适合做：

- harness 诊断与修复实验
- 中间件干预实验
- orchestration 策略实验

### 第二优先级：多代理与能力扩展

- [task_tool.py](../backend/packages/harness/deerflow/tools/builtins/task_tool.py)
- [executor.py](../backend/packages/harness/deerflow/subagents/executor.py)
- [tools.py](../backend/packages/harness/deerflow/tools/tools.py)
- [cache.py](../backend/packages/harness/deerflow/mcp/cache.py)

这些文件适合做：

- subagent 调度实验
- tool 暴露实验
- MCP 能力扩展实验

### 第三优先级：长期上下文与状态

- [thread_state.py](../backend/packages/harness/deerflow/agents/thread_state.py)
- [memory_middleware.py](../backend/packages/harness/deerflow/agents/middlewares/memory_middleware.py)
- [updater.py](../backend/packages/harness/deerflow/agents/memory/updater.py)
- [checkpointer_config.py](../backend/packages/harness/deerflow/config/checkpointer_config.py)

这些文件适合做：

- memory 注入实验
- thread 状态演化实验
- 可恢复运行实验

### 第四优先级：接口与批量实验入口

- [app.py](../backend/app/gateway/app.py)
- [client.py](../backend/packages/harness/deerflow/client.py)
- `backend/app/gateway/routers/thread_runs.py`

这些文件适合做：

- 批量任务投喂
- 实验数据采集
- 前后端解耦实验

## 5. 如果你要“改 harness”，最推荐改哪里

基于 DeerFlow 当前实现，最适合改造的不是底层 provider 适配层，而是编排层和能力层之间的接口位置。

优先建议：

1. 在 [agent.py](../backend/packages/harness/deerflow/agents/lead_agent/agent.py) 中插入新的实验 middleware  
   这是最稳的入口。

2. 在 [tools.py](../backend/packages/harness/deerflow/tools/tools.py) 中控制工具可见性  
   适合做工具集干预实验。

3. 在 [task_tool.py](../backend/packages/harness/deerflow/tools/builtins/task_tool.py) 和 [executor.py](../backend/packages/harness/deerflow/subagents/executor.py) 中改子代理策略  
   适合做多代理调度实验。

4. 在 [memory_middleware.py](../backend/packages/harness/deerflow/agents/middlewares/memory_middleware.py) 与 [updater.py](../backend/packages/harness/deerflow/agents/memory/updater.py) 中改 memory 写入/注入策略  
   适合做长期上下文实验。

## 6. 不建议优先改哪里

如果你的目标是论文实验，而不是把产品做完，前期不建议优先改这些：

- `frontend/*`
- `gateway` 的大部分产品接口
- provider 适配细节
- Nginx 与服务编排脚本

原因很简单：这些部分会消耗大量工程时间，但不一定提升你的实验有效性。

## 7. 推荐的阅读顺序

如果你要在 1 到 2 天内建立后端 harness 的整体模型，建议按下面顺序读：

1. [agent.py](../backend/packages/harness/deerflow/agents/lead_agent/agent.py)
2. [prompt.py](../backend/packages/harness/deerflow/agents/lead_agent/prompt.py)
3. [tools.py](../backend/packages/harness/deerflow/tools/tools.py)
4. `agents/middlewares/*`
5. [task_tool.py](../backend/packages/harness/deerflow/tools/builtins/task_tool.py)
6. [executor.py](../backend/packages/harness/deerflow/subagents/executor.py)
7. [thread_state.py](../backend/packages/harness/deerflow/agents/thread_state.py)
8. [worker.py](../backend/packages/harness/deerflow/runtime/runs/worker.py)
9. [app.py](../backend/app/gateway/app.py)
10. [client.py](../backend/packages/harness/deerflow/client.py)

这条顺序的好处是：  
你会先理解 harness 的核心控制面，再理解运行时和产品接口，而不是一开始就陷进 API 细节。

## 8. 结语

如果把 DeerFlow 后端浓缩成一句话，可以这样描述：

> DeerFlow 后端不是单一 agent 实现，而是一个分层的 harness：上承模型与工具协议，中间用编排层和能力层组织 agent 行为，下接线程状态、运行时环境和产品接口。

对论文实验来说，真正最有价值的不是“重新发明 agent”，而是利用 DeerFlow 已经拆好的后端层次，去研究：

- 哪些编排策略更好
- 哪些能力暴露方式更有效
- 哪些中间件干预能提升成功率与稳定性
- 哪些 thread/run 级状态会影响最终表现
