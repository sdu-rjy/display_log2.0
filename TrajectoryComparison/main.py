import sys
import os
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QTextEdit, QSplitter, QScrollArea, QComboBox, QFormLayout, QGroupBox)
from PyQt5.QtCore import Qt

import pyqtgraph as pg

from evaluator_data import EvaluatorData
from evaluator_canvas import EvaluatorCanvas

LOG_DIR = os.path.join(os.getcwd(), 'logs')

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Evo-like Trajectory Evaluator")
        self.resize(1400, 800)

        self.current_idx = 0
        self.selected_files = [] # 仅存当前对比的两个文件
        
        self.data_manager = EvaluatorData(LOG_DIR)
        
        pg.setConfigOptions(antialias=True)
        self.canvas = EvaluatorCanvas()
        self.canvas.canvas_clicked_pos.connect(self.on_canvas_click)

        self.init_ui()
        self.process_initial_data()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # === 左侧面板 ===
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 1. 轨迹选择区 (新增)
        grp_select = QGroupBox("Select Trajectories for Comparison")
        select_layout = QFormLayout()
        
        self.cmb_ref = QComboBox()
        self.cmb_est = QComboBox()
        select_layout.addRow("Reference (GT):", self.cmb_ref)
        select_layout.addRow("Estimated:", self.cmb_est)
        
        self.cmb_ref.currentIndexChanged.connect(self.on_selection_changed)
        self.cmb_est.currentIndexChanged.connect(self.on_selection_changed)
        
        grp_select.setLayout(select_layout)
        left_layout.addWidget(grp_select)

        # 2. 误差报告区
        self.text_output = QTextEdit()
        self.text_output.setReadOnly(True)
        self.text_output.setStyleSheet("font-family: Consolas, monospace; font-size: 13px;")
        left_layout.addWidget(self.text_output)

        self.realtime_error_label = QLabel("Current Step Offset: --")
        self.realtime_error_label.setStyleSheet("color: blue; font-weight: bold; font-size: 13px;")
        left_layout.addWidget(self.realtime_error_label)

        # 3. 详细状态面板
        self.frame_details_label = QLabel("Waiting for selection...")
        self.frame_details_label.setWordWrap(True)
        self.frame_details_label.setTextFormat(Qt.RichText)
        self.frame_details_label.setStyleSheet("font-size: 12px; background-color: #f9f9f9; padding: 5px;")
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.frame_details_label)
        left_layout.addWidget(scroll_area)

        # === 右侧绘图区 ===
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.addWidget(self.canvas)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([450, 1000])

    def process_initial_data(self):
        success, msg = self.data_manager.load_data()
        if not success:
            self.text_output.setText(msg)
            return
            
        # 填充下拉框
        self.cmb_ref.blockSignals(True)
        self.cmb_est.blockSignals(True)
        
        self.cmb_ref.addItems(self.data_manager.file_names)
        self.cmb_est.addItems(self.data_manager.file_names)
        
        # 默认选中前两个，如果不够就都选第一个
        self.cmb_ref.setCurrentIndex(0)
        self.cmb_est.setCurrentIndex(1 if len(self.data_manager.file_names) > 1 else 0)
        
        self.cmb_ref.blockSignals(False)
        self.cmb_est.blockSignals(False)
        
        self.on_selection_changed()

    def on_selection_changed(self):
        """ 当用户在下拉框选择新的对比目标时触发 """
        ref_name = self.cmb_ref.currentText()
        est_name = self.cmb_est.currentText()
        
        if not ref_name or not est_name: return

        self.selected_files = [ref_name, est_name]
        self.current_idx = 0  # 切换轨迹时重置游标到起点

        # 计算并更新 evo APE/RPE 报告
        report = self.data_manager.compute_evaluation_report(ref_name, est_name)
        self.text_output.setText(report)
        
        # 重绘画布
        self.canvas.setup_trajectories(self.selected_files, self.data_manager.trajectories)
        self.update_step_display()

    def update_step_display(self):
        if len(self.selected_files) < 2: return

        err_texts = self.canvas.update_step(self.selected_files, 
                                            self.data_manager.trajectories, 
                                            self.current_idx)
        
        if err_texts:
            self.realtime_error_label.setText(f"Step {self.current_idx} Offset:\n" + "\n".join(err_texts))

        # 更新下方详细姿态面板
        info_text = f"<b>--- Frame Index: {self.current_idx} ---</b><br>"
        for fname in self.selected_files:
            data = self.data_manager.trajectories[fname]
            idx = min(self.current_idx, len(data['x']) - 1)
            
            ts = data['timestamps'][idx]
            state = data['states'][idx]
            type_ = data['types'][idx]
            px, py, pt = data['x'][idx], data['y'][idx], data['t'][idx]
            
            color = "green" if "RealTimeLocation" in state else "red"
            
            prefix = "[Ref]" if fname == self.selected_files[0] else "[Est]"
            info_text += f"<br><b>{prefix} {fname}</b><br>"
            info_text += f"&nbsp;&nbsp;<b>Time:</b> {ts}<br>"
            info_text += f"&nbsp;&nbsp;<b>State:</b> <span style='color:{color}'>{state}</span> (Type: {type_})<br>"
            info_text += f"&nbsp;&nbsp;<b>Pose:</b> X={px:.4f}, Y={py:.4f}, T={pt:.4f}<br>"
            
        self.frame_details_label.setText(info_text)

    def on_canvas_click(self, x, y):
        if not self.selected_files: return

        min_dist = float('inf')
        best_idx = -1

        # 仅在被选中的两条轨迹里寻找最近点
        for fname in self.selected_files:
            data = self.data_manager.trajectories[fname]
            dists = np.hypot(data['x'] - x, data['y'] - y)
            idx = dists.argmin()
            dist = dists[idx]

            if dist < min_dist:
                min_dist = dist
                best_idx = idx

        if min_dist < 5.0 and best_idx != -1:
            self.current_idx = best_idx
            self.update_step_display()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Right:
            # 限制不能超过较长的那条轨迹
            max_l = max(len(self.data_manager.trajectories[f]['x']) for f in self.selected_files)
            if self.current_idx < max_l - 1:
                self.current_idx += 1
                self.update_step_display()
        elif event.key() == Qt.Key_Left:
            if self.current_idx > 0:
                self.current_idx -= 1
                self.update_step_display()
        else:
            super().keyPressEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())