import os
import sys
from pathlib import Path
import uvicorn

# Asosiy ildiz papkani python pathga qo'shamiz
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

if __name__ == "__main__":
    uvicorn.run(
        "services.auth.app.main:app",
        host="127.0.0.1",
        port=8001,
        reload=True
    )
