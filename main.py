import threading
import webbrowser
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from routers import inventory, layout

# NEW: application startup stays here; database and route logic live in dedicated modules.
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="Pick-to-Light API",
    description="API para controlar el sistema de localizador de almacenes",
    version="1.0.0",
)

# NEW: register independent route modules while preserving the existing public URLs.
app.include_router(inventory.router)
app.include_router(layout.router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def read_root():
    # The temporary local website remains available until the final frontend replaces it.
    return FileResponse(STATIC_DIR / "index.html")


if __name__ == "__main__":
    # NEW: start the browser on the warehouse website; API documentation remains at /docs.
    site_url = "http://127.0.0.1:8000"
    print(f"Open Pick-to-Light here: {site_url}")
    threading.Timer(1.5, lambda: webbrowser.open(site_url)).start()
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
