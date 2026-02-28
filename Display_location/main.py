import sys
import os
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFileDialog, 
                             QSlider, QGroupBox, QFormLayout, QMessageBox)
from PyQt5.QtCore import Qt

from data_loader import DataLoader
from canvas_widget import LogCanvas

# --- 配置区 ---
BASE_DIR = os.getcwd()
LOG_DIR = os.path.join(BASE_DIR, 'logs')
MAP_DIR = os.path.join(BASE_DIR, 'map')
OUT_DIR = os.path.join(BASE_DIR, 'out')

for d in [LOG_DIR, MAP_DIR, OUT_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

LANDMARK_CONFIGS = [
    {'keyword': 'QRCode', 'indices': (0, 1), 'color': 'y', 'symbol': 's'}, 
    {'keyword': 'Reflector', 'indices': (1, 2), 'color': 'c', 'symbol': 't1'},
]

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Robot Log Analyzer - Click to Jump")
        self.resize(1200, 800)

        self.loader = DataLoader()
        
        self.log_files_list = [] 
        self.active_log_index = -1 
        self.current_frame_idx = 0 
        
        self.init_ui()
        self.refresh_all()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)

        # === 左侧控制面板 ===
        control_panel = QWidget()
        control_panel.setFixedWidth(350) # [微调]稍微加宽一点，防止State文字太长换行
        ctrl_layout = QVBoxLayout(control_panel)

        # 1. 概览
        grp_src = QGroupBox("Data Overview")
        src_layout = QVBoxLayout()
        self.lbl_status = QLabel("Initializing...")
        self.lbl_status.setWordWrap(True)
        self.btn_reload = QPushButton("Reload All")
        self.btn_reload.clicked.connect(self.refresh_all)
        src_layout.addWidget(self.lbl_status)
        src_layout.addWidget(self.btn_reload)
        grp_src.setLayout(src_layout)
        ctrl_layout.addWidget(grp_src)

        # 2. 激活日志控制
        grp_active = QGroupBox("Data Control Source")
        active_layout = QVBoxLayout()
        self.lbl_active_name = QLabel("Source: None") 
        self.lbl_active_name.setStyleSheet("color: blue; font-weight: bold;")
        
        switch_layout = QHBoxLayout()
        self.btn_prev_log = QPushButton("< Prev Log")
        self.btn_prev_log.clicked.connect(self.switch_prev_log)
        self.btn_next_log = QPushButton("Next Log >")
        self.btn_next_log.clicked.connect(self.switch_next_log)
        switch_layout.addWidget(self.btn_prev_log)
        switch_layout.addWidget(self.btn_next_log)
        
        active_layout.addWidget(self.lbl_active_name)
        active_layout.addLayout(switch_layout)
        grp_active.setLayout(active_layout)
        ctrl_layout.addWidget(grp_active)

        # 3. 详细信息
        grp_info = QGroupBox("Frame Details")
        info_layout = QFormLayout()
        self.lbl_time = QLabel("--")
        self.lbl_x = QLabel("0.000")
        self.lbl_y = QLabel("0.000")
        self.lbl_t = QLabel("0.000")
        
        # [新增] 状态和类型标签
        self.lbl_state = QLabel("--")
        self.lbl_state.setStyleSheet("color: darkgreen; font-weight: bold;") # 加点样式区别
        self.lbl_type = QLabel("--")

        info_layout.addRow("Time:", self.lbl_time)
        info_layout.addRow("State:", self.lbl_state) # [新增]
        info_layout.addRow("Type:", self.lbl_type)   # [新增]
        info_layout.addRow("X:", self.lbl_x)
        info_layout.addRow("Y:", self.lbl_y)
        info_layout.addRow("T (Deg):", self.lbl_t)
        
        grp_info.setLayout(info_layout)
        ctrl_layout.addWidget(grp_info)

        # 4. 播放控制
        grp_play = QGroupBox("Playback")
        play_layout = QVBoxLayout()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.valueChanged.connect(self.on_slider_changed)
        play_layout.addWidget(self.slider)

        btn_layout = QHBoxLayout()
        self.btn_prev_frame = QPushButton("<<")
        self.btn_prev_frame.clicked.connect(self.prev_frame)
        self.btn_next_frame = QPushButton(">>")
        self.btn_next_frame.clicked.connect(self.next_frame)
        btn_layout.addWidget(self.btn_prev_frame)
        btn_layout.addWidget(self.btn_next_frame)
        
        self.btn_save = QPushButton("Export Frame")
        self.btn_save.clicked.connect(self.export_current_frame)

        play_layout.addLayout(btn_layout)
        play_layout.addWidget(self.btn_save)
        grp_play.setLayout(play_layout)
        ctrl_layout.addWidget(grp_play)

        # === 轨迹时间范围过滤 ===
        grp_filter = QGroupBox("Trajectory Time Filter")
        filter_layout = QFormLayout()
        
        from PyQt5.QtWidgets import QComboBox, QListView
        self.cmb_filter_start = QComboBox()
        self.cmb_filter_end = QComboBox()

        self.cmb_filter_start.setView(QListView())
        self.cmb_filter_end.setView(QListView())
        self.cmb_filter_start.setStyleSheet("QComboBox { combobox-popup: 0; }")
        self.cmb_filter_end.setStyleSheet("QComboBox { combobox-popup: 0; }")

        self.cmb_filter_start.setMaxVisibleItems(15)
        self.cmb_filter_end.setMaxVisibleItems(15)

        self.lbl_filter_info = QLabel("Frames: --")
        self.lbl_filter_info.setStyleSheet("color: #333333; font-size: 11px;")
        
        filter_layout.addRow("Start Time:", self.cmb_filter_start)
        filter_layout.addRow("End Time:", self.cmb_filter_end)
        filter_layout.addRow(self.lbl_filter_info)
        
        # 绑定值变化信号 (当下拉框改变时触发)
        self.cmb_filter_start.currentIndexChanged.connect(self.on_filter_changed)
        self.cmb_filter_end.currentIndexChanged.connect(self.on_filter_changed)
        
        grp_filter.setLayout(filter_layout)
        ctrl_layout.addWidget(grp_filter)

        ctrl_layout.addStretch()
        layout.addWidget(control_panel)

        # === 右侧绘图 ===
        self.canvas = LogCanvas()
        self.canvas.canvas_clicked_pos.connect(self.on_canvas_click)
        layout.addWidget(self.canvas, stretch=1)

    # --- 逻辑 ---

    def refresh_all(self):
        maps = self.loader.load_all_maps(MAP_DIR)
        self.canvas.update_maps(maps)

        count = self.loader.load_all_logs_in_folder(LOG_DIR, LANDMARK_CONFIGS)
        self.log_files_list = sorted(list(self.loader.all_logs_data.keys()))
        
        self.canvas.plot_all_trajectories(self.loader.all_logs_data)
        
        self.lbl_status.setText(f"Maps: {len(maps)} files\nLogs: {count} files")
        
        if self.log_files_list:
            self.active_log_index = 0
            self.activate_log(self.log_files_list[0])
        else:
            self.active_log_index = -1
            self.lbl_active_name.setText("Source: None")

    def activate_log(self, log_name):
        self.loader.select_log(log_name)
        total = len(self.loader.trajectory_data)
        self.lbl_active_name.setText(f"Source: {log_name}")
        self.slider.setRange(0, total - 1)
        self.canvas.update_landmarks(self.loader.landmarks, LANDMARK_CONFIGS)

        # === [新增] 重置范围过滤器 ===
        if total > 0:
            self.cmb_filter_start.blockSignals(True)
            self.cmb_filter_end.blockSignals(True)
            
            self.cmb_filter_start.clear()
            self.cmb_filter_end.clear()
            
            # 提取该日志所有的时间戳列表
            timestamps = [str(d.get('timestamp', f"Frame {i}")) for i, d in enumerate(self.loader.trajectory_data)]
            
            # 批量添加到下拉框
            self.cmb_filter_start.addItems(timestamps)
            self.cmb_filter_end.addItems(timestamps)
            
            # 默认选中第一帧和最后一帧
            self.cmb_filter_start.setCurrentIndex(0)
            self.cmb_filter_end.setCurrentIndex(total - 1)
            
            self.cmb_filter_start.blockSignals(False)
            self.cmb_filter_end.blockSignals(False)
            
            # 手动触发一次更新
            self.on_filter_changed()

    def on_filter_changed(self):
        """ 当用户选择新的起止时间戳时触发 """
        if not self.loader.trajectory_data:
            return

        start_idx = self.cmb_filter_start.currentIndex()
        end_idx = self.cmb_filter_end.currentIndex()

        # 防御性判断：如果列表为空或未选中有效值
        if start_idx < 0 or end_idx < 0:
            return

        # 逻辑保护：确保起点时间不能晚于终点时间
        if start_idx > end_idx:
            # 暂时阻塞信号，将 Start 强制回退到等于 End 的时间
            self.cmb_filter_start.blockSignals(True)
            self.cmb_filter_start.setCurrentIndex(end_idx)
            self.cmb_filter_start.blockSignals(False)
            start_idx = end_idx

        data = self.loader.trajectory_data
        
        # 更新界面上显示的截取帧数信息
        selected_frames = end_idx - start_idx + 1
        self.lbl_filter_info.setText(f"Selected Frames: {selected_frames} (Idx: {start_idx} to {end_idx})")

        # === 截取当前时间范围内的数据 ===
        sliced_data = data[start_idx : end_idx + 1]
        x_pts = [d['x'] for d in sliced_data]
        y_pts = [d['y'] for d in sliced_data]

        # === 发送给 Canvas 仅更新当前激活的这条轨迹 ===
        active_log_name = self.log_files_list[self.active_log_index]
        self.canvas.update_single_trajectory(active_log_name, x_pts, y_pts)
    def on_canvas_click(self, x, y):
        if not self.loader.all_logs_np:
            return

        min_dist = float('inf')
        best_log = None
        best_idx = -1

        for log_name, arrays in self.loader.all_logs_np.items():
            x_arr = arrays['x']
            y_arr = arrays['y']
            
            dists = np.hypot(x_arr - x, y_arr - y)
            idx = dists.argmin()
            dist = dists[idx]

            if dist < min_dist:
                min_dist = dist
                best_log = log_name
                best_idx = idx

        if best_log and min_dist < 5.0:
            if best_log != self.log_files_list[self.active_log_index]:
                self.active_log_index = self.log_files_list.index(best_log)
                self.activate_log(best_log)
            
            self.update_frame_info(best_idx)
            print(f"Jumped to {best_log} frame {best_idx} (dist={min_dist:.2f})")

    def switch_prev_log(self):
        if not self.log_files_list: return
        self.active_log_index = (self.active_log_index - 1) % len(self.log_files_list)
        self.activate_log(self.log_files_list[self.active_log_index])
        self.update_frame_info(0)

    def switch_next_log(self):
        if not self.log_files_list: return
        self.active_log_index = (self.active_log_index + 1) % len(self.log_files_list)
        self.activate_log(self.log_files_list[self.active_log_index])
        self.update_frame_info(0)

    def update_frame_info(self, idx):
        if not self.loader.trajectory_data: return
        idx = max(0, min(idx, len(self.loader.trajectory_data) - 1))
        self.current_frame_idx = idx
        data = self.loader.trajectory_data[idx]
        
        self.lbl_time.setText(data['timestamp'])
        
        # [新增] 更新界面上的状态和类型
        # 使用 .get() 防止老日志没有这个字段报错
        state_text = data.get('loc_state', '--')
        type_text = data.get('loc_type', '--')
        self.lbl_state.setText(state_text)
        self.lbl_type.setText(type_text)

        # 简单的视觉优化：如果不正常状态显示红色 (可选)
        if "RealTimeLocation" in state_text:
            self.lbl_state.setStyleSheet("color: darkgreen; font-weight: bold;")
        else:
            self.lbl_state.setStyleSheet("color: red; font-weight: bold;")

        self.lbl_x.setText(f"{data['x']:.4f}")
        self.lbl_y.setText(f"{data['y']:.4f}")
        t_deg = data['t'] * 57.29578
        self.lbl_t.setText(f"{t_deg:.2f}°")
        
        self.slider.blockSignals(True)
        self.slider.setValue(idx)
        self.slider.blockSignals(False)
        self.canvas.set_current_point(data['x'], data['y'])

    def export_current_frame(self):
        if not self.loader.trajectory_data: return
        data = self.loader.trajectory_data[self.current_frame_idx]
        log_name = self.log_files_list[self.active_log_index]
        out_file = os.path.join(OUT_DIR, f"exp_{log_name}_{self.current_frame_idx}.txt")
        try:
            with open(out_file, 'w') as f:
                f.write(f"{data}\n")
            print(f"Saved: {out_file}")
        except Exception as e:
            print(e)

    def on_slider_changed(self, val):
        self.update_frame_info(val)

    def prev_frame(self):
        self.update_frame_info(self.current_frame_idx - 1)

    def next_frame(self):
        self.update_frame_info(self.current_frame_idx + 1)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Left:
            self.prev_frame()
        elif event.key() == Qt.Key_Right:
            self.next_frame()
        elif event.key() == Qt.Key_Up:
            self.switch_prev_log()
        elif event.key() == Qt.Key_Down:
            self.switch_next_log()
        else:
            super().keyPressEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())