from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from rag.pipeline import run_rag


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


@app.get("/")
def root():
    return {"status": "Nawaloka backend is working"}


@app.post("/chat")
def chat(request: ChatRequest):
    # answer = run_rag(request.message)
    return {"message": request}
