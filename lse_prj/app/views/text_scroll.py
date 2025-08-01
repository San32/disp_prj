import sys
import json
from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QListWidget, QListWidgetItem, QAbstractItemView,
    QLabel, QCheckBox
)
from PySide6.QtGui import QPainter, QFont, QColor
from PySide6.QtCore import QTimer


class ScrollingTextWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("텍스트 스크롤 창")

        self.text = ""
        self.direction = "right"
        self.font_size = 24
        self.speed = 2
        self.offset_x = 0
        self.offset_y = 0
        self.text_width = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_position)

        self.setMinimumSize(400, 100)

    def load_config(self, config):
        self.text = config["text"]
        self.direction = config.get("direction", "right")
        self.font_size = config.get("font_size", 24)
        self.speed = config.get("speed", 2)

        w, h = config.get("window_size", [400, 100])
        self.resize(w, h)
        self.setMinimumSize(w, h)

        font = QFont("맑은 고딕", self.font_size)
        self.setFont(font)

        fm = self.fontMetrics()
        self.text_width = fm.horizontalAdvance(self.text)

        if self.direction in ["left", "right"]:
            self.offset_x = -self.text_width if self.direction == "right" else self.width()
            self.offset_y = self.height() // 2 + self.font_size // 2
        elif self.direction in ["up", "down"]:
            self.offset_y = -self.font_size if self.direction == "down" else self.height()
            self.offset_x = 10

    def start(self):
        self.timer.start(30)

    def stop(self):
        self.timer.stop()

    def update_position(self):
        if self.direction == "right":
            self.offset_x += self.speed
            if self.offset_x > self.width():
                self.offset_x = -self.text_width
        elif self.direction == "left":
            self.offset_x -= self.speed
            if self.offset_x < -self.text_width:
                self.offset_x = self.width()
        elif self.direction == "down":
            self.offset_y += self.speed
            if self.offset_y > self.height() + self.font_size:
                self.offset_y = -self.font_size
        elif self.direction == "up":
            self.offset_y -= self.speed
            if self.offset_y < -self.font_size:
                self.offset_y = self.height() + self.font_size

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0))
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("맑은 고딕", self.font_size))
        painter.drawText(self.offset_x, self.offset_y, self.text)


class JsonManagerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JSON 파일 관리")

        self.load_button = QPushButton("파일 추가")
        self.delete_button = QPushButton("선택 항목 삭제")
        self.save_button = QPushButton("목록 저장")

        self.load_button.clicked.connect(self.add_files)
        self.delete_button.clicked.connect(self.delete_selected)
        self.save_button.clicked.connect(self.save_list)

        self.file_list_widget = QListWidget()
        self.file_list_widget.setDragDropMode(QAbstractItemView.InternalMove)
        self.file_list_widget.currentRowChanged.connect(self.preview_selected)

        self.preview_label = QLabel("미리보기:")
        self.preview_area = QLabel("")
        self.preview_area.setStyleSheet("background: #eee; padding: 5px;")
        self.preview_area.setWordWrap(True)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.load_button)
        btn_layout.addWidget(self.delete_button)
        btn_layout.addWidget(self.save_button)

        layout = QVBoxLayout()
        layout.addLayout(btn_layout)
        layout.addWidget(self.file_list_widget)
        layout.addWidget(self.preview_label)
        layout.addWidget(self.preview_area)

        self.setLayout(layout)

        self.config_cache = {}  # path → JSON

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "JSON 파일 선택", ".", "JSON Files (*.json)")
        if not files:
            return
        for path in files:
            if path in self.config_cache:
                continue  # 중복 방지
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                    if "duration" not in cfg:
                        cfg["duration"] = 5
                    self.config_cache[path] = cfg
                    self.file_list_widget.addItem(QListWidgetItem(path))
            except Exception as e:
                print(f"⚠️ 오류: {path} 불러오기 실패: {e}")

    def delete_selected(self):
        selected_items = self.file_list_widget.selectedItems()
        for item in selected_items:
            path = item.text()
            self.config_cache.pop(path, None)
            row = self.file_list_widget.row(item)
            self.file_list_widget.takeItem(row)
        self.preview_area.setText("")

    def save_list(self):
        save_path, _ = QFileDialog.getSaveFileName(self, "JSON 목록 저장", ".", "JSON Files (*.json)")
        if not save_path:
            return
        ordered_configs = []
        for i in range(self.file_list_widget.count()):
            path = self.file_list_widget.item(i).text()
            cfg = self.config_cache.get(path)
            if cfg:
                ordered_configs.append(cfg)
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(ordered_configs, f, indent=4, ensure_ascii=False)
            print(f"✅ 저장 완료: {save_path}")
        except Exception as e:
            print(f"⚠️ 저장 실패: {e}")

    def preview_selected(self, index):
        if index < 0 or index >= self.file_list_widget.count():
            self.preview_area.setText("")
            return
        path = self.file_list_widget.item(index).text()
        cfg = self.config_cache.get(path)
        if not cfg:
            self.preview_area.setText("⚠️ 미리보기를 불러올 수 없습니다.")
            return
        info = f"""📝 텍스트: {cfg.get('text')}
➡ 방향: {cfg.get('direction')}
🔤 폰트: {cfg.get('font_size')}
🚀 속도: {cfg.get('speed')}
⏱ 출력 시간: {cfg.get('duration')}초"""
        self.preview_area.setText(info)

    def get_ordered_configs(self):
        configs = []
        for i in range(self.file_list_widget.count()):
            path = self.file_list_widget.item(i).text()
            cfg = self.config_cache.get(path)
            if cfg:
                configs.append(cfg)
        return configs


class ControlWindow(QWidget):
    def __init__(self, text_widget: ScrollingTextWidget, json_manager: JsonManagerWindow):
        super().__init__()
        self.setWindowTitle("컨트롤 패널")
        self.text_widget = text_widget
        self.json_manager = json_manager

        self.start_button = QPushButton("시작")
        self.stop_button = QPushButton("정지")
        self.loop_checkbox = QCheckBox("반복 실행")

        self.start_button.clicked.connect(self.start_sequence)
        self.stop_button.clicked.connect(self.stop_sequence)

        layout = QVBoxLayout()
        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)
        layout.addWidget(self.loop_checkbox)
        self.setLayout(layout)

        self.configs = []
        self.current_index = 0

        self.display_timer = QTimer(self)
        self.display_timer.setSingleShot(True)
        self.display_timer.timeout.connect(self.next_config)

    def start_sequence(self):
        self.configs = self.json_manager.get_ordered_configs()
        if not self.configs:
            print("⚠️ 설정이 없습니다.")
            return
        self.current_index = 0
        self.show_config(self.configs[0])

    def stop_sequence(self):
        self.display_timer.stop()
        self.text_widget.stop()

    def show_config(self, config):
        self.text_widget.load_config(config)
        self.text_widget.start()
        duration_ms = config.get("duration", 5) * 1000
        self.display_timer.start(duration_ms)

    def next_config(self):
        self.text_widget.stop()
        self.current_index += 1
        if self.current_index < len(self.configs):
            self.show_config(self.configs[self.current_index])
        else:
            if self.loop_checkbox.isChecked():
                self.current_index = 0
                self.show_config(self.configs[self.current_index])
            else:
                print("✅ 모든 메시지를 출력 완료.")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    scroll_window = ScrollingTextWidget()
    json_manager = JsonManagerWindow()
    control_window = ControlWindow(scroll_window, json_manager)

    scroll_window.show()
    json_manager.show()
    control_window.show()

    sys.exit(app.exec())
