# HandsFree Claude

> 一键自动批准 Claude Code 的工具调用授权,会话结束时播放提示音。

**语言:** [English](README.md) · 简体中文

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg)](https://www.python.org/downloads/)
[![Platforms](https://img.shields.io/badge/Platforms-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](#系统前置条件)

一个极简、始终置顶的 Tk 小窗口。开启 **免手动模式(HandsFree mode)** 后,Claude Code 的所有工具调用授权都会被自动批准;Claude 完成回复时会播放一个提示音。没有守护进程,没有 HTTP 服务,没有语音识别。

本项目源自 [Oi-Claude](https://github.com/jz0523/Oi-Claude),只保留了大多数用户实际在用的那部分功能。

---

## 界面示意

```
┌───────────────────────────────────────┐
│  HandsFree Claude              ⚙      │
│                                        │
│       ●  HandsFree mode: ON            │
│                                        │
│       [       Turn OFF       ]         │
└───────────────────────────────────────┘
```

三个元素:应用名、状态灯(灰色 = 关、绿色 = 开)、开关按钮。齿轮图标打开设置面板。

---

## 运行要求

- Python 3.10 或更高版本
- Windows、macOS 或 Linux
- 已安装 [Claude Code](https://claude.com/claude-code)(命令行或 VS Code 插件)

### 系统前置条件

| 平台 | 需要准备 |
|---|---|
| **Windows** | 无需额外准备 —— python.org 官方安装包自带 Tk。 |
| **macOS** | 使用带 Tk 支持的 Python。python.org 官方安装包可直接使用;Homebrew 的纯 `python3` 不行。必要时执行 `brew install python-tk@3.12`(或你对应的版本)。 |
| **Linux** | 安装系统 Tk 包:`sudo apt install python3-tk`(Debian/Ubuntu)或 `sudo dnf install python3-tkinter`(Fedora)。 |

---

## 安装

```bash
git clone https://github.com/jz0523/HandsFree-Claude.git
cd HandsFree-Claude
pip install -e .
handsfree-claude install-hooks
```

然后 **彻底重启所有正在运行的 Claude Code 会话** —— Claude Code 只在启动时读取 `~/.claude/settings.json`,不会在运行期间热加载 hooks 配置。

### Windows:如果找不到 `handsfree-claude` 命令

Python 用户级安装的 `Scripts` 目录不一定在 PATH 中。任选其一:

**A. 使用模块形式(在任何环境下都可用):**

```powershell
python -m handsfree_claude install-hooks
python -m handsfree_claude
```

**B. 将 Scripts 目录加入用户 PATH(一次性配置):**

```powershell
$scriptsDir = "$([Environment]::GetFolderPath('ApplicationData'))\Python\Python$(python -c 'import sys;print(str(sys.version_info.major)+str(sys.version_info.minor))')\Scripts"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$scriptsDir*") {
  [Environment]::SetEnvironmentVariable("Path", "$userPath;$scriptsDir", "User")
}
```

然后关闭并重新打开 PowerShell 即可生效。

### 从 Oi-Claude 迁移

如果你之前用过 [Oi-Claude](https://github.com/jz0523/Oi-Claude),请先卸载它的 hooks(`oi-claude uninstall-hooks`)。`handsfree-claude install-hooks` 也会检测并提醒你残留的 `oi-claude-hook` 条目 —— 两个工具的 matcher 会互相覆盖,不应同时注册。

---

## 使用

打开窗口:

```bash
handsfree-claude
```

把 HandsFree mode 切到 **开** → 之后 Claude Code 的工具调用提示会被自动批准,Claude 每次回复完成后也会播放一次提示音。
切到 **关**,或关闭窗口 → 恢复正常提示流程。

---

## 设置面板

点击齿轮图标:

- **End sound(提示音)** —— 从自带的音频中选一个。
- **Custom sound file(自定义音频)** —— 浏览并选择你自己的 `.mp3` 或 `.wav`。一旦设置,会覆盖上面的下拉选择。
- **Mute sound(静音)** —— 仍然保持自动批准,但不再播放提示音。

---

## 命令

| 命令 | 作用 |
|---|---|
| `handsfree-claude` | 打开窗口(等价于 `run`)。 |
| `handsfree-claude install-hooks` | 在 `~/.claude/settings.json` 中注册 hooks。幂等:会清理旧的残留条目。 |
| `handsfree-claude uninstall-hooks` | 移除所有变体的 hook 条目。 |
| `handsfree-claude status` | 查看窗口是否在运行、hooks 是否已注册。 |

---

## 工作原理

- 窗口进程独占 `~/.handsfree-claude/state.json`,内容是 `{enabled, pid}`。
- 在 Claude Code 中注册了两个 hook(`PreToolUse`、`Stop`),每次触发时作为短生命周期子进程调用 `handsfree-claude-hook`。
- Hook 读取状态文件。如果 `enabled=true` **而且** 窗口的 PID 仍然存活(用 `psutil.pid_exists` 判断),它会对 `PreToolUse` 输出 `permissionDecision: "allow"`,或在 `Stop` 事件里派发一个 detached 子进程去播放提示音。否则直接静默退出。
- 关闭窗口时,会把 `enabled` 写回 `false` 并清空 PID,不会有"关窗后仍然自动批准"的情况。

在 Windows 上,installer 会把 hook 命令以正斜杠(`/`)写入 settings.json,因为 Claude Code 会通过 Git Bash 调用 hook,而 bash 会把反斜杠当转义字符吃掉。

---

## 排错

**开启了 HandsFree mode,仍然弹出授权提示。**

1. 确认状态灯是绿色,且 `~/.handsfree-claude/state.json` 里 `"enabled": true` 且 PID 与当前窗口匹配。
2. 确认 hook 已注册:`handsfree-claude status` 应该显示 `Hooks installed: yes`。
3. **彻底重启 Claude Code 会话。** Hooks 只在启动时加载。
4. 仍然不工作?打开诊断日志:

   ```bash
   # macOS / Linux
   export HANDSFREE_CLAUDE_DEBUG=1

   # Windows PowerShell
   $env:HANDSFREE_CLAUDE_DEBUG = "1"
   ```

   重启 Claude Code,再触发一次工具调用,然后查看 `~/.handsfree-claude/logs/hook.log`。日志里包含每次 hook 的调用、Claude Code 传入的原始 stdin,以及我们做出的决定。提 issue 时把这个日志附上。

**关闭窗口后,自动批准就失效了。**

这是故意设计的。关闭窗口等同于显式关闭开关 —— HandsFree 永远不会跨启动保留"开启"状态。

---

## 开发

```bash
pip install -e ".[dev]"
pytest
```

47 个单元测试覆盖了状态文件读写、PID 存活判断、配置文件 I/O、hook 分发、CLI 命令、installer 幂等性。Tk UI 部分通过手动冒烟测试验证。

---

## 许可证

[MIT](LICENSE)
