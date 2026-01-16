import sys
import os
import base64
import time
from openai import OpenAI
from PyQt6.QtCore import QSettings

# 配置输入输出目录
INPUT_DIR = "input_images"
OUTPUT_DIR = "output_results"

# 支持的图片格式
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp'}

def process_images():
    # 读取配置 (复用主程序的配置)
    settings = QSettings("MyOCRTool", "Settings")
    
    api_url = settings.value("url", "https://aistudio.baidu.com/llm/lmapi/v3")
    api_token = settings.value("token", "")
    
    if not api_token:
        print("❌ 错误: 未检测到 Token。请先运行主程序 run.command 设置 Token。")
        return

    client = OpenAI(
        api_key=api_token,
        base_url=api_url
    )

    # 获取所有图片文件
    files = [f for f in os.listdir(INPUT_DIR) if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS]
    
    if not files:
        print(f"⚠️  警告: '{INPUT_DIR}' 文件夹为空，请先放入图片。")
        return

    print(f"🚀 发现 {len(files)} 张图片，开始批处理...")
    print("-" * 40)

    for i, file_name in enumerate(files):
        file_path = os.path.join(INPUT_DIR, file_name)
        output_name = os.path.splitext(file_name)[0] + ".md"
        output_path = os.path.join(OUTPUT_DIR, output_name)

        print(f"[{i+1}/{len(files)}] 正在处理: {file_name} ...")

        try:
            # 读取图片并编码
            with open(file_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')

            # 调用 API (使用智能分析模式 Prompt)
            response = client.chat.completions.create(
                model="ernie-5.0-thinking-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "请扮演一位阅卷专家，详细分析这张图片的内容。如果是试卷，请识别题目和学生答案，给出评分建议或知识点分析；如果是其他内容，请总结核心要点。请使用 Markdown 格式输出一份详细的分析报告。"},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]
                    }
                ],
                stream=False
            )

            result = response.choices[0].message.content
            
            # 保存结果
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result)
            
            print(f"✅ 完成! 已保存至: {output_path}")

        except Exception as e:
            print(f"❌ 失败: {str(e)}")
        
        print("-" * 40)

    print("\n🎉 所有任务处理完毕！")

if __name__ == "__main__":
    # 确保目录存在
    if not os.path.exists(INPUT_DIR):
        os.makedirs(INPUT_DIR)
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    process_images()
