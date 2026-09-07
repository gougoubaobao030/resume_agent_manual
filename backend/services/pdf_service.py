from pathlib import Path
from unstructured.partition.pdf import partition_pdf

class PDFParseError(Exception):
    pass

def extract_pdf_text(
    pdf_path: str
) -> str:
    """
    使用unstructured解析PDF，
    返回纯文本。
    """

    path = Path(pdf_path)

    if not path.exists():
        raise FileExistsError(
            f"PDF不存在：{pdf_path}"
        )
    
    #返回一堆elements，注意不是字符串
    elements = partition_pdf(
        filename=str(path)
    )

    #所以需要拼接上去
    texts = []

    for element in elements:
        text = str(element)

        #如果两端不带空格
        if text.strip():
            texts.append(text)
    
    # 如果最终什么有效文字都没有解析出来
    if not text.strip():
        raise PDFParseError(
            "无法解析，请上传文本型PDF"
        )


    return "\n".join(texts)