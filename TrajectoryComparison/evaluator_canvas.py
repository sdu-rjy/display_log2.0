import pyqtgraph as pg
from PyQt5.QtCore import Qt, pyqtSignal
import numpy as np

class EvaluatorCanvas(pg.PlotWidget):
    canvas_clicked_pos = pyqtSignal(float, float)

    def __init__(self):
        super().__init__(title="Trajectory Comparison (Zoomable)")
        self.showGrid(x=True, y=True)
        self.setAspectLocked(True)
        self.addLegend()
        
        self.curve_items = {}
        self.point_items = {}
        self.error_lines = []
        
        self.scene().sigMouseClicked.connect(self._on_scene_clicked)

    def _on_scene_clicked(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.scenePos()
            if self.sceneBoundingRect().contains(pos):
                mouse_point = self.plotItem.vb.mapSceneToView(pos)
                self.canvas_clicked_pos.emit(mouse_point.x(), mouse_point.y())

    def setup_trajectories(self, file_names, trajectories):
        self.clear() 
        self.curve_items.clear()
        self.point_items.clear()
        self.error_lines.clear()

        # 强制颜色：Ref 用白色虚线，Est 用绿色实线
        colors = [(255, 255, 255), (50, 255, 50)]

        for i, fname in enumerate(file_names):
            if fname not in trajectories: continue
            data = trajectories[fname]
            x_list, y_list = data['x'], data['y']
            
            color = colors[i % len(colors)]
            
            if i == 0:
                pen = pg.mkPen(color=color, width=3, style=Qt.DashLine)
                name_label = f"[Ref] {fname}"
            else:
                pen = pg.mkPen(color=color, width=2)
                name_label = f"[Est] {fname}"

            curve = self.plot(x_list, y_list, pen=pen, name=name_label)
            self.curve_items[fname] = curve
            
            pt = pg.ScatterPlotItem(size=12, brush=pg.mkBrush(color), pen='w')
            self.addItem(pt)
            self.point_items[fname] = pt

    def update_step(self, file_names, trajectories, current_idx):
        if len(file_names) < 2: return []

        for line in self.error_lines:
            self.removeItem(line)
        self.error_lines.clear()

        ref_x, ref_y = None, None
        err_texts = []

        for i, fname in enumerate(file_names):
            if fname not in trajectories: continue
            data = trajectories[fname]
            idx = min(current_idx, len(data['x']) - 1)
            px, py = data['x'][idx], data['y'][idx]
            
            self.point_items[fname].setData([px], [py])

            if i == 0:
                ref_x, ref_y = px, py
            elif ref_x is not None:
                # 画误差牵引线
                line = pg.PlotCurveItem([ref_x, px], [ref_y, py], 
                                        pen=pg.mkPen('r', width=1, style=Qt.DotLine))
                self.addItem(line)
                self.error_lines.append(line)

                dist = np.hypot(ref_x - px, ref_y - py)
                err_texts.append(f"<b>APE Offset:</b> {dist:.4f} m")

        return err_texts