# Windows EXE Launcher

This folder contains a PyInstaller wrapper for Vamos Subscription Tracker.

Build from the project root:

```powershell
.\launcher\build_exe.ps1
```

Output:

```text
dist\Vamos Subscription Tracker.exe
```

The EXE starts the FastAPI backend on `127.0.0.1:8000`, serves the built frontend on `127.0.0.1:5174`, opens the browser, and stores SQLite data in:

```text
%APPDATA%\Vamos Subscription Tracker\app.db
```
