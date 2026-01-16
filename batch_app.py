import sys
import os
import base64
import time
import json
import fitz  # PyMuPDF
from openai import OpenAI
from PyQt6.QtCore import QSettings
from PIL import Image, ImageDraw, ImageFont, ImageFile

# 配置输入输出目录
INPUT_DIR = "input_images"
OUTPUT_DIR = "output_results"

# 支持的图片格式
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp'}
# 支持的文档格式
DOC_EXTENSIONS = {'.pdf'}

# 增加 Pillow 图片加载限制，防止大图报错
ImageFile.LOAD_TRUNCATED_IMAGES = True

def analyze_image(client, base64_image, prompt_text):
    """发送图片给大模型进行分析"""
    try:
        response = client.chat.completions.create(
            model="ernie-5.0-thinking-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                         {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            stream=False
        )
        content = response.choices[0].message.content
        # 清理可能存在的 markdown 代码块标记
        if "```json" in content:
            content = content.replace("```json", "").replace("```", "")
        return content.strip()
    except Exception as e:
        return f"❌ 分析失败: {str(e)}"

def draw_marks(img_pil, items):
    """在图片上绘制批改标记"""
    draw = ImageDraw.Draw(img_pil)
    width, height = img_pil.size
    
    # 尝试加载字体，如果失败使用默认
    try:
        # macOS 常见字体
        font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 40)
    except:
        font = ImageFont.load_default()

    for item in items:
        # 获取坐标 (归一化 0-1000 转为 实际像素)
        bbox = item.get("bbox", [])
        if len(bbox) == 4:
            x1 = bbox[0] / 1000 * width
            y1 = bbox[1] / 1000 * height
            x2 = bbox[2] / 1000 * width
            y2 = bbox[3] / 1000 * height
            
            status = item.get("status", "unknown")
            
            if status == "correct":
                color = "#00e676" # 鲜艳绿
                symbol = "✓"
                # 画框
                draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
                # 画符号
                draw.text((x2-30, y1-30), symbol, fill=color, font=font)
                
            elif status == "incorrect":
                color = "#ff1744" # 鲜艳红
                symbol = "✗"
                draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
                draw.text((x2-30, y1-30), symbol, fill=color, font=font)
    
    return img_pil

def generate_html_from_json(json_data, image_rel_path):
    """根据 JSON 生成美观的 HTML 报告"""
    summary = json_data.get("summary", "暂无总结")
    items = json_data.get("items", [])
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; background-color: #f5f7fa; margin: 0; padding: 20px; color: #333; }}
            .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
            .header {{ text-align: center; border-bottom: 2px solid #f0f0f0; padding-bottom: 20px; margin-bottom: 30px; }}
            .score-box {{ font-size: 24px; color: #1976d2; font-weight: bold; margin-top: 10px; }}
            .summary-card {{ background: #e3f2fd; border-left: 5px solid #2196f3; padding: 15px; margin-bottom: 30px; border-radius: 4px; }}
            .image-box {{ text-align: center; margin: 30px 0; border: 1px solid #eee; padding: 10px; border-radius: 8px; }}
            .image-box img {{ max-width: 100%; height: auto; border-radius: 4px; }}
            .question-card {{ border: 1px solid #eee; border-radius: 8px; padding: 20px; margin-bottom: 20px; transition: all 0.2s; }}
            .question-card:hover {{ box-shadow: 0 5px 15px rgba(0,0,0,0.05); border-color: #ddd; }}
            .status-correct {{ color: #2e7d32; background: #e8f5e9; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 14px; float: right; }}
            .status-incorrect {{ color: #c62828; background: #ffebee; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 14px; float: right; }}
            .q-title {{ font-weight: bold; font-size: 16px; margin-bottom: 10px; }}
            .q-analysis {{ color: #666; font-size: 14px; line-height: 1.6; margin-top: 10px; border-top: 1px dashed #eee; padding-top: 10px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>阅卷分析报告</h1>
                <div class="score-box">AI 智能批改</div>
            </div>
            
            <div class="summary-card">
                <h3>总评摘要</h3>
                <p>{summary}</p>
            </div>

            <div class="image-box">
                <p><strong>批改预览</strong> (点击可查看大图)</p>
                <img src="{image_rel_path}" alt="批改后的试卷">
            </div>

            <h3>逐题详细分析</h3>
    """
    
    for idx, item in enumerate(items):
        q_id = item.get("question_id", str(idx+1))
        status = item.get("status", "unknown")
        status_html = '<span class="status-correct">✅ 正确</span>' if status == "correct" else '<span class="status-incorrect">❌ 需改进</span>'
        analysis = item.get("analysis", "无详细分析")
        
        html += f"""
            <div class="question-card">
                {status_html}
                <div class="q-title">题目 {q_id}</div>
                <div class="q-analysis">{analysis}</div>
            </div>
        """
    
    html += """
        </div>
    </body>
    </html>
    """
    return html

def process_images():
    settings = QSettings("MyOCRTool", "Settings")
    default_url = "https://aistudio.baidu.com/llm/lmapi/v3"
    default_token = "6cb2698ad8bee94fb7ccd948fade9548e78f83ab"
    api_url = settings.value("url", default_url)
    api_token = settings.value("token", default_token)
    
    if not api_token or api_token == "在此输入TOKEN":
        api_token = default_token
    if not api_token:
        print("❌ 错误: 未检测到 Token。请先运行主程序 run.command 设置 Token。")
        return

    client = OpenAI(api_key=api_token, base_url=api_url)

    target_files = []
    print(f"📂 正在扫描 '{INPUT_DIR}' ...")
    for root, dirs, files in os.walk(INPUT_DIR):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in IMAGE_EXTENSIONS or ext in DOC_EXTENSIONS:
                rel_path = os.path.relpath(os.path.join(root, file), INPUT_DIR)
                target_files.append(rel_path)
    
    if not target_files:
        print(f"⚠️  警告: '{INPUT_DIR}' 文件夹为空。")
        return

    print(f"🚀 发现 {len(target_files)} 个文件，开始批处理...")
    print("-" * 40)

    PROMPT_MD = "请扮演一位阅卷专家，详细分析这张图片的内容。\n1. ⚠️ 如果图片中包含表格，请务必将其还原为 Markdown 表格。\n2. 如果是试卷，请识别题目和学生答案，给出评分建议或知识点分析。\n3. 如果是其他内容，请总结核心要点。\n请使用 Markdown 格式输出一份详细的分析报告。"
    
    # JSON Prompt 用于试卷
    PROMPT_EXAM_JSON = """请扮演一位阅卷专家，对这张试卷进行批改。
    请识别所有的题目区域和学生答案，判断对错，并提取坐标以便我在图上标记。
    
    ⚠️ 请严格按照以下 JSON 格式输出，不要包含任何 Markdown 标记或额外文本：
    {
        "summary": "这里写一份整体的评价摘要，包括知识点掌握情况和建议。",
        "items": [
            {
                "question_id": "1",
                "status": "correct", 
                "bbox": [100, 200, 500, 300], 
                "analysis": "这道题考察了..."
            },
            {
                "question_id": "2",
                "status": "incorrect", 
                "bbox": [100, 350, 500, 450], 
                "analysis": "学生由于粗心计算错误..."
            }
        ]
    }
    【重要说明】：
    1. status 只能是 "correct" 或 "incorrect"。
    2. bbox 是该题目或答案区域在图片中的归一化坐标 [x1, y1, x2, y2]，范围均为 0-1000（例如 500 代表图片中间）。请尽可能准确框选出题目和手写答案的区域。
    """

    for i, rel_path in enumerate(target_files):
        file_path = os.path.join(INPUT_DIR, rel_path)
        ext = os.path.splitext(file_path)[1].lower()
        is_exam = "试卷" in rel_path
        
        print(f"[{i+1}/{len(target_files)}] 正在处理: {rel_path} ...")

        try:
            if ext in DOC_EXTENSIONS: # PDF
                doc = fitz.open(file_path)
                full_html = ""
                full_md = ""
                
                output_base_dir = os.path.join(OUTPUT_DIR, os.path.dirname(rel_path))
                os.makedirs(output_base_dir, exist_ok=True)
                file_basename = os.path.splitext(os.path.basename(rel_path))[0]

                for page_num, page in enumerate(doc):
                    print(f"     -> 第 {page_num+1} 页...")
                    pix = page.get_pixmap(dpi=150)
                    img_pil = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    
                    # 转 base64 发送给 AI
                    buf = sys.modules['io'].BytesIO() # 使用 sys.modules 避免 import io 冲突
                    img_pil.save(buf, format='JPEG')
                    base64_image = base64.b64encode(buf.getvalue()).decode('utf-8')
                    
                    if is_exam:
                        json_str = analyze_image(client, base64_image, PROMPT_EXAM_JSON)
                        try:
                            data = json.loads(json_str)
                            # 绘图
                            img_marked = draw_marks(img_pil.copy(), data.get("items", []))
                            # 保存批改后的图片
                            marked_img_name = f"{file_basename}_p{page_num+1}_marked.jpg"
                            marked_img_path = os.path.join(output_base_dir, marked_img_name)
                            img_marked.save(marked_img_path)
                            
                            # 生成 HTML 片段
                            page_html = generate_html_from_json(data, marked_img_name)
                            # 为了合并，这里只取 container 内部，或者简单堆叠
                            # 简化起见，直接堆叠 iframe 或者 div
                            full_html += f"<h3>--- 第 {page_num+1} 页 ---</h3>" + page_html
                            
                        except json.JSONDecodeError:
                            print("     ❌ JSON 解析失败，可能是模型输出格式不对")
                            full_html += f"<p>本页解析失败: {json_str}</p>"
                    else:
                        res = analyze_image(client, base64_image, PROMPT_MD)
                        full_md += f"\n\n## 第 {page_num+1} 页\n{res}\n---\n"
                
                doc.close()
                
                # 保存最终结果
                if is_exam:
                    out_path = os.path.join(output_base_dir, f"{file_basename}.html")
                    with open(out_path, "w", encoding="utf-8") as f:
                        f.write(full_html)
                else:
                    out_path = os.path.join(output_base_dir, f"{file_basename}.md")
                    with open(out_path, "w", encoding="utf-8") as f:
                        f.write(full_md)
                        
            else: # 图片
                with open(file_path, "rb") as f:
                    img_pil = Image.open(f).convert("RGB")
                
                # 转 base64
                import io
                buf = io.BytesIO()
                img_pil.save(buf, format='JPEG')
                base64_image = base64.b64encode(buf.getvalue()).decode('utf-8')
                
                output_base_dir = os.path.join(OUTPUT_DIR, os.path.dirname(rel_path))
                os.makedirs(output_base_dir, exist_ok=True)
                file_basename = os.path.splitext(os.path.basename(rel_path))[0]

                if is_exam:
                    json_str = analyze_image(client, base64_image, PROMPT_EXAM_JSON)
                    try:
                        data = json.loads(json_str)
                        # 绘图
                        img_marked = draw_marks(img_pil.copy(), data.get("items", []))
                        # 保存批改后的图片
                        marked_img_name = f"{file_basename}_marked.jpg"
                        marked_img_path = os.path.join(output_base_dir, marked_img_name)
                        img_marked.save(marked_img_path)
                        
                        # 生成 HTML
                        html_content = generate_html_from_json(data, marked_img_name)
                        out_path = os.path.join(output_base_dir, f"{file_basename}.html")
                        with open(out_path, "w", encoding="utf-8") as f:
                            f.write(html_content)
                            
                    except json.JSONDecodeError:
                        print("    ❌ JSON 解析失败")
                else:
                    res = analyze_image(client, base64_image, PROMPT_MD)
                    out_path = os.path.join(output_base_dir, f"{file_basename}.md")
                    with open(out_path, "w", encoding="utf-8") as f:
                        f.write(res)
            
            print(f"✅ 处理完成")

        except Exception as e:
            print(f"❌ 失败: {str(e)}")
            import traceback
            traceback.print_exc()
        
        print("-" * 40)

    print("\n🎉 所有任务处理完毕！")


if __name__ == "__main__":
    # 确保根目录存在
    if not os.path.exists(INPUT_DIR):
        os.makedirs(INPUT_DIR)
        print(f"已创建输入目录: {INPUT_DIR}")
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    process_images()
