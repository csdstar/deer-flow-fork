# DeerFlow Fork Windows 本地开发环境命令清单

这份清单面向当前仓库 [deer-flow-fork](D:/Code/Project/deer-flow-fork)，适合 Windows + conda + Node.js 的本地开发方式。

仓库当前要求来自以下文件：

- [backend/pyproject.toml](D:/Code/Project/deer-flow-fork/backend/pyproject.toml)：`Python >= 3.12`
- [Makefile](D:/Code/Project/deer-flow-fork/Makefile)：`Node.js 22+`、本地安装依赖使用 `uv sync` 和 `pnpm install`
- [frontend/package.json](D:/Code/Project/deer-flow-fork/frontend/package.json)：`packageManager: pnpm@10.26.2`
- [scripts/check.py](D:/Code/Project/deer-flow-fork/scripts/check.py)：检查 `node`、`pnpm`、`uv`、`nginx`
- [scripts/run-with-git-bash.cmd](D:/Code/Project/deer-flow-fork/scripts/run-with-git-bash.cmd)：Windows 启动依赖 Git Bash

## 0. 关于官方文档里的 `make`

官方 README 和 Install 文档确实默认使用 `make`，例如：

- `make config`
- `make check`
- `make install`
- `make dev`

但对当前这个仓库来说，`make` 主要只是一个包装层，并不负责真正的构建逻辑。实际动作都在 [Makefile](D:/Code/Project/deer-flow-fork/Makefile) 里展开了：

- `make config` 实际执行 `python .\scripts\configure.py`
- `make check` 实际执行 `python .\scripts\check.py`
- `make install` 实际执行后端 `uv sync` 和前端 `pnpm install`
- `make dev` 在 Windows 下实际执行 `.\scripts\run-with-git-bash.cmd .\scripts\serve.sh --dev`

所以这份文档没有把 `make` 作为必须依赖，而是直接给出等价命令。这样做的原因是：

- Windows 原生环境通常默认没有 GNU Make
- DeerFlow 当前仓库已经把 `make` 的底层命令写得很清楚
- 你现在的目标是把项目跑起来，而不是强依赖某个入口工具

如果你后面确实想和官方 README 保持完全一致，也可以额外安装 GNU Make；但对当前这个 fork 来说，不装 `make` 也可以完成本地开发启动。

## 1. 官方推荐版本

按当前仓库配置，建议你准备下面这些版本或范围：

| 组件 | 推荐版本 |
| --- | --- |
| Python | `3.12.x` |
| Node.js | `22.x` 或更高 |
| pnpm | `10.26.2` |
| uv | 最新稳定版即可，仓库未固定版本 |
| nginx | 最新稳定版即可，仓库未固定版本 |
| Git for Windows | 最新稳定版即可，需包含 Git Bash |

## 2. 一次性安装命令

以下命令建议在 PowerShell 中执行。

### 2.1 创建并激活 conda 环境

如果你还没有专门给 DeerFlow 准备环境，先执行：

```powershell
conda create -n deerflow python=3.12 -y
conda activate deerflow
python --version
where python
```

如果你已经有可用环境，只需要：

```powershell
conda activate 你的环境名
python --version
where python
```

预期结果：

- `python --version` 至少是 `3.12`
- `where python` 指向 conda 环境，而不是 `WindowsApps\python.exe`

### 2.2 安装 Node.js 22+

如果你还没安装或版本低于 22，优先用官方分发方式：

```powershell
winget install OpenJS.NodeJS.LTS
node --version
npm --version
```

如果你已经装好了，只验证即可：

```powershell
node --version
npm --version
```

### 2.3 安装 pnpm 10.26.2

当前仓库前端显式声明使用 `pnpm@10.26.2`。优先使用 Node 官方推荐的 `corepack`：

```powershell
corepack enable
corepack prepare pnpm@10.26.2 --activate
pnpm --version
```

如果 `corepack` 路线不可用，再使用 npm 全局安装：

```powershell
npm install -g pnpm@10.26.2
pnpm --version
```

### 2.4 安装 uv

`uv` 官方安装文档：

- https://docs.astral.sh/uv/getting-started/installation/

Windows 下优先用：

```powershell
winget install --id=astral-sh.uv -e
uv --version
```

如果你更希望放进当前 Python 环境，也可以备用：

```powershell
pip install uv
uv --version
```

### 2.5 安装 Git for Windows 和 Git Bash

Windows 本地启动脚本会显式调用 Git Bash，所以不能只有 `git`，还要有 `bash.exe`。

官方安装方式可直接用：

```powershell
winget install --id Git.Git -e
git --version
bash --version
```

如果 `bash --version` 失败，检查 Git 的安装目录是否已经加入 `PATH`。常见目录类似：

```text
C:\Program Files\Git\bin
```

### 2.6 安装 nginx

`nginx` 官方下载页：

- https://nginx.org/en/download.html

仓库只检查 `nginx` 是否存在，没有固定版本要求。Windows 上建议下载官方稳定版 zip，解压到固定目录，比如 `C:\tools\nginx`，然后执行：

```powershell
setx PATH "$env:PATH;C:\tools\nginx"
$env:PATH = "$env:PATH;C:\tools\nginx"
nginx -v
```

如果你已经安装过，只验证即可：

```powershell
nginx -v
```

## 3. 环境总校验

全部装完后，在同一个 PowerShell 会话中执行：

```powershell
conda activate deerflow
python --version
node --version
pnpm --version
uv --version
nginx -v
git --version
bash --version
```

建议目标：

- Python `3.12.x`
- Node.js `22+`
- pnpm `10.26.2`
- `uv` 可执行
- `nginx` 可执行
- `bash` 可执行

## 4. DeerFlow 项目初始化命令

在仓库根目录 [deer-flow-fork](D:/Code/Project/deer-flow-fork) 中执行。

### 4.1 进入仓库并激活环境

```powershell
cd D:\Code\Project\deer-flow-fork
conda activate deerflow
```

### 4.2 生成配置文件

如果仓库根目录还没有 `config.yaml`，执行：

```powershell
python .\scripts\configure.py
```

如果你已经有 `config.yaml`，跳过这一步，避免覆盖。

### 4.3 检查依赖

```powershell
python .\scripts\check.py
```

### 4.4 安装后端依赖

```powershell
cd .\backend
uv sync
cd ..
```

### 4.5 安装前端依赖

```powershell
cd .\frontend
pnpm install
cd ..
```

## 5. 必做配置

在启动前，你至少还要完成下面两件事。

### 5.1 配置模型

编辑 [config.yaml](D:/Code/Project/deer-flow-fork/config.yaml)，至少启用一个 `models:` 条目。最简单的 OpenAI 示例：

```yaml
models:
  - name: gpt-4
    display_name: GPT-4
    use: langchain_openai:ChatOpenAI
    model: gpt-4
    api_key: $OPENAI_API_KEY
    max_tokens: 4096
    temperature: 0.7
```

### 5.2 配置环境变量

编辑仓库根目录 `.env`，至少补上你实际使用的模型密钥，例如：

```env
OPENAI_API_KEY=your-real-key
TAVILY_API_KEY=your-real-key
```

如果你使用别的模型，就在 `config.yaml` 中把 `api_key` 指向对应变量，例如：

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GEMINI_API_KEY`
- `DEEPSEEK_API_KEY`
- `VOLCENGINE_API_KEY`
- `VLLM_API_KEY`

## 6. 启动命令

Windows 下不依赖 `make` 的启动方式如下：

```powershell
cd D:\Code\Project\deer-flow-fork
conda activate deerflow
.\scripts\run-with-git-bash.cmd .\scripts\serve.sh --dev
```

如果你想走生产模式：

```powershell
cd D:\Code\Project\deer-flow-fork
conda activate deerflow
.\scripts\run-with-git-bash.cmd .\scripts\serve.sh --prod
```

## 7. 无 `make` 的等价命令速查

仓库里的 `make` 主要只是一个包装层，可以按下面替换：

| `make` 命令 | 等价命令 |
| --- | --- |
| `make config` | `python .\scripts\configure.py` |
| `make check` | `python .\scripts\check.py` |
| `make install` | `cd backend && uv sync` 然后 `cd frontend && pnpm install` |
| `make dev` | `.\scripts\run-with-git-bash.cmd .\scripts\serve.sh --dev` |
| `make start` | `.\scripts\run-with-git-bash.cmd .\scripts\serve.sh --prod` |

如果你装了 GNU Make，那么也可以直接继续使用官方写法：

```powershell
make config
make check
make install
make dev
```

只是对 Windows 原生环境来说，本文更推荐直接使用上面的等价命令。

## 8. 推荐执行顺序

如果你想直接照着跑，按这个顺序最省事：

```powershell
conda create -n deerflow python=3.12 -y
conda activate deerflow
winget install OpenJS.NodeJS.LTS
corepack enable
corepack prepare pnpm@10.26.2 --activate
winget install --id=astral-sh.uv -e
winget install --id Git.Git -e
```

然后手动从 nginx 官网下载稳定版 zip，解压并加入 `PATH`，接着：

```powershell
cd D:\Code\Project\deer-flow-fork
python .\scripts\configure.py
python .\scripts\check.py
cd .\backend
uv sync
cd ..
cd .\frontend
pnpm install
cd ..
.\scripts\run-with-git-bash.cmd .\scripts\serve.sh --dev
```

## 9. 常见阻塞点

- `python` 指向 `WindowsApps`：说明 conda 环境没有正确激活。
- `pnpm` 不可用：先执行 `corepack enable` 和 `corepack prepare pnpm@10.26.2 --activate`。
- `bash` 不可用：安装 Git for Windows，并确认 `bash.exe` 在 `PATH` 中。
- `nginx` 不可用：DeerFlow 的本地模式会检查它，Windows 下需要手动安装官方 zip 版。
- `config.yaml` 没有启用任何模型：服务即使启动，也无法正常工作。
