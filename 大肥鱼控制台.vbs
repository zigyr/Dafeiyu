' Dafeiyu Console launcher (portable, no console window)
Option Explicit

Dim fso, sh, base, appPath, py, candidates, i, p, pathEnv, cand
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")

' Resolve the project root from this script, not from the current directory.
base = fso.GetParentFolderName(WScript.ScriptFullName)
appPath = fso.BuildPath(base, "console\app.py")
If Not fso.FileExists(appPath) Then
    MsgBox "Cannot find console\app.py." & vbCrLf & _
           "Keep this launcher in the project root, next to the console folder.", _
           16, "Dafeiyu Console"
    WScript.Quit 1
End If

' 1) Explicit override: DAFEIYU_PYTHONW=C:\path\to\pythonw.exe
py = sh.ExpandEnvironmentStrings("%DAFEIYU_PYTHONW%")
If py = "%DAFEIYU_PYTHONW%" Then py = ""
If py <> "" Then
    If Not fso.FileExists(py) Then py = ""
End If

' 2) Portable / common Python locations.
If py = "" Then
    candidates = Array( _
        fso.BuildPath(base, "python\pythonw.exe"), _
        "F:\Compilers\python3\pythonw.exe", _
        sh.ExpandEnvironmentStrings("%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe"), _
        sh.ExpandEnvironmentStrings("%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"), _
        sh.ExpandEnvironmentStrings("%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe"), _
        sh.ExpandEnvironmentStrings("%ProgramFiles%\Python313\pythonw.exe"), _
        sh.ExpandEnvironmentStrings("%ProgramFiles%\Python312\pythonw.exe"), _
        "C:\Python313\pythonw.exe", _
        "C:\Python312\pythonw.exe" _
    )
    For i = 0 To UBound(candidates)
        If fso.FileExists(candidates(i)) Then
            py = candidates(i)
            Exit For
        End If
    Next
End If

' 3) Last resort: pythonw.exe on PATH.
If py = "" Then
    pathEnv = sh.ExpandEnvironmentStrings("%PATH%")
    For Each p In Split(pathEnv, ";")
        p = Trim(Replace(p, """", ""))
        If p <> "" Then
            cand = fso.BuildPath(p, "pythonw.exe")
            If fso.FileExists(cand) Then
                py = cand
                Exit For
            End If
        End If
    Next
End If

If py = "" Then
    MsgBox "Cannot find pythonw.exe." & vbCrLf & vbCrLf & _
           "Install Python 3.12 + PySide6, or set the environment variable " & _
           "DAFEIYU_PYTHONW to the full path of pythonw.exe.", _
           16, "Dafeiyu Console"
    WScript.Quit 1
End If

sh.CurrentDirectory = base
sh.Run """" & py & """ """ & appPath & """", 0, False
