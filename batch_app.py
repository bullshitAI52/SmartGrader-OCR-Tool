import sys
import os
import base64
import time
import fitz  # PyMuPDF
from openai import OpenAI
from PyQt6.QtCore import QSettings

# 配置输入输出目录
INPUT_DIR = "input_images"
OUTPUT_DIR = "output_results"

# 支持的图片格式
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp'}
# 支持的文档格式
DOC_EXTENSIONS = {'.pdf'}

def analyze_image(client, base64_image):
    """发送图片给大模型进行分析"""
    try:
        response = client.chat.completions.create(
            model="ernie-5.0-thinking-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                         {"type": "text", "text": "请扮演一位阅卷专家，详细分析这张图片的内容。\n1. ⚠️ 如果图片中包含表格，请务必将其还原为 Markdown 表格。\n2. 如果是试卷，请识别题目和学生答案，给出评分建议或知识点分析。\n3. 如果是其他内容，请总结核心要点。\n请使用 Markdown 格式输出一份详细的分析报告。"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ 分析失败: {str(e)}"

def process_images():
    # 读取配置 (复用主程序的配置)
    settings = QSettings("MyOCRTool", "Settings")
    
    # 优先读取配置，如果没有则使用硬编码的默认值 (用户之前提供的)
    default_url = "https://aistudio.baidu.com/llm/lmapi/v3"
    default_token = "6cb2698ad8bee94fb7ccd948fade9548e78f83ab"

    api_url = settings.value("url", default_url)
    api_token = settings.value("token", default_token)
    
    # 如果读取到的可能是空字符串（视以前保存情况而定），强制回退
    if not api_token or api_token == "在此输入TOKEN":
        api_token = default_token
    
    if not api_token:
        print("❌ 错误: 未检测到 Token。请先运行主程序 run.command 设置 Token。")
        return

    client = OpenAI(
        api_key=api_token,
        base_url=api_url
    )

    # 获取所有待处理文件 (递归遍历)
    target_files = []
    print(f"📂 正在扫描 '{INPUT_DIR}' ...")
    
    for root, dirs, files in os.walk(INPUT_DIR):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in IMAGE_EXTENSIONS or ext in DOC_EXTENSIONS:
                # 保存相对路径
                rel_path = os.path.relpath(os.path.join(root, file), INPUT_DIR)
                target_files.append(rel_path)
    
    if not target_files:
        print(f"⚠️  警告: '{INPUT_DIR}' 文件夹为空，请放入图片或 PDF。")
        return

    print(f"🚀 发现 {len(target_files)} 个文件，开始批处理...")
    print("-" * 40)

    for i, rel_path in enumerate(target_files):
        # 完整的输入文件路径
        file_path = os.path.join(INPUT_DIR, rel_path)
        ext = os.path.splitext(file_path)[1].lower()
        
        # 构建输出文件路径
        output_rel_path = os.path.splitext(rel_path)[0] + ".md"
        output_path = os.path.join(OUTPUT_DIR, output_rel_path)
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        print(f"[{i+1}/{len(target_files)}] 正在处理: {rel_path} ...")

        try:
            full_result = ""
            
            if ext in DOC_EXTENSIONS: # 处理 PDF
                doc = fitz.open(file_path)
                print(f"   📄 文档共 {len(doc)} 页，逐页分析中...")
                
                for page_num, page in enumerate(doc):
                    print(f"     -> 第 {page_num+1} 页...")
                    # 渲染为图片 (dpi=150 足够清晰且不太大)
                    pix = page.get_pixmap(dpi=150)
                    img_data = pix.tobytes("jpg")
                    base64_image = base64.b64encode(img_data).decode('utf-8')
                    
                    # 分析
                    page_result = analyze_image(client, base64_image)
                    
                    full_result += f"\n\n## 第 {page_num+1} 页分析\n\n{page_result}\n\n---\n"
                    
                doc.close()
                
            else: # 处理图片
                with open(file_path, "rb") as image_file:
                    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                full_result = analyze_image(client, base64_image)

            # 保存结果
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(full_result)
            
            print(f"✅ 完成! 已保存至: {output_path}")

        except Exception as e:
            print(f"❌ 失败: {str(e)}")
        
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
