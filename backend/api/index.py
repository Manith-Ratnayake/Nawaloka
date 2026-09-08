import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pipeline import run_pipeline_stream


app = FastAPI(title="Nawaloka AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HistoryMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    model: str
    session_id: str | None = None
    history: list[HistoryMessage] = []


@app.get("/")
def root():
    return {"status": "Nawaloka backend is working"}


@app.post("/chat")
async def chat(request: ChatRequest):
    async def event_stream():
        try:
            history = [{"role": m.role, "content": m.content} for m in request.history]
            async for event in run_pipeline_stream(
                request.message,
                request.model,
                session_id=request.session_id,
                history=history,
            ):
                if event.get("phase") == "done":
                    yield json.dumps({
                        "phase": "done",
                        "message": event["answer"],
                        "debug": event["debug"],
                    }, default=str) + "\n"
                else:
                    yield json.dumps(event, default=str) + "\n"
        except ValueError as error:
            yield json.dumps({"phase": "error", "error": str(error), "status": 400}) + "\n"
        except Exception as error:
            yield json.dumps({"phase": "error", "error": str(error), "status": 500}) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")