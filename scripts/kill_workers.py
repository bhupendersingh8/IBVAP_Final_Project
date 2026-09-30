import psutil

killed = 0
for p in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        cmd = ' '.join(p.info.get('cmdline') or []).lower()
        if 'main_inference_worker.py' in cmd:
            pid = p.info['pid']
            print(f'Terminating worker PID {pid}')
            p.kill()
            killed += 1
    except Exception as e:
        pass
print(f'Terminated {killed} stale worker processes.')
