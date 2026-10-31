# PCR-0005 · NapCat 启动自匹配误杀修复与启动日志

| 字段 | 内容 |
| --- | --- |
| 编号 | PCR-0005 |
| 标题 | NapCat 启动自匹配误杀修复与启动日志 |
| 状态 | 已完成（真实启动待用户复测） |
| 提出日期 | 2026-10-31 |
| 需求方 | zigyr |
| 实施方 | DSH Agent |
| 关联提交 | 本 PCR 对应提交 |
| 关联 PCR | PCR-0002（诊断）、PCR-0003（启动器） |

## 1. 背景与问题

2026-10-31 23:33–23:45，用户点击「一键启动」连续失败：

```text
[23:33:36] 正在拉起 NapCat 网关
[23:34:36] NapCat: NapCat 启动失败，日志：
```

表现为：

- AstrBot 正常，6185/6199 监听；
- WSL 正常，网关 `172.27.48.1`；
- NapCat QQ 程序与配置目录均存在；
- OneBot 配置匹配，WSL→Windows 6199 可达；
- 但 NapCat 进程始终没有出现，`/root/napcat-run.log` 被清空后没有任何内容；
- 每次等满约 36 秒才失败。

## 2. 根因分析

启动脚本由 `wsl.exe ... -- bash -lc "<整段脚本>"` 执行，**整段脚本是 bash 进程的命令行参数**。
脚本中有：

```bash
Q=/root/Napcat/opt/QQ/qq
pkill -f '[o]pt/QQ/qq'
pkill -f 'Xvfb :99'
```

`pkill -f` 匹配的是**完整命令行**，因此：

- `Q=/root/Napcat/opt/QQ/qq` 这一行让 bash 自己的命令行包含 `opt/QQ/qq`；
- 脚本里的 `Xvfb :99` 让 bash 命令行包含 `Xvfb :99`；
- 结果 `pkill` 匹配并杀掉了**正在执行脚本的 bash 自己**；
- 脚本在 `screen`/`xvfb-run` 启动前就被终止，所以日志只剩空文件，QQ 自然没有起来。

旧版 Web 控制台的 start 流程没有 `pkill -f 'opt/QQ/qq'`，因此 21:15 还能启动；本次新增的清理逻辑引入了这个回归。

## 3. 需求提炼

- **问题**：启动脚本的 `pkill -f` 自匹配，误杀父 shell；失败信息为空。
- **目标（可验证）**：
  1. 停止旧进程改用**精确进程名**（`pkill -x qq` / `pkill -x Xvfb`），不再用会匹配脚本自身的 `-f` 路径。
  2. PID 检测改用 `pgrep -x qq/QQ`，避免把 bash 自己当成 QQ。
  3. 启动器把自身环境（QQ 路径/权限、xvfb-run/Xvfb/screen 是否存在、screen 状态、xvfb 日志）写入 `/root/napcat-run.log`。
  4. 启动失败时把完整日志写入控制台事件日志，并尽量缩短等待。
  5. 诊断新增「NapCat QQ 可执行」「xvfb-run」「Xvfb」「screen」检查。
- **非目标**：
  - 不改变 AstrBot 启动、OneBot 校准、快速登录流程。
  - 不修改 QQ/NapCat 二进制或系统包。

## 4. 方案与取舍

| 方案 | 说明 | 取舍 |
| --- | --- | --- |
| A（采纳） | 精确进程名 + 启动器全量日志 + 前置依赖诊断 | 解决自匹配；失败原因可见 |
| B | 继续用 `pkill -f`，但在脚本里拼接字符串规避匹配 | 可读性差、容易再犯 |
| C | 不清理旧进程，直接启动 | 可能多开/端口冲突，不可靠 |
| D | 用 systemd 管理 NapCat | 改动大，超出当前范围 |

## 5. 实施计划

1. `WSL.probe` 改用 `pgrep -x qq/QQ`，不再用路径模式。
2. `NapCat.start`：`pkill -x qq/QQ`、`pkill -x Xvfb`；保留 `pkill -f "xvfb-run -a $Q"`（`$Q` 在脚本中是字面量，不会自匹配）。
3. 启动脚本 `exec 3>&1`，把环境、`ls -l`、依赖路径、`screen -ls`、失败诊断写入 `$L`；PID 只从 fd 3 输出。
4. 启动失败时读取完整日志、提取 `ERROR:`/`no QQ process` 作为首行原因；等待从 35s 降到约 17s。
5. `Backend.start_all` 把完整失败信息写入事件日志，控制台日志可直接看到。
6. 诊断增加 `test -x` 与 `command -v` 依赖检查。
7. 用真实报告复测。

## 6. 验收标准

- [ ] 启动脚本不再包含会匹配自身的 `pkill -f 'opt/QQ/qq'` / `pkill -f 'Xvfb :99'`。
- [ ] 生成脚本经人工检查/静态检查无语法问题。
- [ ] 空闲诊断新增 QQ 可执行与 xvfb-run/Xvfb/screen 检查。
- [ ] 用户重启控制台后一键启动，NapCat 进程出现（真实 WSL 验证）。
- [ ] 若仍失败，`/root/napcat-run.log` 与控制台日志能给出具体原因。
- [ ] `selftest.py` / `py_compile` 通过。

## 7. 风险与回滚

| 风险 | 概率 / 影响 | 缓解 | 回滚 |
| --- | --- | --- | --- |
| `pkill -x qq` 匹配不到特殊进程名 | 低 / 中 | 同时匹配 `QQ`；失败日志会显示；可改回路径模式但需避免自匹配 | `git revert` |
| 误杀其他 Xvfb | 低 / 低 | WSL 内通常只有 NapCat 的 Xvfb；必要时按 display 精确匹配 | 重启 WSL |
| 日志过大 | 低 / 低 | 每次启动截断；失败只取尾部 2600 字符 | 清空日志 |
| 真实启动仍失败 | 中 / 中 | 新增依赖诊断 + 启动器日志，下一次可定位 | 回滚本次提交 |

## 8. 验证记录

| 日期 | 检查项 | 命令 / 方式 | 结果 |
| --- | --- | --- | --- |
| 2026-10-31 | 生成脚本 | monkeypatch `wsl.run` 捕获 `NapCat.start` 脚本 | 1937 字节；关键行均为 `pkill -x` / `pgrep -x` |
| 2026-10-31 | 自匹配检查 | 检索脚本中的 `pkill -f` | 仅剩 `xvfb-run -a $Q`（`$Q` 为字面量，安全） |
| 2026-10-31 | 语法 | `python -m py_compile console/core.py` | 通过 |
| 2026-10-31 | 自检 | `python console\selftest.py` | 8/8 通过 |
| 2026-10-31 | 真实 WSL 启动 | 需用户重启控制台后点击一键启动 | 待复测 |

## 9. 评审与确认

| 日期 | 确认人 | 结论 | 备注 |
| --- | --- | --- | --- |
| 2026-10-31 | zigyr | 已批准 | 用户回传 23:45 启动失败报告；定位为 `pkill -f` 自匹配，按报告修复 |
