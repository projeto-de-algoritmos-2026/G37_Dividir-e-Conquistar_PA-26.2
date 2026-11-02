"""
Sobe o backend (FastAPI/uvicorn) e o frontend (servidor HTTP simples) juntos,
com um unico comando: `python3 run.py`

Pressione Ctrl+C para derrubar os dois processos de uma vez.
"""

import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).parent
BACKEND_DIR = RAIZ / "backend"
FRONTEND_DIR = RAIZ / "frontend"


def main():
    print("Subindo backend (porta 8000) e frontend (porta 5500)...\n")

    processo_backend = subprocess.Popen([sys.executable, "main.py"], cwd=BACKEND_DIR)

    # pequena pausa para o backend comecar a subir antes do frontend
    time.sleep(1)

    processo_frontend = subprocess.Popen(
        [sys.executable, "-m", "http.server", "5500"], cwd=FRONTEND_DIR
    )

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