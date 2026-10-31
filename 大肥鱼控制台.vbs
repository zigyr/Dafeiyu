' Dafeiyu Console launcher (no console window)
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = "F:\dafeiyu"
sh.Run """F:\Compilers\python3\pythonw.exe"" ""F:\dafeiyu\console\app.py""", 0, False
