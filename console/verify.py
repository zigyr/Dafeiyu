# -*- coding: utf-8 -*-
import sys, time
sys.path.insert(0, r"F:\dafeiyu\console")
import server as c

time.sleep(7)
s = c.status()
print("ASTRBOT_RUNNING:", s["astrbot"]["running"])
print("NAPCAT_RUNNING:", s["napcat"]["running"])
print("QQ_LINKED:", s["qq"]["linked"])
print("GATEWAY:", s["napcat"]["wsl_gateway"])

r = c.wsl_bash("tail -n 60 /root/napcat-run.log | sed 's/\\x1b\\[[0-9;]*m//g'")
t = r.stdout or ""
print("NAPCAT_LOG_UTF8_OK:", ("接收" in t or "发送" in t))
sample = t[-260:].encode("unicode_escape").decode("ascii")
print("NAPCAT_SAMPLE:", sample)

astr = c.read_tail(c.ASTRBOT_LOG, 60)
print("ASTRBOT_LOG_LEN:", len(astr))
print("ASTRBOT_LOG_UTF8_OK:", any(x in astr for x in ["已启动", "连接", "插件", "WebUI", "运行"]))
asample = astr[-300:].encode("unicode_escape").decode("ascii")
print("ASTRBOT_SAMPLE:", asample)
