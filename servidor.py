#!/usr/bin/env python3
"""servidor.py — launcher apenas. Backend isolado em backend/."""
import atexit, http.client, subprocess, sys, time
from functools import partial
from http.server import HTTPServer
from frontend import FrontendHandler

HOST, BPORT, FPORT = "127.0.0.1", 8001, 8000

def iniciar_backend():
    try:
        c=http.client.HTTPConnection(HOST,BPORT,timeout=1); c.request("GET","/api/health"); r=c.getresponse()
        if r.status<500: print(f"[launcher] backend já em {BPORT}"); c.close(); return None
        c.close()
    except: pass
    print(f"[launcher] subindo backend -> python -m backend.api :{BPORT}")
    p=subprocess.Popen([sys.executable,"-m","backend.api"],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
    atexit.register(lambda: (p.terminate(), p.wait(timeout=2)) if p.poll() is None else None)
    for i in range(15):
        time.sleep(0.5)
        try:
            c=http.client.HTTPConnection(HOST,BPORT,timeout=1); c.request("GET","/api/health"); r=c.getresponse(); r.read(); c.close()
            print(f"[launcher] backend OK :{BPORT}"); return p
        except:
            if i==5: print("[launcher] aguardando...")
    print("[launcher] fallback ativo"); return p

if __name__=="__main__":
    import os as _os
    _demo = _os.getenv("DEMO_PASS", "dev_only_change_me")
    print("=== Sossego Launcher ===")
    print("servidor.py só inicia; backend seguro em backend/")
    bp=iniciar_backend()
    print(f"Frontend http://localhost:{FPORT}/  Backend http://{HOST}:{BPORT}/api/health")
    print(f"Login admin/{_demo} aluno/{_demo}  Ctrl+C para parar")
    try: HTTPServer(("",FPORT), partial(FrontendHandler, directory="web")).serve_forever()
    except KeyboardInterrupt:
        print("\n[launcher] parando..."); 
        if bp: 
            try: bp.terminate()
            except: pass
        sys.exit(0)
