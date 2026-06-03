import sys, re, io, time, base64, requests, threading, keyboard
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                             QWidget, QTextEdit, QLabel, QLineEdit, QStackedWidget, QHBoxLayout)
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
        self.edit_url = QLineEdit(self.settings.value("url", "在此输入API_URL"))
        layout.addWidget(self.edit_url)
 
        layout.addWidget(QLabel("<b>API_TOKEN:</b>"))
        self.edit_token = QLineEdit(self.settings.value("token", "在此输入TOKEN"))
        layout.addWidget(self.edit_token)
 
        # layout.addWidget(QLabel("<b>快捷键 (如 alt+q, ctrl+shift+a):</b>"))
        # self.edit_hotkey = QLineEdit(self.settings.value("hotkey", "alt+q"))
        # layout.addWidget(self.edit_hotkey)
 
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
        self.label_status.setText("图片解析中")
        self.btn_capture.setEnabled(False)
        threading.Thread(target=self.ocr_worker, args=(img_obj,), daemon=True).start()
         
    def ocr_worker(self, img):
        try:
            #图像预处理
            img = img.convert('L')
            img = ImageEnhance.Contrast(img).enhance(2.0)
            img = img.filter(ImageFilter.SHARPEN)
            img = img.convert('RGB')
            #图像压缩
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=95)
            file_data = base64.b64encode(img_byte_arr.getvalue()).decode("ascii")
 
            # 从界面获取实时配置
            url = self.settings.value("url")
            token = self.settings.value("token")
 
            headers = {"Authorization": f"token {token}", "Content-Type": "application/json"}
            payload = {"file": file_data, "fileType": 1, "useDocOrientationClassify": False, "useChartRecognition": False}
             
            response = requests.post(url, json=payload, headers=headers, timeout=20)
             
            if response.status_code == 200:
                result = response.json()["result"]
                text = "".join([re.sub(r'<[^>]+>', '', res["markdown"]["text"]) + "\n" for res in result.get("layoutParsingResults", [])])
                self.signals.finished.emit(text.strip() or "解析失败，请尝试重新识别", "识别完成")
            else:
                self.signals.finished.emit("", f"API错误: {response.status_code}")
        except Exception as e:
            self.signals.finished.emit("", f"异常: {str(e)}")
 
    def on_ocr_finished(self, text, status):
        self.btn_capture.setEnabled(True)
        self.label_status.setText(status)
        if text:
            self.result_box.setText(text)
            pyperclip.copy(text)
 
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())