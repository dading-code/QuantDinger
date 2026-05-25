Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\www\workai\qd-ai\QuantDinger\backend_api_python"
WshShell.Run "cmd /c set PYTHONIOENCODING=utf-8 & python run.py", 0, False
