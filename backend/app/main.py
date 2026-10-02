from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles

from api.auth import get_current_user, router as auth_router
from api.candidates import router as candidates_router
from api.jd import router as jd_router
from api.resume import router as resume_router
from api.scoring import router as scoring_router
from api.talent import router as talent_router
from api.translation import router as translation_router
from api.users import router as users_router


app = FastAPI(title="Resume Agent API")

avatars_path = Path(__file__).resolve().parents[2] / "data" / "avatars"
avatars_path.mkdir(parents=True, exist_ok=True)
app.mount("/media/avatars", StaticFiles(directory=avatars_path), name="avatars")

# 登录与当前用户接口保持公开；它们各自决定是否需要当前用户。
app.include_router(auth_router)
app.include_router(users_router)

# 业务接口统一要求登录，具体 API 函数签名暂时无需改变。
protected = [Depends(get_current_user)]
app.include_router(jd_router, dependencies=protected)
app.include_router(candidates_router, dependencies=protected)
app.include_router(resume_router, dependencies=protected)
app.include_router(scoring_router, dependencies=protected)
app.include_router(talent_router, dependencies=protected)
app.include_router(translation_router, dependencies=protected)


@app.get("/")
def root():
    return {"message": "Resume Agent Backend Running"}


@app.get("/health")
def health():
    return {"status": "ok"}
