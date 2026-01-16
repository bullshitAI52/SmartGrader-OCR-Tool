import sys, re, io, time, base64, requests, threading, keyboard
from openai import OpenAI
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                             QWidget, QTextEdit, QLabel, QLineEdit, QStackedWidget, QHBoxLayout, QComboBox)

from PyQt6.QtCore import Qt, QRect, pyqtSignal, QObject, QTimer, QSettings
from PyQt6.QtGui import QPainter, QPen, QColor
from PIL import ImageGrab, ImageEnhance, ImageFilter
import pyperclip
 
 
class WorkerSignals(QObject):
    finished = pyqtSignal(str, str)
 
#截图层
class CaptureWindow(QWidget):
    def __init__(self, callback, cancel_callback):
        super().__init__()
        self.callback = callback
        self.cancel_callback = cancel_callback
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        self.setWindowOpacity(0.3)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.start_pos = self.end_pos = None
        self.is_drawing = False
 
    def paintEvent(self, event):
        if self.is_drawing and self.start_pos and self.end_pos:
            painter = QPainter(self)
            painter.setPen(QPen(QColor(255, 0, 0), 2, Qt.PenStyle.SolidLine)) 
            painter.drawRect(QRect(self.start_pos, self.end_pos))
 
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.cancel_callback(); self.close()
        elif event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.pos(); self.is_drawing = True
 
    def mouseMoveEvent(self, event):
        if self.is_drawing: self.end_pos = event.pos(); self.update()
 
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_drawing = False
            self.hide()
            QApplication.processEvents()
            time.sleep(0.15)
            x1, y1 = min(self.start_pos.x(), event.pos().x()), min(self.start_pos.y(), event.pos().y())
            x2, y2 = max(self.start_pos.x(), event.pos().x()), max(self.start_pos.y(), event.pos().y())
            if x2 - x1 < 10 or y2 - y1 < 10:
                self.cancel_callback(); self.close(); return
            ratio = self.screen().devicePixelRatio()
            bbox = (x1 * ratio, y1 * ratio, x2 * ratio, y2 * ratio)
            img = ImageGrab.grab(bbox)
            self.callback(img); self.close()
 
#主窗口
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("截图文字识别工具v1.30")
        self.resize(450, 600)
         
        #配置保存
        self.settings = QSettings("MyOCRTool", "Settings")
         
         
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
         
        self.init_main_ui()    
        self.init_setting_ui() 
        self.init_about_ui()
         
        self.signals = WorkerSignals()
        self.signals.finished.connect(self.on_ocr_finished)
         
        #初始热键绑定
        #self.current_hotkey = self.settings.value("hotkey", "alt+q")
        #self.rebind_hotkey(self.current_hotkey)
 
    def init_main_ui(self):
        page = QWidget()
        layout = QVBoxLayout(page)
         
        header_layout = QHBoxLayout()
         
        self.btn_to_setting = QPushButton("设置")
        self.btn_to_setting.clicked.connect(lambda: self.stack.setCurrentIndex(1))
 
        self.btn_to_about = QPushButton("关于")
        self.btn_to_about.clicked.connect(lambda: self.stack.setCurrentIndex(2))
 
 
        
        header_layout.addWidget(self.btn_to_setting)
        header_layout.addWidget(self.btn_to_about)
        header_layout.addStretch()
 
        layout.addLayout(header_layout)
 
        self.btn_capture = QPushButton("开始截图")
        self.btn_capture.setMinimumHeight(60)
        self.btn_capture.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.btn_capture.clicked.connect(self.start_capture)
        layout.addWidget(self.btn_capture)
 
        self.label_status = QLabel("工具已就绪")
        layout.addWidget(self.label_status)
 
        self.result_box = QTextEdit()
        layout.addWidget(self.result_box)
         
        self.stack.addWidget(page)
 
    def init_setting_ui(self):
        page = QWidget()
        layout = QVBoxLayout(page)
 
        layout.addWidget(QLabel("<b>API_URL:</b>"))
        self.edit_url = QLineEdit(self.settings.value("url", "https://aistudio.baidu.com/llm/lmapi/v3"))
        layout.addWidget(self.edit_url)
 
        layout.addWidget(QLabel("<b>API_TOKEN:</b>"))
        self.edit_token = QLineEdit(self.settings.value("token", "6cb2698ad8bee94fb7ccd948fade9548e78f83ab"))
        layout.addWidget(self.edit_token)
 
        # layout.addWidget(QLabel("<b>快捷键 (如 alt+q, ctrl+shift+a):</b>"))
        # self.edit_hotkey = QLineEdit(self.settings.value("hotkey", "alt+q"))
        # layout.addWidget(self.edit_hotkey)
 
        layout.addWidget(QLabel("<b>识别模式:</b>"))
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["纯文本提取", "表格还原 (HTML)", "智能分析报告"])
        # Load saved index, default to 0
        self.combo_mode.setCurrentIndex(int(self.settings.value("mode", 0)))
        layout.addWidget(self.combo_mode)

        layout.addStretch()
 
        btn_save = QPushButton("保存并返回")
        btn_save.setMinimumHeight(40)
        btn_save.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        btn_save.clicked.connect(self.save_settings)
        layout.addWidget(btn_save)
 
        self.stack.addWidget(page)
 
    def init_about_ui(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("<h2>截图文字识别工具v1.30</h2>"))
        layout.addWidget(QLabel("<b>本工具免费且已开源，仅供学习交流，严禁倒卖！</b>"))
        layout.addWidget(QLabel("<p>功能说明：截图区域文字识别，鼠标右键或ESC可取消截图</p>"))
         
 
        layout.addStretch()
         
        btn_back = QPushButton("返回")
        btn_back.setMinimumHeight(40)
        btn_back.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        layout.addWidget(btn_back)
         
        self.stack.addWidget(page) 
         
 
    def save_settings(self):
        #保存到配置
        self.settings.setValue("url", self.edit_url.text())
        self.settings.setValue("token", self.edit_token.text())
        self.settings.setValue("mode", self.combo_mode.currentIndex())
         
        #new_hotkey = self.edit_hotkey.text().lower()
        #if new_hotkey != self.current_hotkey:
            #self.rebind_hotkey(new_hotkey)
            #self.current_hotkey = new_hotkey
            #self.settings.setValue("hotkey", new_hotkey)
             
        self.stack.setCurrentIndex(0)
        self.label_status.setText("设置已保存")
 
    def rebind_hotkey(self, key_str):
        try:
            keyboard.unhook_all() #清除旧的
            keyboard.add_hotkey(key_str, self.start_capture)
        except:
            print("热键绑定失败")
 
    def start_capture(self):
        if self.isVisible():
            self.hide()
            QTimer.singleShot(250, self.show_capture_window)
         
    def show_capture_window(self):
        self.cap_win = CaptureWindow(self.request_ocr_thread, self.on_capture_cancel)
        self.cap_win.show()
 
    def on_capture_cancel(self):
        self.show(); self.label_status.setText("截图已取消")
 
    def request_ocr_thread(self, img_obj):
        self.show()
        self.label_status.setText("正在思考中...")
        self.btn_capture.setEnabled(False)
        threading.Thread(target=self.ocr_worker, args=(img_obj,), daemon=True).start()
         
    def ocr_worker(self, img):
        try:
            # 图像预处理
            img = img.convert('RGB')
            # 图像压缩
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=95)
            # base64 编码
            base64_image = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

            # 从界面获取实时配置
            base_url = self.settings.value("url")
            api_key = self.settings.value("token")
            mode_index = int(self.settings.value("mode", 0))

            # 默认模型
            model = "ernie-5.0-thinking-preview"

            # 构建 Prompt
            prompts = [
                "请识别这张图片中的所有文字，直接输出文字内容，不要包含其他解释、markdown 格式或 '识别结果' 等字样。保持原有的换行格式。", # 0: Text
                "请识别图片中的表格结构，并将其还原为 HTML 表格代码 (<table>...)。请直接输出 HTML 代码，不要包含 ```html 标记或其他解释。", # 1: Table
                "请扮演一位阅卷专家，分析这张图片的内容。如果是试卷，请识别题目和学生答案，并给出评分建议或知识点分析；如果是其他内容，请总结核心要点。请使用 Markdown 格式输出一份分析报告。" # 2: Analysis
            ]
            
            prompt_text = prompts[mode_index] if mode_index < len(prompts) else prompts[0]

            client = OpenAI(
                api_key=api_key,
                base_url=base_url
            )

            response = client.chat.completions.create(
                model=model,
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
            # 尝试提取思考过程（如果有）
            # 注意：OpenAI 标准库通常把 extra details 放在 message.content 里或者其他字段，
            # 这里 Ernie 的思考过程可能需要特殊处理，但通常 content 是最终回答。
            # 用户代码示例里的 stream 处理逻辑略有不同，但这里我们用非 stream 简化。
            
            if content:
                self.signals.finished.emit(content.strip(), "识别完成")
            else:
                self.signals.finished.emit("", "未识别到文字")

        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg:
                error_msg = "认证失败：请检查 Token"
            elif "404" in error_msg:
                error_msg = "请求错误：检查 URL 或模型名称"
            self.signals.finished.emit("", f"出错: {error_msg}")
 
    def on_ocr_finished(self, text, status):
        self.btn_capture.setEnabled(True)
        self.label_status.setText(status)
        if text:
            # 简单判断是否为 HTML 或 Markdown 表格
            if "<table>" in text or "<tr>" in text:
                self.result_box.setHtml(text)
            else:
                try:
                    self.result_box.setMarkdown(text)
                except AttributeError:
                    self.result_box.setText(text) # Fallback for older PyQt
            
            pyperclip.copy(text)
 
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())