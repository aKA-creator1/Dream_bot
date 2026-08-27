import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from app import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5050"))
    uvicorn.run(app, host="0.0.0.0", port=port)
