import os
import psutil

current_pid = os.getpid()
uvicorn_pid = None

for p in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        pname = (p.info.get('name') or '').lower()
        if 'python' not in pname:
            continue
        pid = p.info['pid']
        if pid == current_pid:
            continue
        cmd = ' '.join(p.info.get('cmdline') or [])
        if 'uvicorn' in cmd:
            uvicorn_pid = pid
            print(f'Preserving backend PID {pid}')
            continue
        print(f'Terminating PID {pid}: {cmd[:50]}')
        p.kill()
    except Exception as e:
        print(f'Error on {pid}: {e}')

print('Done cleaning.')
