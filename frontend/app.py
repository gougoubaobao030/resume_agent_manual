import gradio as gr

from api_client import (
    parse_jd,
    save_jd,
)


def parse_button_click(raw_text):

    result = parse_jd(raw_text)

    job = result["job"]


    requirements = job["requirements"]


    table = []

    for item in requirements:

        table.append(
            [
                item["name"],
                item["description"],
                item["category"],
                item["weight"],
            ]
        )


    return (
        job["job_title"],
        table,
        job["raw_text"],
    )



def save_button_click(
    job_title,
    raw_text,
    table,
):

    requirements = []


    for row in table:

        requirements.append(
            {
                "name": row[0],
                "description": row[1],
                "category": row[2],
                "weight": row[3],
            }
        )


    data = {

        "job_title": job_title,

        "raw_text": raw_text,

        "requirements": requirements,

    }


    result = save_jd(data)


    return result["job"]["id"]



with gr.Blocks(
    title="Resume Agent JD Demo"
) as demo:


    gr.Markdown(
        """
# Resume Agent

## JD解析与HR确认 Demo
"""
    )


    raw_text = gr.Textbox(
        label="请输入岗位JD",
        lines=10,
        placeholder="输入岗位说明...",
    )


    parse_btn = gr.Button(
        "AI解析JD"
    )


    job_title = gr.Textbox(
        label="岗位名称"
    )


    hidden_raw = gr.Textbox(
        label="原始JD",
        visible=False,
    )


    requirements = gr.Dataframe(
        headers=[
            "要求名称",
            "描述",
            "分类",
            "权重",
        ],
        datatype=[
            "str",
            "str",
            "str",
            "number",
        ],
        interactive=True,
    )


    save_btn = gr.Button(
        "保存JD"
    )


    save_result = gr.Textbox(
        label="保存结果"
    )


    parse_btn.click(
        fn=parse_button_click,
        inputs=[
            raw_text
        ],
        outputs=[
            job_title,
            requirements,
            hidden_raw,
        ],
    )


    save_btn.click(
        fn=save_button_click,
        inputs=[
            job_title,
            hidden_raw,
            requirements,
        ],
        outputs=[
            save_result
        ],
    )



if __name__ == "__main__":

    demo.launch(
        server_name="127.0.0.1",
        server_port=12000,
    )