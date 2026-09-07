from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def root():
    return {"status": "Nawaloka backend is working"}


@app.post("/chat")
def chat():
    return {"message": "Agent will go here"}