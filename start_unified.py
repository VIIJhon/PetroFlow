import subprocess
import sys
import os
import threading
import signal

def run_process(cmd, cwd, prefix):
    # Determine encoding depending on the platform, usually utf-8 is fine
    process = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    
    def read_output():
        for line in process.stdout:
            sys.stdout.write(f"{prefix} | {line}")
            sys.stdout.flush()
            
    thread = threading.Thread(target=read_output, daemon=True)
    thread.start()
    return process

if __name__ == "__main__":
    root_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(root_dir, "backend")
    frontend_dir = os.path.join(root_dir, "frontend")
    
    print("\n=======================================================")
    print("  PETROFLOW V3.0 - UNIFIED DEV LAUNCHER")
    print("=======================================================\n")
    
    # 1. Kill old processes on port 8000 and 3000
    subprocess.run("for /f \"tokens=5\" %a in ('netstat -aon ^| findstr \":8000\" 2^>nul') do taskkill /PID %a /F >nul 2>&1", shell=True)
    subprocess.run("for /f \"tokens=5\" %a in ('netstat -aon ^| findstr \":3000\" 2^>nul') do taskkill /PID %a /F >nul 2>&1", shell=True)
    
    # 2. Start Backend
    backend_cmd = "venv\\Scripts\\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
    backend_proc = run_process(backend_cmd, backend_dir, "[BACKEND]")
    
    # 3. Start Frontend
    frontend_cmd = "set GENERATE_SOURCEMAP=false && set BROWSER=none && npm start"
    frontend_proc = run_process(frontend_cmd, frontend_dir, "[FRONTEND]")
    
    try:
        backend_proc.wait()
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down servers...")
        backend_proc.terminate()
        frontend_proc.terminate()
        sys.exit(0)
