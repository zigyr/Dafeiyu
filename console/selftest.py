# -*- coding: utf-8 -*-
"""不依赖 WSL / 服务的本地自检。"""
from __future__ import annotations

import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))

import core  # noqa: E402
from settings import Settings  # noqa: E402


def main() -> int:
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        print(("[ OK ] " if cond else "[FAIL] ") + name + ((" · " + detail) if detail else ""))
        ok = ok and bool(cond)

    check("Python", sys.version_info >= (3, 10), sys.version.split()[0])
    check("psutil", True)
    check("ANSI 清理", core.strip_ansi("\x1b[32mhello\x1b[0m") == "hello")
    matrix = core.Backend._qr_matrix("https://example.com/dafeiyu?t=1")
    check("离线二维码", len(matrix) > 20 and len(matrix) == len(matrix[0]), "%dx%d" % (len(matrix), len(matrix[0])))
    st = Settings.load()
    check("配置读取", st.account.isdigit(), st.account)
    check("AstrBot 配置", Path(st.astrbot_cwd, "data", "cmd_config.json").exists())
    check("WSL 命令行", bool(core.WSL._find_exe()))
    check("日志目录", core.LOG_DIR.exists(), str(core.LOG_DIR))
    print("\n结果:", "通过" if ok else "有失败项")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
