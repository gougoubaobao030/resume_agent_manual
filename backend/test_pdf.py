from services.pdf_service import extract_pdf_text

#哇 cool 真的都抽出来了
text = extract_pdf_text(
    r"D:\UntiyArt\MonkeyCareerDocs\最终简历\Portfolio_Version21.md.pdf"
)

print(text)