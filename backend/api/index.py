from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pipeline import run_pipeline


app = FastAPI(title="Nawaloka AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    model: str
    session_id: str | None = None


@app.get("/")
def root():
    return {"status": "Nawaloka backend is working"}


@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        answer = await run_pipeline(request.message, request.model)
        return {"message": answer}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
