from fastapi import FastAPI

from api.jd import router as jd_router
from api.resume import router as resume_router
from api.scoring import router as scoring_router
from api.talent import router as talent_router


app = FastAPI(
    title="Resume Agent API"
)


#注册路由
app.include_router(
    jd_router
)
app.include_router(resume_router)
# 注册以后swagger就会出现 POST /api/scoring/job-match
app.include_router(scoring_router)
app.include_router(talent_router)


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