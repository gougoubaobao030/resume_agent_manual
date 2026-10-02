import argparse
import sys
from getpass import getpass
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from database import SessionLocal  # noqa: E402
from services.auth_service import create_user, reset_user_password  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="管理 Resume Agent 内部用户")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create_parser = subparsers.add_parser("create", help="创建预置用户")
    create_parser.add_argument("username")
    create_parser.add_argument("--display-name")
    create_parser.add_argument(
        "--language", choices=["zh-CN", "ja-JP", "en-US"], default="zh-CN"
    )
    reset_parser = subparsers.add_parser("reset-password", help="重置用户密码")
    reset_parser.add_argument("username")
    args = parser.parse_args()

    password = getpass("新密码（至少8个字符）: ")
    confirmation = getpass("再次输入新密码: ")
    if password != confirmation:
        raise SystemExit("两次输入的密码不一致")

    with SessionLocal() as db:
        if args.command == "create":
            user = create_user(
                db,
                username=args.username,
                password=password,
                display_name=args.display_name,
                preferred_language=args.language,
            )
            print(f"已创建用户: {user.username} ({user.id})")
        else:
            user = reset_user_password(db, args.username, password)
            print(f"已重置密码并撤销旧会话: {user.username}")


if __name__ == "__main__":
    main()
