import os
import sqlite3
from collections.abc import Generator
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

# 首先确定数据库位置
# “数据库到底在哪？优先听 .env 的；如果 .env 没说，就用项目自己的默认位置；如果 .env 写的是相对路径，我还帮你把它固定到项目根目录，避免启动位置不同导致找错数据库。”
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / "resume_agent.db"
DEFAULT_DATABASE_URL = f"sqlite+pysqlite:///{DEFAULT_DATABASE_PATH.as_posix()}"
configured_database_url = os.getenv("DATABASE_URL")
if configured_database_url and configured_database_url.startswith("sqlite+pysqlite:///./"):
    relative_path = configured_database_url.removeprefix("sqlite+pysqlite:///./")
    DATABASE_URL = f"sqlite+pysqlite:///{(PROJECT_ROOT / relative_path).as_posix()}"
else:
    DATABASE_URL = configured_database_url or DEFAULT_DATABASE_URL

# 创建引擎 设定要是有占用等5秒再报错, 仅仅针对sqlite
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"timeout": 5} if DATABASE_URL.startswith("sqlite") else {},
)

# 监听 Engine 的 connect 事件。每当数据库建立一条新连接时，就自动调用下面这个函数。
# 自动调用下面的函数
# 每新建一个session总要设定点东西
@event.listens_for(Engine, "connect")
def configure_sqlite_connection(dbapi_connection, _connection_record) -> None:
    """为每条 SQLite 连接启用约束与适合当前小型并发任务的设置。"""

    if not isinstance(dbapi_connection, sqlite3.Connection):
        return

    cursor = dbapi_connection.cursor()
    # curosr可以理解成一个工作笔，点点基本配置
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()

# session工厂
SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    expire_on_commit=False,
)

#请求来了
#↓
#get_db()
#↓
#创建 Session
#↓
#yield session
#↓
#FastAPI 接口拿这个 session 去查数据库
#↓
#接口执行完
#↓
#回到 get_db()
#↓
#退出 with
#↓
#Session 自动 close
#就是给fastAPI用的，yield快速扔出session，用完回收，因为有with
#所以用完会关闭
def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：每个请求使用一个 Session，请求结束后关闭。"""

    with SessionLocal() as session:
        yield session
