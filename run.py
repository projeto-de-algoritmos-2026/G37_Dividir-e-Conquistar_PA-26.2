"""
Sobe o backend (FastAPI/uvicorn) e o frontend (Vite) juntos,
com um unico comando: `python3 run.py`

O frontend agora e um projeto React + Vite: precisa do Node.js 18+ e do npm.
Na primeira vez (sem frontend/node_modules), o run.py roda `npm install` sozinho.

Pressione Ctrl+C para derrubar os dois processos de uma vez.
"""

import shutil
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).parent
BACKEND_DIR = RAIZ / "backend"
FRONTEND_DIR = RAIZ / "frontend"


def achar_npm():
    """Descobre o executavel do npm de forma multiplataforma.

    Tenta `npm` no PATH e, no Windows, cai para `npm.cmd`. Devolve None se
    nao encontrar nada.
    """
    npm = shutil.which("npm")
    if npm:
        return npm
    # no Windows o npm costuma ser um .cmd
    return shutil.which("npm.cmd")


def main():
    print("Subindo backend (porta 8000) e frontend (porta 5500)...\n")

    processo_backend = subprocess.Popen([sys.executable, "main.py"], cwd=BACKEND_DIR)

    # pequena pausa para o backend comecar a subir antes do frontend
    time.sleep(1)

    npm = achar_npm()
    if npm is None:
        print(
            "\nNode.js/npm nao encontrado. Instale o Node 18+ e rode "
            "npm install em frontend/."
        )
        print("Subindo apenas o backend.\n")
        print("Backend:      http://127.0.0.1:8000  (docs em /docs)")
        print("\nCtrl+C para parar.\n")
        try:
            processo_backend.wait()
        except KeyboardInterrupt:
            print("\nEncerrando...")
            processo_backend.terminate()
        return

    # na primeira vez, instala as dependencias do frontend antes de subir o Vite
    if not (FRONTEND_DIR / "node_modules").exists():
        print("Instalando dependencias do frontend (npm install)...")
        subprocess.run([npm, "install"], cwd=FRONTEND_DIR, check=True)

    processo_frontend = subprocess.Popen([npm, "run", "dev"], cwd=FRONTEND_DIR)

    print("\nBackend:      http://127.0.0.1:8000  (docs em /docs)")
    print("Frontend:     http://127.0.0.1:5500")
    print("\nCtrl+C para parar os dois.\n")

    try:
        processo_backend.wait()
        processo_frontend.wait()
    except KeyboardInterrupt:
        print("\nEncerrando...")
        processo_backend.terminate()
        processo_frontend.terminate()


if __name__ == "__main__":
    main()
