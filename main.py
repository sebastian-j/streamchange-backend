from fastapi import FastAPI, WebSocket

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok"}