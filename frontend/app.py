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
        None,
    )



def save_button_click(
    job_title,
    raw_text,
    table,
):

    requirements = []


    for row in table.to_dict(orient="records"):

        requirements.append(
            {
                "name": row["要求名称"],
                "description": row["描述"],
                "category": row["分类"],
                "weight": row["权重"],
            }
        )


    data = {

        "job_title": job_title,

        "raw_text": raw_text,

        "requirements": requirements,

    }


    result = save_jd(data)


    return result["job"]["id"]



def select_requirement(evt: gr.SelectData):

    if not evt.selected:
        return None

    return evt.index[0]



def add_requirement(table):

    table = table.copy()
    table.loc[len(table)] = {
        "要求名称": "",
        "描述": "",
        "分类": "other",
        "权重": 1,
    }

    return table, None



def delete_selected_requirement(
    table,
    selected_row,
):

    if selected_row is None:
        gr.Warning("请先在表格中选中要删除的要求")
        return table, None

    if 0 <= selected_row < len(table):
        table = table.drop(
            table.index[selected_row]
        ).reset_index(drop=True)

    return table, None



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


    selected_requirement_row = gr.State(
        value=None
    )


    with gr.Row():

        add_requirement_btn = gr.Button(
            "新增要求"
        )

        delete_requirement_btn = gr.Button(
            "删除选中要求"
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
            selected_requirement_row,
        ],
    )


    requirements.select(
        fn=select_requirement,
        outputs=[
            selected_requirement_row
        ],
    )


    add_requirement_btn.click(
        fn=add_requirement,
        inputs=[
            requirements
        ],
        outputs=[
            requirements,
            selected_requirement_row,
        ],
    )


    delete_requirement_btn.click(
        fn=delete_selected_requirement,
        inputs=[
            requirements,
            selected_requirement_row,
        ],
        outputs=[
            requirements,
            selected_requirement_row,
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
