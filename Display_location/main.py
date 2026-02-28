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
        # grp_active = QGroupBox("Data Control Source")
        # active_layout = QVBoxLayout()
        # self.lbl_active_name = QLabel("Source: None") 
        # self.lbl_active_name.setStyleSheet("color: blue; font-weight: bold;")
        
        # switch_layout = QHBoxLayout()
        # self.btn_prev_log = QPushButton("< Prev Log")
        # self.btn_prev_log.clicked.connect(self.switch_prev_log)
        # self.btn_next_log = QPushButton("Next Log >")
        # self.btn_next_log.clicked.connect(self.switch_next_log)
        # switch_layout.addWidget(self.btn_prev_log)
        # switch_layout.addWidget(self.btn_next_log)
        
        # active_layout.addWidget(self.lbl_active_name)
        # active_layout.addLayout(switch_layout)
        # grp_active.setLayout(active_layout)
        # ctrl_layout.addWidget(grp_active)

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
        
        self.btn_save = QPushButton("Export Range")
        self.btn_save.clicked.connect(self.export_trajectory_range)

        play_layout.addLayout(btn_layout)
        play_layout.addWidget(self.btn_save)
        grp_play.setLayout(play_layout)
        ctrl_layout.addWidget(grp_play)

        # 5. 轨迹时间范围过滤 (按时间戳)
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

        self.slider_filter_start = QSlider(Qt.Horizontal)
        self.slider_filter_end = QSlider(Qt.Horizontal)
        self.slider_filter_start.setToolTip("Drag to set Start Time")
        self.slider_filter_end.setToolTip("Drag to set End Time")

        self.lbl_filter_info = QLabel("Frames: --")
        self.lbl_filter_info.setStyleSheet("color: #333333; font-size: 11px;")
        
        filter_layout.addRow("Start Time:", self.cmb_filter_start)
        filter_layout.addRow("Start Slider:", self.slider_filter_start) # 起点滑块
        filter_layout.addRow("End Time:", self.cmb_filter_end)
        filter_layout.addRow("End Slider:", self.slider_filter_end)     # 终点滑块
        filter_layout.addRow(self.lbl_filter_info)

        self.cmb_filter_start.currentIndexChanged.connect(self.on_filter_changed)
        self.cmb_filter_end.currentIndexChanged.connect(self.on_filter_changed)
        self.slider_filter_start.valueChanged.connect(self.cmb_filter_start.setCurrentIndex)
        self.slider_filter_end.valueChanged.connect(self.cmb_filter_end.setCurrentIndex)   
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
        
        # 将所有日志的数据合并为一个全局大列表
        self.merged_trajectory = []
        for log_name in self.log_files_list:
            self.merged_trajectory.extend(self.loader.all_logs_data[log_name])
            
        total = len(self.merged_trajectory)
        self.lbl_status.setText(f"Maps: {len(maps)} files\nLogs: {count} files\nTotal Frames: {total}")

        if total > 0:
            self.slider.setRange(0, total - 1) # 这是播放控制的滑块
            
            # ========================================================
            # [关键修复在这里] 必须把新增的起止滑块的范围也设置为总帧数！
            # ========================================================
            self.slider_filter_start.blockSignals(True)
            self.slider_filter_end.blockSignals(True)
            
            self.slider_filter_start.setRange(0, total - 1)
            self.slider_filter_end.setRange(0, total - 1)

            # 下拉框同步更新
            self.cmb_filter_start.blockSignals(True)
            self.cmb_filter_end.blockSignals(True)
            self.cmb_filter_start.clear()
            self.cmb_filter_end.clear()
            
            timestamps = [str(d.get('timestamp', f"Frame {i}")) for i, d in enumerate(self.merged_trajectory)]
            self.cmb_filter_start.addItems(timestamps)
            self.cmb_filter_end.addItems(timestamps)
            
            # 默认选中首尾，并同步给滑块
            self.cmb_filter_start.setCurrentIndex(0)
            self.cmb_filter_end.setCurrentIndex(total - 1)
            self.slider_filter_start.setValue(0)
            self.slider_filter_end.setValue(total - 1)
            
            # 恢复信号
            self.cmb_filter_start.blockSignals(False)
            self.cmb_filter_end.blockSignals(False)
            self.slider_filter_start.blockSignals(False)
            self.slider_filter_end.blockSignals(False)
            # ========================================================
            
            self.canvas.update_landmarks(self.loader.landmarks, LANDMARK_CONFIGS)
            
            # 触发一次全局绘制
            self.on_filter_changed()
            self.update_frame_info(0)
        else:
            self.lbl_status.setText("No log data loaded.")

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
        if not hasattr(self, 'merged_trajectory') or not self.merged_trajectory:
            return

        start_idx = self.cmb_filter_start.currentIndex()
        end_idx = self.cmb_filter_end.currentIndex()

        if start_idx < 0 or end_idx < 0: return

        if start_idx > end_idx:
            self.cmb_filter_start.blockSignals(True)
            self.cmb_filter_start.setCurrentIndex(end_idx)
            self.cmb_filter_start.blockSignals(False)
            start_idx = end_idx

        # 更新截取帧数信息
        selected_frames = end_idx - start_idx + 1
        self.lbl_filter_info.setText(f"Selected Frames: {selected_frames} (Idx: {start_idx} to {end_idx})")

        # 截取全局数据
        sliced_data = self.merged_trajectory[start_idx : end_idx + 1]
        x_pts = [d['x'] for d in sliced_data]
        y_pts = [d['y'] for d in sliced_data]

        # 传递给画布更新单一轨迹
        self.canvas.update_unified_trajectory(x_pts, y_pts)

    def on_canvas_click(self, x, y):
        # 匹配点击点到全局进度
        if not self.loader.all_logs_np: return

        min_dist = float('inf')
        best_log = None
        best_local_idx = -1

        for log_name, arrays in self.loader.all_logs_np.items():
            x_arr = arrays['x']
            y_arr = arrays['y']
            
            dists = np.hypot(x_arr - x, y_arr - y)
            idx = dists.argmin()
            dist = dists[idx]

            if dist < min_dist:
                min_dist = dist
                best_log = log_name
                best_local_idx = idx

        if best_log and min_dist < 5.0:
            # 计算局部索引在全局列表中的绝对偏移量
            global_idx = 0
            for name in self.log_files_list:
                if name == best_log:
                    global_idx += best_local_idx
                    break
                global_idx += len(self.loader.all_logs_data[name])
                
            self.update_frame_info(global_idx)
            print(f"Jumped to Global Frame {global_idx} (dist={min_dist:.2f})")

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
        if not hasattr(self, 'merged_trajectory') or not self.merged_trajectory: return
        idx = max(0, min(idx, len(self.merged_trajectory) - 1))
        self.current_frame_idx = idx
        data = self.merged_trajectory[idx]
        
        self.lbl_time.setText(data.get('timestamp', '--'))
        
        state_text = data.get('loc_state', '--')
        type_text = data.get('loc_type', '--')
        self.lbl_state.setText(state_text)
        self.lbl_type.setText(type_text)

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

    def export_trajectory_range(self):
        """ 将当前起止时间范围内的轨迹按指定格式导出到 TXT 文件 """
        if not hasattr(self, 'merged_trajectory') or not self.merged_trajectory:
            QMessageBox.warning(self, "Warning", "No data to export.")
            return

        # 获取当前时间过滤器选中的起止索引
        start_idx = self.cmb_filter_start.currentIndex()
        end_idx = self.cmb_filter_end.currentIndex()

        if start_idx < 0 or end_idx < 0 or start_idx > end_idx:
            QMessageBox.warning(self, "Warning", "Invalid time range selected.")
            return

        # 截取选定范围内的数据
        sliced_data = self.merged_trajectory[start_idx : end_idx + 1]
        
        # 构造安全的文件名 (去掉时间戳里的冒号和空格，防止文件系统报错)
        start_str = sliced_data[0].get('timestamp', f'idx{start_idx}').replace(':', '').replace(' ', '_').replace(',', '')
        end_str = sliced_data[-1].get('timestamp', f'idx{end_idx}').replace(':', '').replace(' ', '_').replace(',', '')
        out_file = os.path.join(OUT_DIR, f"export_traj_{start_str}_to_{end_str}.txt")

        try:
            with open(out_file, 'w', encoding='utf-8') as f:
                for data in sliced_data:
                    # 获取字段，如果没有则用 '--' 占位
                    ts = data.get('timestamp', '--')
                    state = data.get('loc_state', '--')
                    ltype = data.get('loc_type', '--')
                    x = data.get('x', 0.0)
                    y = data.get('y', 0.0)
                    t = data.get('t', 0.0)  # 这里对应 theta

                    # 按照要求格式化: 时间戳 状态 定位模式 x y theta
                    # 坐标保留 6 位小数保证精度
                    line = f"{ts} {state} {ltype} {x:.6f} {y:.6f} {t:.6f}\n"
                    f.write(line)
            
            print(f"Saved {len(sliced_data)} frames to: {out_file}")
            QMessageBox.information(self, "Export Successful", 
                                    f"Successfully exported {len(sliced_data)} frames.\n\nFile saved to:\n{out_file}")
            
        except Exception as e:
            print(f"Export failed: {e}")
            QMessageBox.critical(self, "Export Error", f"Failed to write file:\n{e}")

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
        else:
            super().keyPressEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())