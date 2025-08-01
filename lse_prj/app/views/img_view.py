import sys
import cv2
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                                QPushButton, QLabel, QFileDialog, QMessageBox,
                                QDialog, QListWidget)
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os
from datetime import datetime

# 리눅스 나눔명조 글꼴 경로 지정
FONT_PATH = "/usr/share/fonts/truetype/nanum/NanumMyeongjo.ttf"
FONT_SIZE = 30

try:
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
except IOError:
    print(f"폰트 파일 '{FONT_PATH}'를 찾을 수 없습니다.")
    print("시스템에 나눔명조 글꼴이 설치되어 있는지 확인하거나 다른 폰트 경로를 지정해주세요.")
    font = ImageFont.load_default()

class PlaylistManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("재생 목록 관리")
        self.setGeometry(200, 200, 400, 500)

        self.playlist_file = "playlist.txt"
        self.video_list = []

        self.init_ui()
        self.load_playlist()

    def init_ui(self):
        main_layout = QVBoxLayout()

        self.list_widget = QListWidget()
        main_layout.addWidget(self.list_widget)

        control_layout = QHBoxLayout()
        self.add_button = QPushButton("파일 추가")
        self.remove_button = QPushButton("선택 항목 삭제")
        self.close_button = QPushButton("닫기")

        control_layout.addWidget(self.add_button)
        control_layout.addWidget(self.remove_button)
        control_layout.addWidget(self.close_button)

        main_layout.addLayout(control_layout)
        self.setLayout(main_layout)

        self.add_button.clicked.connect(self.add_file)
        self.remove_button.clicked.connect(self.remove_file)
        self.close_button.clicked.connect(self.accept)

    def load_playlist(self):
        self.list_widget.clear()
        self.video_list.clear()
        if os.path.exists(self.playlist_file):
            with open(self.playlist_file, 'r', encoding='utf-8') as f:
                for line in f:
                    path = line.strip()
                    if path and os.path.exists(path):
                        self.video_list.append(path)
                        self.list_widget.addItem(os.path.basename(path))

    def save_playlist(self):
        with open(self.playlist_file, 'w', encoding='utf-8') as f:
            for path in self.video_list:
                f.write(path + '\n')

    def add_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "파일 선택", "", "Media Files (*.mp4 *.avi *.mov *.mkv *.wmv *.jpg *.jpeg *.png *.bmp *.txt)"
        )
        if file_path and file_path not in self.video_list:
            self.video_list.append(file_path)
            self.list_widget.addItem(os.path.basename(file_path))
            self.save_playlist()

    def remove_file(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            return
        
        for item in selected_items:
            row = self.list_widget.row(item)
            self.list_widget.takeItem(row)
            del self.video_list[row]
        
        self.save_playlist()

class VideoPlayer(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PySide6 동영상 플레이어")
        self.setGeometry(100, 100, 800, 600)

        self.video_source = ""
        self.cap = None
        self.is_playing = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.time_timer = QTimer(self)
        self.time_timer.timeout.connect(self.display_current_time)

        self.frame_counter = 0
        self.fps = 0
        self.total_duration_secs = 0

        self.playlist = []
        self.current_playlist_index = -1

        self.is_image_mode = False
        self.is_time_mode = False
        self.time_config = {}

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        control_layout = QHBoxLayout()

        self.video_label = QLabel("동영상이 여기에 표시됩니다.")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("background-color: black; color: white;")

        self.file_name_label = QLabel("선택된 파일 없음")
        self.file_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.select_button = QPushButton("파일 선택")
        self.play_button = QPushButton("재생")
        self.stop_button = QPushButton("중지")
        self.playlist_button = QPushButton("재생 목록")
        self.play_playlist_button = QPushButton("재생 목록 순차 재생")

        self.play_button.setEnabled(False)
        self.stop_button.setEnabled(False)

        self.select_button.clicked.connect(self.select_file)
        self.play_button.clicked.connect(self.play_video)
        self.stop_button.clicked.connect(self.stop_video)
        self.playlist_button.clicked.connect(self.open_playlist_manager)
        self.play_playlist_button.clicked.connect(self.play_playlist)

        control_layout.addWidget(self.select_button)
        control_layout.addWidget(self.play_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addWidget(self.playlist_button)
        control_layout.addWidget(self.play_playlist_button)

        main_layout.addWidget(self.video_label)
        main_layout.addWidget(self.file_name_label)
        main_layout.addLayout(control_layout)

        self.setLayout(main_layout)

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "파일 선택", "", "Media Files (*.mp4 *.avi *.mov *.mkv *.wmv *.jpg *.jpeg *.png *.bmp *.txt)"
        )
        if file_path:
            self.load_video(file_path)
            self.current_playlist_index = -1

    def load_video(self, file_path):
        self.stop_video()
        self.video_source = file_path
        
        file_name = os.path.basename(file_path).lower()
        file_ext = os.path.splitext(file_path)[1].lower()
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']

        if file_name == "현재시간.txt":
            self.is_time_mode = True
            self.is_image_mode = False
            self.parse_time_config(file_path)
            self.time_timer.start(1000) # 1초마다 시간 업데이트
            self.display_current_time() # 즉시 시간 표시
        elif file_ext in image_extensions:
            self.is_image_mode = True
            self.is_time_mode = False
            self.display_image(file_path)
        else:
            self.is_image_mode = False
            self.is_time_mode = False
            self.cap = cv2.VideoCapture(self.video_source)
            if not self.cap.isOpened():
                QMessageBox.critical(self, "오류", "동영상 파일을 열 수 없습니다.")
                self.video_source = ""
                return

            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            total_frames = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)
            self.total_duration_secs = total_frames / self.fps
            self.play_video()

        self.file_name_label.setText(f"선택된 파일: {os.path.basename(self.video_source)}")
        self.play_button.setEnabled(True)
        self.stop_button.setEnabled(True)

    def parse_time_config(self, file_path):
        self.time_config = {
            'position': (10, 10),
            'font_size': 30
        }
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or '=' not in line:
                        continue
                    key, value = line.split('=', 1)
                    key = key.strip().lower()
                    value = value.strip()

                    if key == 'position':
                        try:
                            x, y = map(int, value.split(','))
                            self.time_config['position'] = (x, y)
                        except ValueError:
                            pass
                    elif key == 'font_size':
                        try:
                            self.time_config['font_size'] = int(value)
                        except ValueError:
                            pass
        except Exception as e:
            QMessageBox.warning(self, "경고", f"설정 파일 읽기 오류: {e}")

    def display_current_time(self):
        if not self.is_time_mode:
            self.time_timer.stop()
            return
        
        current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 폰트 크기 동적 변경
        try:
            time_font = ImageFont.truetype(FONT_PATH, self.time_config['font_size'])
        except IOError:
            time_font = ImageFont.load_default()

        # 검은색 배경 이미지 생성
        background = np.zeros((self.video_label.height(), self.video_label.width(), 3), dtype=np.uint8)
        frame_pil = Image.fromarray(background)
        draw = ImageDraw.Draw(frame_pil)
        
        draw.text(self.time_config['position'], current_time_str, font=time_font, fill=(255, 255, 255))
        
        frame = cv2.cvtColor(np.array(frame_pil), cv2.COLOR_RGB2BGR)

        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format.Format_BGR888)
        
        pixmap = QPixmap.fromImage(q_image)
        self.video_label.setPixmap(pixmap)

    def display_image(self, file_path):
        image = cv2.imread(file_path)
        if image is None:
            QMessageBox.critical(self, "오류", "이미지 파일을 열 수 없습니다.")
            return

        frame_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(frame_pil)
        subtitle_text = f"파일: {os.path.basename(file_path)}"
        
        try:
            text_bbox = draw.textbbox((0, 0), subtitle_text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
        except AttributeError:
            text_width, text_height = draw.textsize(subtitle_text, font=font)
        
        text_position = (10, 10)
        draw.text(text_position, subtitle_text, font=font, fill=(255, 255, 255))
        
        frame = cv2.cvtColor(np.array(frame_pil), cv2.COLOR_RGB2BGR)

        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format.Format_BGR888)
        
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(self.video_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.video_label.setPixmap(scaled_pixmap)

        QTimer.singleShot(3000, self.play_next_in_playlist)

    def play_next_in_playlist(self):
        if self.current_playlist_index != -1:
            next_index = (self.current_playlist_index + 1) % len(self.playlist)
            self.current_playlist_index = next_index
            self.load_video(self.playlist[self.current_playlist_index])

    def play_video(self):
        if not self.cap or not self.cap.isOpened():
            QMessageBox.critical(self, "오류", "재생할 파일이 없습니다.")
            return

        self.is_playing = True
        self.frame_counter = 0
        self.timer.start(int(1000 / self.fps))

    def stop_video(self):
        self.is_playing = False
        if self.timer.isActive():
            self.timer.stop()
        if self.time_timer.isActive():
            self.time_timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None
        self.video_label.setText("동영상이 여기에 표시됩니다.")
        self.file_name_label.setText("선택된 파일 없음")
        self.play_button.setEnabled(False)
        self.stop_button.setEnabled(False)

    def update_frame(self):
        if self.is_playing:
            ret, frame = self.cap.read()
            if ret:
                self.frame_counter += 1
                current_time_secs = self.frame_counter / self.fps
                
                current_mins = int(current_time_secs // 60)
                current_secs = int(current_time_secs % 60)

                total_mins = int(self.total_duration_secs // 60)
                total_secs = int(self.total_duration_secs % 60)

                subtitle_text = (
                    f"파일: {os.path.basename(self.video_source)} | "
                    f"재생 시간: {current_mins:02d}:{current_secs:02d} / {total_mins:02d}:{total_secs:02d}"
                )

                frame_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                draw = ImageDraw.Draw(frame_pil)
                
                try:
                    text_bbox = draw.textbbox((0, 0), subtitle_text, font=font)
                    text_width = text_bbox[2] - text_bbox[0]
                    text_height = text_bbox[3] - text_bbox[1]
                except AttributeError:
                    text_width, text_height = draw.textsize(subtitle_text, font=font)
                
                text_position = (10, 10)
                
                draw.text(text_position, subtitle_text, font=font, fill=(255, 255, 255))
                
                frame = cv2.cvtColor(np.array(frame_pil), cv2.COLOR_RGB2BGR)

                height, width, channel = frame.shape
                bytes_per_line = 3 * width
                q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format.Format_BGR888)
                
                pixmap = QPixmap.fromImage(q_image)
                scaled_pixmap = pixmap.scaled(self.video_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.video_label.setPixmap(scaled_pixmap)
            else:
                self.stop_video()
                self.play_next_in_playlist()

    def open_playlist_manager(self):
        dialog = PlaylistManagerDialog(self)
        dialog.exec()
        self.playlist = dialog.video_list

    def play_playlist(self):
        if not os.path.exists("playlist.txt"):
            QMessageBox.warning(self, "경고", "재생 목록 파일(playlist.txt)이 없습니다.")
            return

        self.playlist = []
        with open("playlist.txt", 'r', encoding='utf-8') as f:
            for line in f:
                path = line.strip()
                if path and os.path.exists(path):
                    self.playlist.append(path)

        if not self.playlist:
            QMessageBox.warning(self, "경고", "재생 목록에 동영상이 없습니다.")
            return

        self.current_playlist_index = 0
        self.load_video(self.playlist[self.current_playlist_index])

if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = VideoPlayer()
    player.show()
    sys.exit(app.exec())