import os
import sys
from pathlib import Path

# Keep generated Python cache files out of the project folders.
sys.dont_write_bytecode = True

# Ensure backend/python directory is in sys.path so app imports work seamlessly
PYTHON_DIR = Path(__file__).resolve().parent
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print("Starting Government Accident Detection & Alert System Backend (Python FastAPI)...")
    print(f"Open the website at: http://127.0.0.1:{port}")

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port
    )
