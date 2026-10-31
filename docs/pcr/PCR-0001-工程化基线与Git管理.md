# PCR-0001 · 工程化基线与 Git 管理

| 字段 | 内容 |
| --- | --- |
| 编号 | PCR-0001 |
| 标题 | 工程化基线与 Git 管理 |
| 状态 | 已批准 |
| 提出日期 | 2026-10-31 |
| 需求方 | zigyr |
| 实施方 | DSH Agent |
| 关联提交 | 待回填 |
| 关联 PCR | — |

## 1. 背景与问题

大肥鱼控制台（PySide6 + AstrBot + NapCat）目前仅在本机以脚本方式运行，存在五个问题：

1. **无版本控制**：无法追溯改动、无法回滚、换机后无法恢复。
2. **目录混杂**：`console/` 源码与 `QQ/`（约 1.17 GB）、`napcat/`（110 MB）、`_download/`（148 MB）、`logs/`、`astrbot/` 运行时数据混放在根目录。
3. **历史脚本散落**：`astrbot/` 下有 13 个一次性运维脚本；`console/server.py` 是旧 Web 版控制台，`verify.py` 仍依赖它。
4. **敏感信息明文**：`console/settings.json`、根目录 `linux-onebot11.json` 含 OneBot token，`astrbot/ws_token.txt` 含运行 token，而目标仓库是公开仓库。
5. **无变更与交接文档**：需求、决策、验证过程不可回溯。

## 2. 需求提炼

原始诉求（2026-10-31）：

> 对于我每次的需求，就进行提炼并与我进行沟通协商，生成专业的 PCR，随后记录在项目文件夹的对应位置，然后再进行代码去解决问题。对于这个项目文件夹进行整理，同时按照企业开发的严谨性，用 git 进行管理；关联 https://github.com/zigyr/Dafeiyu.git 并完成一次 push；先省略 README.md；项目文件夹中放一个任务交接文档，记录每次对项目功能的增删改操作。

结构化：

- **问题**：项目缺乏变更管理、版本控制与目录治理。
- **目标**：建立可复用的 PCR 流程；完成 Git 基线与首次推送；整理目录；沉淀交接文档。
- **非目标**：见 3.2。
- **验收**：见第 6 节。

## 3. 范围与影响

### 3.1 范围内

| 类型 | 内容 |
| --- | --- |
| 新增 | `.gitignore`、`.gitattributes`、`docs/变更管理.md`、`docs/pcr/_模板.md`、本 PCR、`任务交接文档.md`、`console/settings.example.json`、`tools/setup/`、`archive/legacy/` |
| 移动 | `astrbot/*.py`（13 个）→ `tools/setup/`；`console/server.py`、`console/verify.py` → `archive/legacy/` |
| 修改 | `console/verify.py` 的 `sys.path`；`使用说明.md` 的文件树与变更管理章节 |
| 仓库 | `git init`、5 次原子提交、关联 `origin`、推送 `main` |
| 删除 | `console/vendor/qrcode/**/__pycache__` 等缓存（可再生成） |

### 3.2 范围外（非目标）

- 不修改控制台功能逻辑、界面与后端行为。
- 不重构 `console/` 为 `src/` 包结构（留待后续 PCR）。
- 不迁移 `QQ/`、`napcat/`、`_download/` 等运行时资产。
- 不创建 `README.md`（按要求暂缓）。
- 不调整 WSL / NapCat / AstrBot 运行环境。

### 3.3 影响分析

| 维度 | 影响 | 结论 |
| --- | --- | --- |
| 启动路径 | `大肥鱼控制台.vbs` 仍指向 `console/app.py` | 无影响 |
| 配置路径 | `settings.json` 位置不变 | 无影响 |
| 运行时 | 移动的脚本不参与运行时 | 无影响 |
| 旧工具 | `verify.py` 移动后需修正导入路径 | 已处理 |
| 安全 | token / 密钥全部移出跟踪范围 | 风险消除 |
| 仓库体积 | 仅源码 + 文档 + 预览图，约 1.5 MB | 可正常推送 |

## 4. 方案与取舍

### 4.1 整理力度

- **方案 A（采纳）**：保守分层。保留 `console/` 与启动器路径，新增 `docs/`、`tools/`、`archive/`。
- 方案 B：只加文档与 Git，不移动文件。整理效果不足。
- 方案 C：深度重构为 `src/dafeiyu` 包。改动面大、回归成本高，不适合作为基线变更。

### 4.2 跟踪范围

- **方案 A（采纳）**：源码 + 文档 + 预览图；运行时 / 二进制 / 密钥忽略。
- 方案 B：只跟踪 `console/`，文档不入库，不利于交接。
- 方案 C：包含运行时资产，超过 1.2 GB，GitHub 拒收，不可行。

### 4.3 敏感信息

- **方案 A（采纳）**：`settings.json`、`ws_token.txt`、`linux-onebot11.json`、`astrbot/data` 全部忽略，新增 `settings.example.json`。
- 方案 B：脱敏后提交真实配置，仍会泄露账号与拓扑。
- 方案 C：原样提交，公开仓库会泄露 token，不可接受。

## 5. 实施计划

1. 建立 `.gitignore` / `.gitattributes`，初始化仓库并提交基线。
2. 编写 `docs/变更管理.md`、`docs/pcr/_模板.md`、本 PCR。
3. 归档一次性脚本与旧 Web 控制台，修正 `verify.py` 导入路径。
4. 新增 `console/settings.example.json`，更新 `使用说明.md`。
5. 编写 `任务交接文档.md`，回填验证记录。
6. 关联远端并推送，核对远端状态。

## 6. 验收标准

- [ ] 仓库存在 5 次语义化提交，`git status` 干净。
- [ ] 远端 `main` 与本地一致，GitHub 可见提交。
- [ ] 跟踪文件中不含 OneBot token / ws token / QQ 密码。
- [ ] `console/selftest.py` 全部通过。
- [ ] `大肥鱼控制台.vbs` 启动路径未改变。
- [ ] `docs/pcr/` 与 `任务交接文档.md` 齐全，`使用说明.md` 文件树与实际一致。

## 7. 风险与回滚

| 风险 | 概率 / 影响 | 缓解 | 回滚 |
| --- | --- | --- | --- |
| 移动脚本导致引用失效 | 低 / 低 | 仅移动非运行时脚本；`verify.py` 同步修正 | `git revert` 或移回原路径 |
| 公开仓库泄露密钥 | 中 / 高 | 忽略规则 + 推送前密钥扫描 | 立即重置 token，必要时清理历史 |
| 大文件误入库 | 低 / 中 | `.gitignore` 覆盖 + `git status` 复核 | `git rm --cached` 后重写历史 |
| 本机 Git TLS 异常 | 中 / 低 | 仓库级 `http.sslBackend=openssl` | 删除该项配置 |
| 推送失败 | 低 / 中 | 使用已保存凭据；失败则保留本地提交待重试 | 保留本地仓库，重试推送 |

## 8. 验证记录

| 日期 | 检查项 | 命令 / 方式 | 结果 |
| --- | --- | --- | --- |
| 2026-10-31 | 待回填 | | |

## 9. 评审与确认

| 日期 | 确认人 | 结论 | 备注 |
| --- | --- | --- | --- |
| 2026-10-31 | zigyr | 已批准 | 确认：保守分层 / 源码+文档+预览图入库 / 密钥全部排除并给样例 |
