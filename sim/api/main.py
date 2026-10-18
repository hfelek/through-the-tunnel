from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Through the Tunnel")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"])


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
