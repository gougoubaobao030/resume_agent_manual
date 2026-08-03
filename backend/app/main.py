from fastapi import FastAPI

app = FastAPI(
    title="Resume Agent API"
)

@app.get("/")
def root():
    return {
        "message": "Resume Agent Backend Running"
    }