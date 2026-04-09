先给结论：

在 DeerFlow 里，`ThreadState` 不是“聊天记录容器”，而是**线程级运行时命名空间**。  
`message` 是给模型看的当前上下文，`state` 是给运行时和工具协同用的结构化状态，`memory` 是从历史对话里提炼出来、供未来回合复用的长期知识。三者会互相投影，但职责不同。

**1. ThreadState 到底是什么**
[thread_state.py](D:/Code/Project/deer-flow-fork/backend/packages/harness/deerflow/agents/thread_state.py#L48) 里的 `ThreadState` 继承自 LangChain 的 [AgentState](D:/Code/Project/deer-flow-fork/backend/.venv/Lib/site-packages/langchain/agents/middleware/types.py#L305)。基类已经自带：

- `messages`：主消息流
- `jump_to`：LangGraph 控制流跳转
- `structured_response`：结构化输出

DeerFlow 在此基础上加了这些线程级字段：

- `sandbox`：当前线程绑定的 sandbox 信息。来源是 [sandbox/middleware.py](D:/Code/Project/deer-flow-fork/backend/packages/harness/deerflow/sandbox/middleware.py#L14)。
- `thread_data`：线程自己的 `workspace/uploads/outputs` 路径。来源是 [thread_data_middleware.py](D:/Code/Project/deer-flow-fork/backend/packages/harness/deerflow/agents/middlewares/thread_data_middleware.py#L15)。
- `title`：线程标题，主要给 UI 用。来源是 [title_middleware.py](D:/Code/Project/deer-flow-fork/backend/packages/harness/deerflow/agents/middlewares/title_middleware.py#L14)。
- `artifacts`：要展示给用户的输出文件列表。`present_file_tool` 会写它，见 [present_file_tool.py](D:/Code/Project/deer-flow-fork/backend/packages/harness/deerflow/tools/builtins/present_file_tool.py)。
- `todos`：计划模式下的任务列表。它主要来自 LangChain 的 `TodoListMiddleware`，DeerFlow 的 [todo_middleware.py](D:/Code/Project/deer-flow-fork/backend/packages/harness/deerflow/agents/middlewares/todo_middleware.py#L47) 负责补救上下文丢失。
- `uploaded_files`：本轮新上传文件的结构化元数据。由 [uploads_middleware.py](D:/Code/Project/deer-flow-fork/backend/packages/harness/deerflow/agents/middlewares/uploads_middleware.py#L187) 写入。
- `viewed_images`：已经读取过的图片内容，保存 `base64 + mime_type`。由 [view_image_tool.py](D:/Code/Project/deer-flow-fork/backend/packages/harness/deerflow/tools/builtins/view_image_tool.py) 写入。

它的“权能”主要体现在四件事：

- 它是 **middleware 和 tools 的共享协作面**。例如 `present_file_tool` 读取 `thread_data.outputs_path` 做路径校验，[present_file_tool.py](D:/Code/Project/deer-flow-fork/backend/packages/harness/deerflow/tools/builtins/present_file_tool.py)。
- 它是 **跨回合状态承载面**。`make_lead_agent()` 把它作为 `state_schema` 传给 agent，见 [agent.py](D:/Code/Project/deer-flow-fork/backend/packages/harness/deerflow/agents/lead_agent/agent.py#L344)。
- 它是 **线程隔离面**。`run_agent()` 会把 `thread_id` 注入 runtime，上层中间件再据此解析线程目录和 sandbox，见 [worker.py](D:/Code/Project/deer-flow-fork/backend/packages/harness/deerflow/runtime/runs/worker.py#L90)。
- 它是 **状态源，而不是 prompt 本身**。除 `messages` 外，其他 state 字段默认模型看不见，必须由中间件主动投影成 message 或 prompt。

**2. State 在中间件里怎么用**
最关键的是 [agent.py](D:/Code/Project/deer-flow-fork/backend/packages/harness/deerflow/agents/lead_agent/agent.py#L208) 的 middleware 链。它不是“大家都改 message”，而是很多 middleware 在读写 `state`。

按生命周期看：

- `before_agent`
  - `ThreadDataMiddleware` 根据 `thread_id` 写入 `thread_data`，[thread_data_middleware.py](D:/Code/Project/deer-flow-fork/backend/packages/harness/deerflow/agents/middlewares/thread_data_middleware.py#L77)。
  - `UploadsMiddleware` 扫描上传目录，把本轮新文件写入 `uploaded_files`，同时把 `<uploaded_files>` 文本块塞进最后一条 `HumanMessage`，[uploads_middleware.py](D:/Code/Project/deer-flow-fork/backend/packages/harness/deerflow/agents/middlewares/uploads_middleware.py#L205)。
  - `SandboxMiddleware` 负责给线程绑定 `sandbox`，[sandbox/middleware.py](D:/Code/Project/deer-flow-fork/backend/packages/harness/deerflow/sandbox/middleware.py#L51)。

- `before_model`
  - `TodoMiddleware` 先看 `state.todos`，如果 todo 还在但历史消息里原始 `write_todos` 调用已经被 summary 挤掉，就补一条提醒消息，[todo_middleware.py](D:/Code/Project/deer-flow-fork/backend/packages/harness/deerflow/agents/middlewares/todo_middleware.py#L58)。
  - `ViewImageMiddleware` 读取 `state.viewed_images`，并检查相关 `ToolMessage` 是否都完成；满足条件后再把图片投影成一条新的 `HumanMessage` 给模型看，[view_image_middleware.py](D:/Code/Project/deer-flow-fork/backend/packages/harness/deerflow/agents/middlewares/view_image_middleware.py#L94)。

- `after_model`
  - `TitleMiddleware` 读取 `state.messages`，在首轮对话后生成并写回 `title`，[title_middleware.py](D:/Code/Project/deer-flow-fork/backend/packages/harness/deerflow/agents/middlewares/title_middleware.py#L46)。
  - `TokenUsageMiddleware` 只读最后一条 AI message 的 `usage_metadata`，不改 state，[token_usage_middleware.py](D:/Code/Project/deer-flow-fork/backend/packages/harness/deerflow/agents/middlewares/token_usage_middleware.py)。

- `after_agent`
  - `MemoryMiddleware` 读取 `state.messages`，做过滤后把结果送进 memory queue，但**不把 memory 写回 ThreadState**，[memory_middleware.py](D:/Code/Project/deer-flow-fork/backend/packages/harness/deerflow/agents/middlewares/memory_middleware.py#L196)。

这里最关键的模式是：

- `state` 经常是**结构化源数据**
- `message` 经常是**投影给模型看的版本**

最典型的两个例子：

- 上传文件：结构化信息进 `uploaded_files`，模型真正看到的是 `<uploaded_files>...</uploaded_files>` 文本块。
- 图片：二进制/元数据进 `viewed_images`，模型真正看到的是后续注入的 `HumanMessage + image_url` blocks。

**3. `message / state / memory` 的边界**
可以把三者理解成三层：

- `message`
  - 形式：`HumanMessage / AIMessage / ToolMessage`
  - 作用：当前回合给模型和工具链看的“会话事实”
  - 生命周期：跟随线程消息流，可能被 summarization 截断
  - 合并规则：`messages` 使用 LangGraph 的 `add_messages` reducer，默认 append-only，同 ID 才替换，见 [message.py](D:/Code/Project/deer-flow-fork/backend/.venv/Lib/site-packages/langgraph/graph/message.py#L61)
  - 适合放：模型此刻必须直接看到的内容
  - 不适合放：纯运行时元数据、长期偏好、线程目录路径

- `state`
  - 形式：`ThreadState` 里的结构化字段
  - 作用：运行时、middleware、tool 之间的共享状态
  - 生命周期：跟线程走；是否持久化取决于 checkpointer
  - 可见性：默认模型看不见，除非某个 middleware 把它投影到 message 或 prompt
  - 适合放：路径、sandbox、todo、artifacts、图片缓存、线程标题
  - 不适合放：面向长期复用的抽象知识总结

- `memory`
  - 形式：独立存储里的 memory data，不在 `ThreadState` 里
  - 作用：跨回合、甚至跨线程复用的长期知识
  - 生命周期：独立于当前线程消息流；由 memory storage 持久化
  - 写入方式：`MemoryMiddleware -> MemoryUpdateQueue -> MemoryUpdater`
  - 读取方式：在 system prompt 生成时由 `_get_memory_context()` 注入 `<memory>...</memory>`，见 [prompt.py](D:/Code/Project/deer-flow-fork/backend/packages/harness/deerflow/agents/lead_agent/prompt.py#L384)
  - 适合放：用户偏好、稳定约束、项目背景、经确认的方法偏好
  - 不适合放：当前回合的精确消息历史、线程目录、临时上传文件事件

**4. 你可以直接拿来判断的规则**
如果一条信息：

- 必须让模型这轮立即看到，用 `message`
- 必须让运行时/工具/中间件协同使用，用 `state`
- 必须让未来回合以“摘要知识”形式继续利用，用 `memory`

再具体一点：

- `/mnt/user-data/outputs/report.md` 这种路径，放 `state.thread_data`，不要放 memory。
- “用户刚上传了这 3 个文件”，本轮通过 message 注入给模型，但不要进入长期 memory。
- “用户偏好先给结论、再给细节”，适合进入 memory，不必每轮都靠 message 重述。
- “当前 todo 进度”是 state；当 message 窗口丢了原始调用时，再由 middleware 临时投影回 message。

**5. 你现在读源码时最该抓住的一句话**
DeerFlow 里最容易混淆的不是“哪个字段叫什么”，而是：

**state 是运行时真相，message 是给模型看的投影，memory 是给未来回合看的压缩知识。**