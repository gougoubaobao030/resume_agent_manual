import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from pwdlib import PasswordHash
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from models import UserModel, UserSessionModel
from schemas.auth import UserPublic

# 核心是数据库不是明文密码
# 想要浏览器记住，下次依旧打开就是登录状态，那就需要用到cookie
SESSION_COOKIE_NAME = "resume_agent_session"
# 登录默认有效期 7天
SESSION_MAX_AGE_SECONDS = 7 * 24 * 60 * 60
# 密码加密，验证器
password_hasher = PasswordHash.recommended()

# 统一转小写
def normalize_username(username: str) -> str:
    return username.strip().lower()


# 数据库里存一串hash结果
def hash_password(password: str) -> str:
    return password_hasher.hash(password)

# 密码也是把密码 和 数据库的哈希一起拿来验证
# 不存在解密，就是把拿到的对比hash，看看是不是一样
def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)

# 服务器生成随机token给浏览器，但是
# 数据库存的是hash结果
# 防的是数据库泄露
def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

# 处理时区，时间有时区
def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)

# 数据库数据里给前端的内容
def to_user_public(user: UserModel) -> UserPublic:
    return UserPublic(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        avatar_path=user.avatar_path,
        preferred_language=user.preferred_language,
    )


# 每次操作都是通过session管理的，session在前面db的时候会扔给fastapi
# session就是从我们database.py里的get_db()得到
# 本质是一个操作工具
def authenticate_user(db: Session, username: str, password: str) -> UserModel | None:
    user = db.scalar(
        select(UserModel).where(UserModel.username == normalize_username(username))
    )
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


# 登录成功 生成raw_token
def create_user_session(db: Session, user_id: str) -> str:
    now = datetime.now(timezone.utc)
    # 清楚旧缓存
    db.execute(delete(UserSessionModel).where(UserSessionModel.expires_at <= now))
    raw_token = secrets.token_urlsafe(32)
    db.add(UserSessionModel(
        token_hash=hash_session_token(raw_token),
        user_id=user_id,
        created_at=now,
        expires_at=now + timedelta(seconds=SESSION_MAX_AGE_SECONDS),
    ))
    db.commit()
    # 返回给浏览器， 存在浏览器cookie里
    return raw_token

# 整个过程叫做session登录
def get_user_by_session_token(db: Session, raw_token: str) -> UserModel | None:
    # get session也就是orm内部方法
    session_row = db.get(UserSessionModel, hash_session_token(raw_token))
    if session_row is None:
        return None
    if _as_utc(session_row.expires_at) <= datetime.now(timezone.utc):
        db.delete(session_row)
        db.commit()
        return None
    user = db.get(UserModel, session_row.user_id)
    return user if user is not None and user.is_active else None


def delete_user_session(db: Session, raw_token: str) -> None:
    session_row = db.get(UserSessionModel, hash_session_token(raw_token))
    if session_row is not None:
        # 删掉
        db.delete(session_row)
        # 操作正式提交到数据库
        db.commit()


def create_user(
    db: Session,
    *,
    username: str,
    password: str,
    display_name: str | None = None,
    preferred_language: str = "zh-CN",
) -> UserModel:
    normalized_username = normalize_username(username)
    if db.scalar(select(UserModel.id).where(UserModel.username == normalized_username)):
        raise ValueError("用户名已存在")
    if len(password) < 8:
        raise ValueError("密码至少需要8个字符")
    user = UserModel(
        id=f"user_{uuid4().hex}",
        username=normalized_username,
        password_hash=hash_password(password),
        display_name=display_name.strip() if display_name else None,
        preferred_language=preferred_language,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def reset_user_password(db: Session, username: str, new_password: str) -> UserModel:
    if len(new_password) < 8:
        raise ValueError("密码至少需要8个字符")
    user = db.scalar(
        select(UserModel).where(UserModel.username == normalize_username(username))
    )
    if user is None:
        raise ValueError("用户不存在")
    user.password_hash = hash_password(new_password)
    db.execute(delete(UserSessionModel).where(UserSessionModel.user_id == user.id))
    db.commit()
    db.refresh(user)
    return user


def change_user_password(
    db: Session,
    user: UserModel,
    current_password: str,
    new_password: str,
) -> str:
    if not verify_password(current_password, user.password_hash):
        raise ValueError("原密码不正确")
    if len(new_password) < 8:
        raise ValueError("新密码至少需要8个字符")
    user.password_hash = hash_password(new_password)
    db.execute(delete(UserSessionModel).where(UserSessionModel.user_id == user.id))
    db.commit()
    return create_user_session(db, user.id)
