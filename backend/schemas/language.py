from enum import Enum

# 用来给pydantic校验
class AnalysisLanguage(str, Enum):
    """当前产品支持的界面与分析语言。"""

    ZH_CN = "zh-CN"
    JA_JP = "ja-JP"
    EN_US = "en-US"


ANALYSIS_LANGUAGE_NAMES: dict[AnalysisLanguage, str] = {
    AnalysisLanguage.ZH_CN: "简体中文",
    AnalysisLanguage.JA_JP: "日本語",
    AnalysisLanguage.EN_US: "English",
}

# 这里是后端传给大模型用的
# 之前我错误的以为是传给前端的...那方向就反了
def get_analysis_language_name(language: AnalysisLanguage) -> str:
    return ANALYSIS_LANGUAGE_NAMES[language]
