# PCR-0007 · NapCat 启动脚本文件化与字面路径

| 字段 | 内容 |
| --- | --- |
| 编号 | PCR-0007 |
| 标题 | NapCat 启动脚本文件化与字面路径 |
| 状态 | 已完成（真实启动待用户复测） |
| 提出日期 | 2026-10-31 |
| 需求方 | zigyr |
| 实施方 | DSH Agent |
| 关联提交 | 本 PCR 对应提交 |
| 关联 PCR | PCR-0005（自匹配误杀修复） |

## 1. 背景与问题

PCR-0005 修复了 `pkill -f` 自匹配后，用户 23:53–23:54 的新日志仍失败：

```text
--- launcher stderr ---
bash: line 7: : No such file or directory
bash: line 16: : No such file or directory
[23:54:43] 启动遇到问题 · NapCat 启动失败（启动器无输出）
```

对应脚本第 7/16 行正是两处日志重定向 `: > "$L"` 与 `} >> "$L"`；
`$L` 在执行时为空，导致：

- `/root/napcat-run.log` 没有被清空，读到的还是 21:15 的旧日志；
- 启动器没有产生新日志；
- 最终报“启动器无输出”。

同时，旧版通过 `bash -lc "<近 2KB 脚本>"` 内联执行，受 login profile、
引号/变量展开、环境继承影响，难以稳定复现。

## 2. 需求提炼

- **目标**：
  1. 启动脚本写入 `/root/napcat-start.sh`，用 `bash` 文件执行，不再内联传参；
  2. QQ 路径、日志路径、screen/xvfb 命令全部使用生成时的字面量，不依赖 `$Q`/`$L` 环境；
  3. 所有进程清理只用 `pkill -x`，彻底移除 `pkill -f` 的路径模式；
  4. 启动/读取日志对空的 `layout["log"]` 有兜底；
  5. 失败信息包含 QQ 路径、日志路径、启动器路径，便于下轮定位。
- **非目标**：
  - 不改变 NapCat/QQ 版本、账号、登录方式；
  - 不改变 AstrBot 启动与 OneBot 校准。

## 3. 范围与影响

| 类型 | 内容 |
| --- | --- |
| 修改 | `core.NapCat.start()`：生成 `/root/napcat-start.sh`；字面路径；`bash file` 执行；失败信息带路径 |
| 修改 | `core.NapCat.stop()`：去掉 `pkill -f` 与 Q 变量，仅精确进程名 |
| 修改 | `core.NapCat.probe/read_log/read_qq_log/read_qr_file`：日志/二维码路径兜底 |
| 新增 | 本 PCR |
| 数据 / 配置 | 无 |
| 依赖 | 无 |
| 安全 | 启动脚本以 root 写入 `/root`，运行 NapCat |

## 4. 方案与取舍

| 方案 | 说明 | 取舍 |
| --- | --- | --- |
| A（采纳） | 写 `/root/napcat-start.sh`，字面路径，`bash file` | 可读、可复现、可手工执行 |
| B | 继续内联 `bash -lc`，只修变量 | 仍受 profile/引号影响，难定位 |
| C | 用 systemd 服务 | 改动大，超出范围 |

## 5. 实施计划

1. `NapCat.start` 用 `wsl.write` 写 `/root/napcat-start.sh`；失败直接返回明确错误。
2. 脚本中 `: > '/root/napcat-run.log'`、`>> '/root/napcat-run.log'`、`xvfb-run -a '/root/Napcat/opt/QQ/qq'` 等全部字面量。
3. 清理：`pkill -x qq/QQ/xvfb-run/Xvfb`；移除 `pkill -f`。
4. `bash /root/napcat-start.sh` 执行；pid 仍从 fd 3 输出。
5. 失败信息增加 `QQ=... LOG=... LAUNCHER=...`。
6. 读取日志/二维码时对空 layout 兜底。
7. 真实启动复测。

## 6. 验收标准

- [x] 生成的 `/root/napcat-start.sh` 不含 `"$L"` 重定向，日志路径为字面量。
- [x] 脚本中不再有 `pkill -f`。
- [x] `start` 通过 `bash <file>` 执行，失败信息含 QQ/LOG/LAUNCHER。
- [x] `probe/read_log/read_qq_log/read_qr_file` 有路径兜底。
- [x] `py_compile` / `selftest.py` 通过。
- [ ] 用户重启控制台后一键启动，NapCat 进程出现（真实 WSL 复测）。

## 7. 风险与回滚

| 风险 | 概率 / 影响 | 缓解 | 回滚 |
| --- | --- | --- | --- |
| `/root/napcat-start.sh` 写入失败 | 低 / 中 | 返回明确错误，检查 WSL 权限 | 恢复内联脚本 |
| 字面路径含空格/特殊字符 | 低 / 低 | 当前路径无空格；`shlex.quote` 生成 | 调整路径 |
| 脚本文件被外部修改 | 低 / 低 | 每次启动覆盖 | 删除文件重试 |

## 8. 验证记录

| 日期 | 检查项 | 命令 / 方式 | 结果 |
| --- | --- | --- | --- |
| 2026-10-31 | 生成脚本 | monkeypatch `wsl.write/run` 捕获 | 2339 字节；路径 `/root/napcat-start.sh`；无 `$L` 重定向 |
| 2026-10-31 | 自匹配检查 | 检索脚本 | 无 `pkill -f`；仅 `pkill -x` |
| 2026-10-31 | 语法 | `python -m py_compile console/core.py` | 通过 |
| 2026-10-31 | 自检 | `python console\selftest.py` | 8/8 通过 |
| 2026-10-31 | 真实 WSL 启动 | 需用户重启控制台后一键启动 | 待复测 |

## 9. 评审与确认

| 日期 | 确认人 | 结论 | 备注 |
| --- | --- | --- | --- |
| 2026-10-31 | zigyr | 已批准 | 用户回传 23:54 启动器空变量错误；按日志改为文件化+字面路径 |
