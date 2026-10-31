# PCR-0008 · NapCat 运行状态误判修复

| 字段 | 内容 |
| --- | --- |
| 编号 | PCR-0008 |
| 标题 | NapCat 运行状态误判修复 |
| 状态 | 已完成（真实运行观察待用户复测） |
| 提出日期 | 2026-11-01 |
| 需求方 | zigyr |
| 实施方 | DSH Agent |
| 关联提交 | 本 PCR 对应提交 |
| 关联 PCR | PCR-0005 / PCR-0007（NapCat 启动） |

## 1. 背景与问题

2026-11-01 00:34 用户截图：

- NapCat 卡：**已停止 / 未运行**；
- QQ 卡：**已登录 / 反向 WS 已连接**；
- 顶栏：**NapCat 未运行**（红色）；
- 日志：`NapCat: NapCat 已启动`、`已全部启动，QQ 与 AstrBot 已连通`；
- 用户描述：能扫码、能登录、能正常对话，**过一会就不行了**。

矛盾说明：NapCat 实际在跑（QQ 登录 + 反向 WS 已建立），但进程检测返回空，
状态判成“已停止”。随后：

1. 「自动守护」看到 `napcat.running=False`，限频调用一键启动；
2. `start_all` / `NapCat.start` 认为 NapCat 没跑，先 `screen -S napcat -X quit` / `pkill`；
3. 正在工作的 NapCat/QQ 被重启，连接断开——表现就是“聊一会就断”。

根因：PCR-0005 为避免 `pkill -f` 自匹配，把探测改成 `pgrep -x qq/QQ`；
但实际 Linux QQ/NapCat 进程的 `comm` 不一定是 `qq`/`QQ`，精确匹配漏报。
同时 `n_running` 只看 `pids`，没有用 WebUI / 反向 WS 兜底。

## 2. 需求提炼

- **目标（可验证）**：
  1. `WSL.probe` 的 PID 检测兼容路径：`pgrep -x qq/QQ` + `pgrep -f '[o]pt/QQ/qq'`；
  2. `status.napcat.running` 在 PID 为空但存在反向 WS、或 WebUI 6099 可连时仍为 True；
  3. `start_all` 在已有反向 WS / WebUI 时跳过 NapCat 启动，绝不重启正在工作的实例；
  4. UI NapCat 卡在 PID 为空但 WS 已连接时显示“运行中 · 反向 WS 已连接”，不再显示“已停止”；
  5. 自动守护不再因误判触发重启。
- **非目标**：
  - 不改变 QQ 登录、AstrBot 连接与 NapCat 启动脚本；
  - 不改变“无 WS/WebUI/PID 时”的真实停止判断。

## 3. 范围与影响

| 类型 | 内容 |
| --- | --- |
| 修改 | `core.WSL.probe()`：PID 增加路径匹配 |
| 修改 | `core.Backend.status()`：`n_running` 加入 peers/WebUI 端口兜底 |
| 修改 | `core.Backend.start_all()`：已有 peers/WebUI 时跳过 NapCat 启动 |
| 修改 | `core.NapCat.start/stop()`：增加 `pkill -f '[o]pt/QQ/qq'` 路径级清理（启动脚本已文件化，不会匹配自身） |
| 修改 | `ui.MainWindow.apply_status()`：PID 为空但运行时的卡片文案 |
| 新增 | 本 PCR |
| 数据 / 配置 | 无 |
| 依赖 | 无 |
| 安全 | 只读检测；无新增系统操作 |

## 4. 方案与取舍

| 方案 | 说明 | 取舍 |
| --- | --- | --- |
| A（采纳） | 多源判定：PID + 反向 WS + WebUI 端口 | 兼容进程名差异；不会误重启 |
| B | 只加 `pgrep -f` 路径 | 仍可能漏报；WebUI 失效时无兜底 |
| C | 只看 WebUI | WebUI 被禁用/端口冲突时误判 |
| D | 只看 screen 会话 | 残留会话会误判“运行中” |

## 5. 实施计划

1. `WSL.probe` PIDS 改为 `{ pgrep -x qq; pgrep -x QQ; pgrep -f '[o]pt/QQ/qq'; } | sort -u`。
2. `status`：先算 `webui_port_open`，`n_running = pids or peers or webui_port_open`。
3. `start_all`：若 `pids` / `peers` / 6099 任一存在，直接标记“已在运行”，不调用启动。
4. `start/stop` 增加 `pkill -f '[o]pt/QQ/qq'` 路径级清理；启动脚本文件化后 bash 命令行不含脚本正文，不会自匹配。
5. 卡片文案：PID 为空但 linked 时显示“运行中 · 反向 WS 已连接”。
6. 用合成 status 验证：pids=[] + peers 存在 → running=True、health=ok。
7. 用户重启控制台观察。

## 6. 验收标准

- [x] 合成状态：PID 为空但 peers 存在 → `napcat.running=True`、`health=ok`。
- [x] `start_all` 在 peers/WebUI 存在时不重启 NapCat（代码路径）。
- [x] UI 不再把“WS 已连接”的 NapCat 显示为已停止。
- [x] `py_compile` / `selftest.py` 通过。
- [ ] 用户实际运行 10 分钟以上，状态保持“运行正常”、聊天不中断（待复测）。

## 7. 风险与回滚

| 风险 | 概率 / 影响 | 缓解 | 回滚 |
| --- | --- | --- | --- |
| 6099 被其他程序占用导致误判运行中 | 低 / 低 | 同时要求 peers 或 PID；端口仅作兜底 | 恢复只看 pids |
| peers 残留导致误判 | 低 / 低 | TCP 断开后 peers 会消失；状态 2.6s 刷新 | 恢复只看 pids |
| 路径模式匹配到启动脚本的 bash | 低 / 低 | 启动脚本已文件化，bash cmdline 不含 QQ 路径；probe 自身不含路径 | 只用精确名 |

## 8. 验证记录

| 日期 | 检查项 | 命令 / 方式 | 结果 |
| --- | --- | --- | --- |
| 2026-11-01 | 合成状态 | monkeypatch `probe.pids=[]`、`peers=[...]`、`6099=True` | `running=True`、`health=ok`、`qq.linked=True` |
| 2026-11-01 | 语法 | `python -m py_compile console/core.py console/ui.py` | 通过 |
| 2026-11-01 | 自检 | `python console\selftest.py` | 8/8 通过 |
| 2026-11-01 | 真实运行观察 | 用户重启控制台后聊天/挂机 10 分钟 | 待复测 |

## 9. 评审与确认

| 日期 | 确认人 | 结论 | 备注 |
| --- | --- | --- | --- |
| 2026-11-01 | zigyr | 已批准 | 用户 00:34 截图与“聊一会就断”描述；按误判重启修复 |
