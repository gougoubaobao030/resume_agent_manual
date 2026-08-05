from fastapi import FastAPI

from api.jd import router as jd_router


app = FastAPI(
    title="Resume Agent API"
)


#注册路由
app.include_router(
    jd_router
)


@app.get("/")
def root():
    return {
        "message": "Resume Agent Backend Running"
    }

@app.get("/health")
def health():
    return {
        "status": "ok"
    }