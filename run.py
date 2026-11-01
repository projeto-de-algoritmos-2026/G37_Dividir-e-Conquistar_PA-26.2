import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent / "backend"


def main():
    print("Subindo backend (porta 8000)...\n")
    processo = subprocess.Popen([sys.executable, "main.py"], cwd=BACKEND_DIR)

    print("Backend:      http://127.0.0.1:8000")
    print("Documentacao: http://127.0.0.1:8000/docs")
    print("\nCtrl+C para parar.\n")

    try:
        processo.wait()
    except KeyboardInterrupt:
        print("\nEncerrando...")
        processo.terminate()


if __name__ == "__main__":
    main()