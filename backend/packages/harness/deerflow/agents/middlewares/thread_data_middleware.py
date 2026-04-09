import logging
from typing import NotRequired, override

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langgraph.config import get_config
from langgraph.runtime import Runtime

from deerflow.agents.thread_state import ThreadDataState
from deerflow.config.paths import Paths, get_paths

logger = logging.getLogger(__name__)


class ThreadDataMiddlewareState(AgentState):
    """Compatible with the `ThreadState` schema."""

    thread_data: NotRequired[ThreadDataState | None]


class ThreadDataMiddleware(AgentMiddleware[ThreadDataMiddlewareState]):
    """为每次线程执行准备线程级目录信息。

    它负责把当前 `thread_id` 映射到 DeerFlow 约定的线程目录结构：
    - {base_dir}/threads/{thread_id}/user-data/workspace
    - {base_dir}/threads/{thread_id}/user-data/uploads
    - {base_dir}/threads/{thread_id}/user-data/outputs

    生命周期管理：
    - `lazy_init=True`（默认）：只计算路径，目录按需创建
    - `lazy_init=False`：在 before_agent() 阶段提前创建目录
    """

    state_schema = ThreadDataMiddlewareState

    def __init__(self, base_dir: str | None = None, lazy_init: bool = True):
        """初始化中间件。

        Args:
            base_dir: 线程数据根目录，默认使用 Paths 的全局解析结果。
            lazy_init: 为 True 时延迟创建目录；为 False 时在 before_agent() 中提前创建。
                      默认开启延迟模式，以减少不必要的 IO。
        """
        super().__init__()
        self._paths = Paths(base_dir) if base_dir else get_paths()
        self._lazy_init = lazy_init

    def _get_thread_paths(self, thread_id: str) -> dict[str, str]:
        """获取某个线程的数据目录路径。

        Args:
            thread_id: The thread ID.

        Returns:
            包含 workspace_path、uploads_path、outputs_path 的字典。
        """
        return {
            "workspace_path": str(self._paths.sandbox_work_dir(thread_id)),
            "uploads_path": str(self._paths.sandbox_uploads_dir(thread_id)),
            "outputs_path": str(self._paths.sandbox_outputs_dir(thread_id)),
        }

    def _create_thread_directories(self, thread_id: str) -> dict[str, str]:
        """创建线程目录，并返回这些目录路径。

        Args:
            thread_id: The thread ID.

        Returns:
            创建后的目录路径字典。
        """
        self._paths.ensure_thread_dirs(thread_id)
        return self._get_thread_paths(thread_id)

    @override
    def before_agent(self, state: ThreadDataMiddlewareState, runtime: Runtime) -> dict | None:
        context = runtime.context or {}
        thread_id = context.get("thread_id")
        if thread_id is None:
            config = get_config()
            thread_id = config.get("configurable", {}).get("thread_id")

        if thread_id is None:
            raise ValueError("Thread ID is required in runtime context or config.configurable")

        if self._lazy_init:
            # 延迟初始化：先把路径写入 state，不立即创建物理目录
            paths = self._get_thread_paths(thread_id)
        else:
            # 立即初始化：进入 agent 前先把线程目录准备好
            paths = self._create_thread_directories(thread_id)
            logger.debug("Created thread data directories for thread %s", thread_id)

        return {
            "thread_data": {
                **paths,
            }
        }
