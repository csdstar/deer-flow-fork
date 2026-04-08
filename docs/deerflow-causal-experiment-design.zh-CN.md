# DeerFlow 因果化实验设计说明

本文档只回答一个问题：在 DeerFlow 上，哪些部件最适合做“可跑、可测、可对比”的实验，以及每个实验该怎么落地。  
不展开因果理论细节，重点放在工程可行性、实验变量、干预方式、数据采集与评估指标。

适用前提：

- 你已经能本地跑通 DeerFlow
- 你希望以 DeerFlow 为实验底座，而不是从零重写 agent 框架
- 你当前更需要“实验方案”而不是“理论推导”

## 1. 为什么 DeerFlow 适合作为实验底座

DeerFlow 不是一个单点 agent，而是一个把多个决策层显式拼装起来的 harness。  
这意味着它天然适合做“部件级干预”实验。

它的关键特点是：

- lead agent 的创建逻辑是显式的，见 [backend/packages/harness/deerflow/agents/lead_agent/agent.py](../backend/packages/harness/deerflow/agents/lead_agent/agent.py)
- middleware 链是显式的，适合插入自定义实验逻辑，见 [backend/packages/harness/deerflow/agents/middlewares/tool_error_handling_middleware.py](../backend/packages/harness/deerflow/agents/middlewares/tool_error_handling_middleware.py)
- 工具暴露是集中装配的，见 [backend/packages/harness/deerflow/tools/tools.py](../backend/packages/harness/deerflow/tools/tools.py)
- 子代理是单独的执行器与任务工具，见 [backend/packages/harness/deerflow/tools/builtins/task_tool.py](../backend/packages/harness/deerflow/tools/builtins/task_tool.py) 和 [backend/packages/harness/deerflow/subagents/executor.py](../backend/packages/harness/deerflow/subagents/executor.py)
- 线程状态是结构化的，而不只是 message history，见 [backend/packages/harness/deerflow/agents/thread_state.py](../backend/packages/harness/deerflow/agents/thread_state.py)
- memory、guardrail、sandbox audit、clarification 都是独立模块，适合做控制变量实验
- 运行过程有 run / thread / checkpointer / tracing 这些基础设施，便于采集实验数据，见 [backend/packages/harness/deerflow/runtime/runs/worker.py](../backend/packages/harness/deerflow/runtime/runs/worker.py)、[backend/packages/harness/deerflow/config/checkpointer_config.py](../backend/packages/harness/deerflow/config/checkpointer_config.py)、[backend/packages/harness/deerflow/tracing/factory.py](../backend/packages/harness/deerflow/tracing/factory.py)

如果你想做的是“因果化验证与修复”，DeerFlow 的优势不在模型多强，而在于它把很多决策点拆出来了，方便你做：

- `do(tool policy = X)`
- `do(subagent = on/off)`
- `do(memory injection = on/off)`
- `do(clarification first = forced)`
- `do(risky bash blocked = true)`

这比在一个黑盒 agent 上做实验更容易。

## 2. 实验设计总原则

建议把你的实验设计成“部件级干预实验”，而不是一开始就做全系统因果发现。

更稳的做法是：

1. 固定大部分系统设置  
   例如固定模型、固定 prompt 主体、固定工具集，只改一个关键部件。
2. 把某个部件当作可干预变量  
   例如 memory 注入策略、subagent 使用策略、tool 修复策略。
3. 设计对照组和干预组  
   对同一批任务，比较不同策略下的成功率、错误率、时延、token 消耗。
4. 记录中间变量而不只看最终答案  
   例如调用了哪些工具、失败在哪一步、是否触发澄清、是否进入子代理、是否发生重试。

这个思路和 DeerFlow 当前架构是对齐的，因为它本身就已经有“状态”和“中间件链”。

## 3. DeerFlow 中最适合做实验的部件

下面这张表可以直接当作“选题入口表”。

| 部件 | 当前作用 | 适合做的实验 | 为什么适合 | 主要源码入口 |
| --- | --- | --- | --- | --- |
| Lead Agent 装配 | 组装模型、工具、middleware、prompt | 比较不同 runtime 策略 | 是总装配点，改动集中 | [agent.py](../backend/packages/harness/deerflow/agents/lead_agent/agent.py) |
| Middleware 链 | 在模型调用前后、工具调用前后插入控制逻辑 | 因果诊断、干预修复、日志采集 | 插件式，改造成本最低 | [tool_error_handling_middleware.py](../backend/packages/harness/deerflow/agents/middlewares/tool_error_handling_middleware.py) |
| Tool 暴露层 | 决定 LLM 能看见哪些工具 | 工具选择、工具可见性干预 | 能直接控制决策空间 | [tools.py](../backend/packages/harness/deerflow/tools/tools.py) |
| Subagent 机制 | 把任务委托给独立 agent | 多代理调度收益/代价实验 | 变量清晰，易做开关对照 | [task_tool.py](../backend/packages/harness/deerflow/tools/builtins/task_tool.py), [executor.py](../backend/packages/harness/deerflow/subagents/executor.py) |
| Memory 机制 | 持久化和注入历史偏好/事实 | 记忆污染、选择性注入、修复实验 | 最容易做 on/off 和阈值实验 | [memory_middleware.py](../backend/packages/harness/deerflow/agents/middlewares/memory_middleware.py), [updater.py](../backend/packages/harness/deerflow/agents/memory/updater.py) |
| Clarification 机制 | 在不确定时中断并向用户追问 | 先澄清 vs 直接行动实验 | 适合研究错误预防 | [clarification_middleware.py](../backend/packages/harness/deerflow/agents/middlewares/clarification_middleware.py) |
| Guardrail / Sandbox Audit | 在工具执行前做策略检查 | 安全干预、风险修复实验 | 已有规则层，便于扩展 | [middleware.py](../backend/packages/harness/deerflow/guardrails/middleware.py), [sandbox_audit_middleware.py](../backend/packages/harness/deerflow/agents/middlewares/sandbox_audit_middleware.py) |
| Model Factory | 统一创建模型实例并附加 tracing | 模型/推理模式控制实验 | 适合做模型层控制变量 | [factory.py](../backend/packages/harness/deerflow/models/factory.py) |
| Thread / Checkpointer / Run | 保存线程状态与运行事件 | 实验数据采集、复现实验 | 适合做离线分析 | [thread_state.py](../backend/packages/harness/deerflow/agents/thread_state.py), [worker.py](../backend/packages/harness/deerflow/runtime/runs/worker.py), [thread_runs.py](../backend/app/gateway/routers/thread_runs.py) |

## 4. 优先推荐的 4 条实验路线

按“可行性 + 论文化程度 + 代码改造难度”的综合排序，我建议优先级如下：

1. 工具调用诊断与修复
2. 子代理调度策略
3. Memory 注入与污染修复
4. 澄清优先策略

下面分别展开。

## 5. 路线 A：工具调用诊断与修复

这是最推荐的主实验路线。

### 5.1 研究目标

研究问题可以写成：

- DeerFlow 中任务失败，是否主要由错误工具选择或错误工具参数导致？
- 在工具失败后，采用不同修复策略是否能显著提升成功率？

### 5.2 为什么这条路线最稳

原因很直接：

- 工具调用是显式事件，不是隐式推理
- 工具失败有明确反馈
- 干预动作可以做成规则，不依赖复杂模型训练
- 很容易做对照组

DeerFlow 当前已经有：

- 工具异常转错误消息的机制，见 [tool_error_handling_middleware.py](../backend/packages/harness/deerflow/agents/middlewares/tool_error_handling_middleware.py)
- 工具执行前的 guardrail 机制，见 [guardrails/middleware.py](../backend/packages/harness/deerflow/guardrails/middleware.py)
- bash 风险分类机制，见 [sandbox_audit_middleware.py](../backend/packages/harness/deerflow/agents/middlewares/sandbox_audit_middleware.py)

这说明你不需要从零造实验框架，只需要在现有工具链前后再加一个实验 middleware。

### 5.3 推荐的实验变量

自变量：

- 工具修复策略

推荐至少做 4 组：

- `Baseline`：保持 DeerFlow 当前行为
- `Repair-Args`：工具失败后重写参数再试一次
- `Repair-Tool`：工具失败后换成候选替代工具
- `Clarify-First`：高不确定任务先触发澄清，再执行工具

中间变量：

- 首次工具选择是否正确
- 是否发生 tool error
- 是否触发二次修复
- 修复后是否成功

因变量：

- 任务成功率
- 平均工具失败次数
- 平均完成时长
- 平均 token 用量
- 用户侧可见错误率

### 5.4 推荐的实现方式

新增两个实验模块：

- `CausalTraceMiddleware`
- `CausalRepairMiddleware`

建议位置：

- `backend/packages/harness/deerflow/agents/middlewares/causal_trace_middleware.py`
- `backend/packages/harness/deerflow/agents/middlewares/causal_repair_middleware.py`

挂载位置建议：

- 在 [agent.py](../backend/packages/harness/deerflow/agents/lead_agent/agent.py) 的 `_build_middlewares()` 中插入
- `CausalTraceMiddleware` 放在工具和模型调用都能看到的位置
- `CausalRepairMiddleware` 放在 `ToolErrorHandlingMiddleware` 之前或与之配合

### 5.5 可记录的数据

每个 run 记录：

- `run_id`
- `thread_id`
- `task_category`
- `tool_name`
- `tool_args`
- `error_type`
- `repair_action`
- `repair_count`
- `final_status`
- `latency_ms`
- `token_usage`

可以挂到：

- runtime metadata，见 [agent.py](../backend/packages/harness/deerflow/agents/lead_agent/agent.py)
- run stream，见 [worker.py](../backend/packages/harness/deerflow/runtime/runs/worker.py)
- tracing callbacks，见 [factory.py](../backend/packages/harness/deerflow/models/factory.py)

### 5.6 任务集怎么设计

建议不要一上来做开放式聊天任务，而是做工具链明确的任务。

推荐 4 类：

- 文件定位与读取任务
- 多步工具链任务
- 代码修改与结果输出任务
- 含有歧义或参数不完整的任务

每类准备 20 到 30 个任务，比纯数量更重要的是覆盖不同失败模式。

### 5.7 这条路线的优点

- 工程工作量可控
- 指标清晰
- 容易写“验证 + 修复”结构
- 非常适合毕设

## 6. 路线 B：子代理调度策略实验

如果你想保留“多智能体”元素，但不想再讲传统多智能体协作范式，这条路线很合适。

### 6.1 研究目标

研究问题可以写成：

- 子代理是否真的提升了复杂任务表现？
- 对哪些任务类型，子代理是正收益；对哪些任务类型，子代理会引入额外成本？

### 6.2 为什么 DeerFlow 上容易做

因为 DeerFlow 的 subagent 是显式可开关的：

- 是否暴露 `task` 工具由 [tools.py](../backend/packages/harness/deerflow/tools/tools.py) 的 `subagent_enabled` 决定
- lead agent prompt 会根据 `subagent_enabled` 切换协作策略，见 [prompt.py](../backend/packages/harness/deerflow/agents/lead_agent/prompt.py)
- 子代理执行器是独立模块，见 [executor.py](../backend/packages/harness/deerflow/subagents/executor.py)
- `task` 工具本身已经会发出开始、运行中、完成等事件，见 [task_tool.py](../backend/packages/harness/deerflow/tools/builtins/task_tool.py)

这很适合做开关实验。

### 6.3 推荐的实验组

- `Single-Agent`：关闭 subagent
- `Subagent-On`：开启 subagent，默认并发上限
- `Subagent-Low-Parallel`：限制更低的并发
- `Subagent-Selective`：只在任务满足特定条件时启用

### 6.4 推荐的任务类型

要把任务分成两类，否则结果会混淆：

- 可分解任务  
  例如多文件分析、多来源检索、多角度比较
- 不可分解任务  
  例如单文件读取、一次简单编辑、单次命令执行

### 6.5 指标

- 成功率
- 平均总时长
- 平均 token
- 子代理调用次数
- 子代理结果被主代理真正利用的比例
- 无效分解率

### 6.6 推荐实现点

你可以新增一个“调度判定层”，不要直接改 `task_tool` 的底层执行逻辑。

优先改这些位置：

- [agent.py](../backend/packages/harness/deerflow/agents/lead_agent/agent.py)
- [prompt.py](../backend/packages/harness/deerflow/agents/lead_agent/prompt.py)
- [task_tool.py](../backend/packages/harness/deerflow/tools/builtins/task_tool.py)
- [executor.py](../backend/packages/harness/deerflow/subagents/executor.py)

最稳的做法不是“让模型自己决定一切”，而是：

- 在 runtime metadata 或 middleware 中给出 `subagent_policy`
- 由实验代码控制：哪些任务允许分解、最大并发多少、什么情况下强制单代理

### 6.7 这条路线的优缺点

优点：

- 保留多智能体研究元素
- 和你原题方向有延续性
- 容易做 ablation

缺点：

- 任务集设计要求更高
- 很容易把结果混淆成“prompt 写得好不好”，而不是“子代理机制是否有效”

## 7. 路线 C：Memory 注入与污染修复实验

这条路线更偏“长期上下文是否帮助或伤害 agent”。

### 7.1 研究目标

研究问题可以写成：

- 长期 memory 注入是否总是提升性能？
- 低质量或过时 memory 是否会污染当前任务决策？
- selective injection / selective update 能否修复这种污染？

### 7.2 DeerFlow 里已有的基础

DeerFlow 已经有完整的 memory 链路：

- 运行结束后把消息送入队列，见 [memory_middleware.py](../backend/packages/harness/deerflow/agents/middlewares/memory_middleware.py)
- 队列带 debounce，见 [queue.py](../backend/packages/harness/deerflow/agents/memory/queue.py)
- 由单独 updater 调用模型更新 memory，见 [updater.py](../backend/packages/harness/deerflow/agents/memory/updater.py)
- memory 会在 prompt 中注入，见 [prompt.py](../backend/packages/harness/deerflow/agents/lead_agent/prompt.py)
- memory 的配置可控，见 [memory_config.py](../backend/packages/harness/deerflow/config/memory_config.py)

这条链已经很完整，适合直接做实验。

### 7.3 推荐的实验组

- `Memory-Off`：完全关闭注入
- `Memory-On`：保持当前默认
- `Memory-High-Confidence`：只注入高置信 facts
- `Memory-Correction-Weighted`：强化 correction 类事实
- `Memory-Filtered`：过滤特定类别或来源的 memory

### 7.4 关键变量

自变量：

- 是否注入 memory
- 注入阈值
- 写入阈值
- 是否保留 correction / reinforcement

中间变量：

- memory 中事实数量
- memory 命中率
- 当前任务是否引用了错误 memory

因变量：

- 任务成功率
- 错误引用率
- 工具选择偏差率
- 多轮对话中的修复能力

### 7.5 推荐实现点

优先改这些位置：

- [memory_middleware.py](../backend/packages/harness/deerflow/agents/middlewares/memory_middleware.py)
- [updater.py](../backend/packages/harness/deerflow/agents/memory/updater.py)
- [storage.py](../backend/packages/harness/deerflow/agents/memory/storage.py)
- [prompt.py](../backend/packages/harness/deerflow/agents/lead_agent/prompt.py)
- [memory_config.py](../backend/packages/harness/deerflow/config/memory_config.py)

### 7.6 这条路线的风险

它的难点不是代码，而是任务构造。  
你需要设计“前一轮注入了错误偏好或陈旧事实，后一轮任务因此被误导”的场景，否则看不出差异。

## 8. 路线 D：澄清优先策略实验

这条路线适合作为辅助实验，不建议当唯一主线。

### 8.1 研究目标

研究问题可以写成：

- 在需求缺失或存在歧义时，“先澄清”是否能降低后续错误率？
- 它是否会增加时延，且这种时延是否值得？

### 8.2 DeerFlow 上的现成基础

DeerFlow 的澄清机制不是普通工具输出，而是 workflow 级中断：

- `ask_clarification` 会被 [clarification_middleware.py](../backend/packages/harness/deerflow/agents/middlewares/clarification_middleware.py) 拦截
- 它会返回 `Command(goto=END)`，直接停止当前执行并等待用户回复

这比普通 prompt engineering 更适合做“先问再做”的实验。

### 8.3 推荐实验组

- `Direct-Action`
- `Clarify-When-Ambiguous`
- `Clarify-Always-On-Risky`

### 8.4 指标

- 首次成功率
- 总交互轮数
- 返工率
- 平均任务完成时长

### 8.5 为什么不建议作为唯一主线

因为它更像“交互策略实验”，论文上不如“工具修复”或“子代理调度”硬。

## 9. 最小可运行方案：建议你这样做

如果目标是“毕设能做完、能跑、能出图”，建议采用“一主一辅”方案。

主线建议：

- 路线 A：工具调用诊断与修复

辅线建议二选一：

- 路线 B：子代理调度
- 路线 C：memory 污染修复

最小可运行版本可以这样定：

### 9.1 主实验

主实验名称：

- 因果化工具调用修复实验

实验组：

- Baseline
- Repair-Args
- Repair-Tool
- Clarify-First

任务数建议：

- 60 到 100 个任务
- 每类任务 15 到 25 个
- 每个任务重复运行 3 次

核心输出：

- 成功率对比图
- 平均失败次数对比图
- 平均时延对比图
- 修复策略命中率

### 9.2 辅实验

辅实验名称：

- 子代理调度收益分析

实验组：

- Single-Agent
- Subagent-On
- Subagent-Selective

任务集按“可分解 / 不可分解”分开。

### 9.3 不建议的做法

不要同时改：

- prompt 主体
- model provider
- memory 策略
- subagent 策略
- tool policy

否则实验很难解释。

## 10. 建议你优先新增的实验代码

如果你现在就要动手，建议先只加下面三样：

### 10.1 `CausalTraceMiddleware`

作用：

- 记录每轮任务的关键决策和结果

建议记录字段：

- thread_id
- run_id
- task_id
- intervention_group
- selected_tools
- tool_errors
- used_subagents
- clarification_triggered
- memory_injected
- final_status

推荐挂载位置：

- [agent.py](../backend/packages/harness/deerflow/agents/lead_agent/agent.py)

### 10.2 `CausalRepairMiddleware`

作用：

- 在工具失败时执行可控修复策略

策略可以先做成规则版：

- 参数重写
- 候选工具替换
- 风险任务先澄清
- 连续失败后停止重试

### 10.3 实验配置块

建议在 `config.yaml` 中新增实验配置，而不是写死在代码里。

例如：

```yaml
experiment:
  enabled: true
  group: repair_args
  trace_output: .deer-flow/experiments/trace.jsonl
  subagent_policy: selective
  memory_policy: high_confidence_only
```

当前仓库配置是集中读取的，入口在 [app_config.py](../backend/packages/harness/deerflow/config/app_config.py)。  
这意味着你很容易把实验组做成配置切换，而不是分叉一堆代码版本。

## 11. 数据采集建议

你的实验不要只看前端页面结果，建议直接在后端采集结构化数据。

优先使用这几层：

- `metadata`  
  `make_lead_agent()` 已经会注入 `agent_name`、`model_name`、`thinking_enabled` 等信息，见 [agent.py](../backend/packages/harness/deerflow/agents/lead_agent/agent.py)
- `run/thread`  
  Gateway 已经有 run 与 thread API，见 [thread_runs.py](../backend/app/gateway/routers/thread_runs.py)
- `checkpointer/store`  
  适合做复现实验与状态恢复，见 [checkpointer_config.py](../backend/packages/harness/deerflow/config/checkpointer_config.py)
- `tracing`  
  可对接 LangSmith/Langfuse，见 [tracing/factory.py](../backend/packages/harness/deerflow/tracing/factory.py)

推荐最终保存为 JSONL，每一条对应一次任务执行或一次工具调用。

## 12. 哪些地方先不要改

为了保证实验清晰，前期不建议优先改这些：

- 前端页面
- 模型适配层底层实现
- Nginx / Gateway 路由结构
- skills 生态本身

原因不是这些不重要，而是它们不利于你快速得到一组可以比较的实验结果。

前期最值得改的是：

- middleware
- tools 暴露策略
- subagent 策略
- memory 策略
- 实验日志采集

## 13. 最后的建议

如果你现在只能选一条主线，建议选：

- “基于 DeerFlow Harness 的工具调用因果诊断与修复实验”

如果你想保留“多智能体”元素，再加一个辅线：

- “子代理调度收益与代价分析”

这个组合的优点是：

- 题目不空
- 代码改造量可控
- 指标容易量化
- 实验能复现
- 论文叙事也顺

## 14. 仓库出处汇总

核心源码出处如下，便于后续继续细化实验设计：

- Lead Agent 装配： [backend/packages/harness/deerflow/agents/lead_agent/agent.py](../backend/packages/harness/deerflow/agents/lead_agent/agent.py)
- Lead Agent Prompt： [backend/packages/harness/deerflow/agents/lead_agent/prompt.py](../backend/packages/harness/deerflow/agents/lead_agent/prompt.py)
- Thread State： [backend/packages/harness/deerflow/agents/thread_state.py](../backend/packages/harness/deerflow/agents/thread_state.py)
- 工具装配： [backend/packages/harness/deerflow/tools/tools.py](../backend/packages/harness/deerflow/tools/tools.py)
- 子代理任务工具： [backend/packages/harness/deerflow/tools/builtins/task_tool.py](../backend/packages/harness/deerflow/tools/builtins/task_tool.py)
- 子代理执行器： [backend/packages/harness/deerflow/subagents/executor.py](../backend/packages/harness/deerflow/subagents/executor.py)
- 工具异常处理： [backend/packages/harness/deerflow/agents/middlewares/tool_error_handling_middleware.py](../backend/packages/harness/deerflow/agents/middlewares/tool_error_handling_middleware.py)
- LLM 异常与重试： [backend/packages/harness/deerflow/agents/middlewares/llm_error_handling_middleware.py](../backend/packages/harness/deerflow/agents/middlewares/llm_error_handling_middleware.py)
- 澄清中断机制： [backend/packages/harness/deerflow/agents/middlewares/clarification_middleware.py](../backend/packages/harness/deerflow/agents/middlewares/clarification_middleware.py)
- Memory Middleware： [backend/packages/harness/deerflow/agents/middlewares/memory_middleware.py](../backend/packages/harness/deerflow/agents/middlewares/memory_middleware.py)
- Memory Queue： [backend/packages/harness/deerflow/agents/memory/queue.py](../backend/packages/harness/deerflow/agents/memory/queue.py)
- Memory Updater： [backend/packages/harness/deerflow/agents/memory/updater.py](../backend/packages/harness/deerflow/agents/memory/updater.py)
- Memory Storage： [backend/packages/harness/deerflow/agents/memory/storage.py](../backend/packages/harness/deerflow/agents/memory/storage.py)
- Guardrail Middleware： [backend/packages/harness/deerflow/guardrails/middleware.py](../backend/packages/harness/deerflow/guardrails/middleware.py)
- Guardrail Provider 协议： [backend/packages/harness/deerflow/guardrails/provider.py](../backend/packages/harness/deerflow/guardrails/provider.py)
- Sandbox Audit： [backend/packages/harness/deerflow/agents/middlewares/sandbox_audit_middleware.py](../backend/packages/harness/deerflow/agents/middlewares/sandbox_audit_middleware.py)
- 模型工厂： [backend/packages/harness/deerflow/models/factory.py](../backend/packages/harness/deerflow/models/factory.py)
- 运行执行器： [backend/packages/harness/deerflow/runtime/runs/worker.py](../backend/packages/harness/deerflow/runtime/runs/worker.py)
- 线程运行接口： [backend/app/gateway/routers/thread_runs.py](../backend/app/gateway/routers/thread_runs.py)
- 配置入口： [backend/packages/harness/deerflow/config/app_config.py](../backend/packages/harness/deerflow/config/app_config.py)
- Checkpointer 配置： [backend/packages/harness/deerflow/config/checkpointer_config.py](../backend/packages/harness/deerflow/config/checkpointer_config.py)
- Tracing 工厂： [backend/packages/harness/deerflow/tracing/factory.py](../backend/packages/harness/deerflow/tracing/factory.py)
