
import os
import io
import base64
from openai import OpenAI
from PIL import Image

def ocr_image(image_path, api_key, base_url):
    try:
        if not os.path.exists(image_path):
            print(f"Error: Image not found at {image_path}")
            return

        with Image.open(image_path) as img:
            img = img.convert('RGB')
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=95)
            base64_image = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

        print(f"Image loaded. Size: {img.size}")
        print("Sending request to API...")

        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )

        model = "ernie-5.0-thinking-preview"
        prompt = "请识别这张图片中的所有文字，直接输出文字内容，不要包含其他解释、markdown 格式或 '识别结果' 等字样。保持原有的换行格式。"

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            stream=False
        )
        
        content = response.choices[0].message.content
        print("\n--- OCR Result ---\n")
        print(content)
        print("\n------------------\n")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    image_path = "/Users/apple/Documents/阅卷助手/input_images/图片/WechatIMG86.jpg"
    # Default values from ocr_app.py
    api_key = "6cb2698ad8bee94fb7ccd948fade9548e78f83ab"
    base_url = "https://aistudio.baidu.com/llm/lmapi/v3"
    
    ocr_image(image_path, api_key, base_url)
