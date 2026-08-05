import requests


BACKEND_URL = "http://127.0.0.1:18000"


def parse_jd(raw_text: str):
    """
    调用后端JD解析接口
    """

    response = requests.post(
        f"{BACKEND_URL}/api/jd/parse",
        json={
            "raw_text": raw_text
        },
        timeout=120,
    )

    response.raise_for_status()

    return response.json()



def save_jd(data: dict):
    """
    保存HR确认后的JD
    """

    response = requests.post(
        f"{BACKEND_URL}/api/jd",
        json=data,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()