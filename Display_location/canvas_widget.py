import pyqtgraph as pg
from PyQt5.QtCore import pyqtSignal, Qt
import numpy as np

class LogCanvas(pg.GraphicsLayoutWidget):
    # 修改信号：发射点击的 (x, y) 坐标，而不是索引
    canvas_clicked_pos = pyqtSignal(float, float)

    def __init__(self):
        super().__init__()
        self.plot_item = self.addPlot(title="Trajectory Analysis")
        self.plot_item.setAspectLocked(True)
        self.plot_item.showGrid(x=True, y=True)
        self.legend = self.plot_item.addLegend()

        # 监听场景点击事件
        self.plot_item.scene().sigMouseClicked.connect(self._on_scene_clicked)

        self.map_items = {} 
        self.traj_items = {} 
        self.landmark_items = []

        self.map_styles = [
            {'symbol': 'o', 'brush': (255, 0, 0, 200), 'pen': None, 'size': 10},
            {'symbol': 's', 'brush': (100, 200, 100, 200), 'pen': None, 'size': 1},
            {'symbol': 't', 'brush': (200, 100, 100, 200), 'pen': None, 'size': 1},
            {'symbol': 'd', 'brush': (100, 100, 200, 200), 'pen': None, 'size': 1},
            {'symbol': '+', 'brush': (200, 200, 50, 200),  'pen': None, 'size': 1},
        ]
        
        self.traj_pen = pg.mkPen(color=(0, 120, 255), width=2) 

        self.current_pos_scatter = pg.ScatterPlotItem(size=15, symbol='o', 
                                                     pen=pg.mkPen('w'), brush=pg.mkBrush('r'),
                                                     name='Current Pos')
        self.current_pos_scatter.setZValue(100)
        self.plot_item.addItem(self.current_pos_scatter)

    def _on_scene_clicked(self, event):
        """ 处理鼠标点击 """
        if event.button() == Qt.LeftButton:
            # 将屏幕像素坐标转换为图表坐标
            pos = event.scenePos()
            if self.plot_item.sceneBoundingRect().contains(pos):
                mouse_point = self.plot_item.vb.mapSceneToView(pos)
                self.canvas_clicked_pos.emit(mouse_point.x(), mouse_point.y())

    def update_maps(self, maps_data):
        for item in self.map_items.values():
            self.plot_item.removeItem(item)
            self.legend.removeItem(item)
        self.map_items.clear()

        for i, (name, points) in enumerate(maps_data.items()):
            if points is None or len(points) == 0:
                continue
            style = self.map_styles[i % len(self.map_styles)]
            item = pg.ScatterPlotItem(pos=points, size=style['size'], symbol=style['symbol'],
                                      brush=style['brush'], pen=style['pen'], pxMode=True, name=name)
            item.setZValue(-10)
            self.plot_item.addItem(item)
            self.map_items[name] = item

    def plot_all_trajectories(self, all_logs_data):
        for item in self.traj_items.values():
            self.plot_item.removeItem(item)
            self.legend.removeItem(item)
        self.traj_items.clear()

        added_legend = False
        for fname, data_list in all_logs_data.items():
            if not data_list: continue
            
            x_pts = [d['x'] for d in data_list]
            y_pts = [d['y'] for d in data_list]
            
            plot_name = "Trajectory" if not added_legend else None
            if plot_name: added_legend = True
            
            curve = pg.PlotCurveItem(x_pts, y_pts, pen=self.traj_pen, name=plot_name)
            curve.setZValue(10)
            self.plot_item.addItem(curve)
            self.traj_items[fname] = curve

    def update_landmarks(self, landmarks_dict, configs):
        for item in self.landmark_items:
            self.plot_item.removeItem(item)
        self.landmark_items.clear()

        for kw, coords in landmarks_dict.items():
            if coords:
                pts = np.array(coords)
                cfg = next((c for c in configs if c['keyword'] == kw), None)
                if cfg:
                    item = pg.ScatterPlotItem(pos=pts, size=10, symbol=cfg.get('symbol', 't'), 
                                              brush=cfg.get('color', 'g'), pen=pg.mkPen('w'), name=kw)
                    item.setZValue(20)
                    self.plot_item.addItem(item)
                    self.landmark_items.append(item)

    def set_current_point(self, x, y):
        self.current_pos_scatter.setData([x], [y])

    def update_single_trajectory(self, log_name, x_pts, y_pts):
        """ 仅更新指定名称的轨迹数据（用于时间范围截取显示） """
        if log_name in self.traj_items:
            self.traj_items[log_name].setData(x_pts, y_pts)