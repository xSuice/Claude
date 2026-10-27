"""PC-side telemetry snapshot (strict schema, no process names). Used by liveness_reporter.py; failures never affect liveness."""
import json,shutil,subprocess

def snapshot():
    import psutil
    d={'cpu_pct':round(psutil.cpu_percent(interval=0.5),1),'ram_pct':round(psutil.virtual_memory().percent,1),'gpu':None}
    exe=shutil.which('nvidia-smi')
    if exe:
        try:
            r=subprocess.run([exe,'--query-gpu=utilization.gpu,temperature.gpu,memory.used,memory.total','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=8,creationflags=0x08000000)
            u,t,mu,mt=[float(x) for x in r.stdout.strip().splitlines()[0].split(',')]
            d['gpu']={'util_pct':u,'temp_c':t,'vram_used_mb':mu,'vram_total_mb':mt}
        except Exception:
            d['gpu']=None
    return d

if __name__=='__main__':
    print(json.dumps(snapshot()))
