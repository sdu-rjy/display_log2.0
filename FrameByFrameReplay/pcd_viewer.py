import sys
import io
import open3d as o3d
import os
import glob
import numpy as np

# 强制设置标准输出为 UTF-8，解决中文乱码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def parse_pcd_viewpoint(file_path):
    """解析 PCD 文件头部的 VIEWPOINT 字段"""
    translation = np.array([0.0, 0.0, 0.0])
    rotation_q = np.array([1.0, 0.0, 0.0, 0.0]) # w, x, y, z
    
    try:
        with open(file_path, 'rb') as f:
            while True:
                line = f.readline().decode('utf-8', errors='ignore')
                if line.startswith('DATA'): 
                    break
                if line.startswith('VIEWPOINT'):
                    parts = line.strip().split()
                    if len(parts) >= 8:
                        translation = np.array([float(parts[1]), float(parts[2]), float(parts[3])])
                        rotation_q = np.array([float(parts[4]), float(parts[5]), float(parts[6]), float(parts[7])])
                    break
    except Exception as e:
        print(f"解析 Viewpoint 失败: {e}")

    R = o3d.geometry.get_rotation_matrix_from_quaternion(rotation_q)
    transform_matrix = np.eye(4)
    transform_matrix[:3, :3] = R
    transform_matrix[:3, 3] = translation
    return transform_matrix

class PointCloudPlayer:
    def __init__(self, map_path, frames_dir):
        self.frames_dir = frames_dir
        self.current_index = 0
        
        self.pcd_files = sorted(glob.glob(os.path.join(frames_dir, "*.pcd")))
        
        if not self.pcd_files:
            print(f"错误: 在 {frames_dir} 中没有找到 .pcd 文件")
            sys.exit(1)
            
        print(f"共加载了 {len(self.pcd_files)} 帧动态点云。")

        self.vis = o3d.visualization.VisualizerWithKeyCallback()
        self.vis.create_window(window_name="PCD Player (按 R 回正)", width=1280, height=720)
        self.vis.get_render_option().point_size = 5.0
        self.current_arrow = None
        # 加载静态地图
        print(f"正在加载静态地图: {map_path} ...")
        self.static_map = o3d.io.read_point_cloud(map_path)
        if self.static_map.is_empty():
            print("警告: 地图文件为空或读取失败")
            self.map_center = np.array([0, 0, 0])
        else:
            self.static_map.paint_uniform_color([0.5, 0.5, 0.5]) # 灰色
            self.vis.add_geometry(self.static_map)
            # 获取地图中心，用于回正时对齐
            self.map_center = self.static_map.get_center()

        self.current_frame = o3d.geometry.PointCloud()
        self.update_frame(0)

        # ================= 按键注册 =================
        # 262: 右箭头 (下一帧)
        # 263: 左箭头 (上一帧)
        # 82 : R 键 (Reset View / 回正)
        self.vis.register_key_callback(262, self.next_frame)
        self.vis.register_key_callback(263, self.prev_frame)
        self.vis.register_key_callback(82, self.reset_view) 
        
        print("\n=== 操作指南 ===")
        print("按 [右箭头] : 下一帧")
        print("按 [左箭头] : 上一帧")
        print("按 [R]      : 视角回正 (XY平面俯视)")
        print("按 [Q]      : 退出")
        print("================")

        # 启动时自动回正一次视角
        self.reset_view(self.vis)

    def reset_view(self, vis):
        """
        一键回正视角：俯视 XY 平面
        """
        ctr = vis.get_view_control()
        
        # 1. set_lookat: 相机观察的焦点 (设为地图中心)
        ctr.set_lookat(self.map_center)
        
        # 2. set_front: 相机镜头的朝向向量 (垂直向下，即 Z 轴正向指向屏幕外)
        # [0, 0, 1] 表示相机位于 Z 轴上方
        ctr.set_front([0, 0, 1])
        
        # 3. set_up: 屏幕的"上方"对应的轴 (Y 轴朝上)
        ctr.set_up([0, 1, 0])
        
        # 4. set_zoom: 缩放比例 (可选)
        ctr.set_zoom(0.8)
        
        print(">> 视角已回正 (XY 平面)", flush=True)
        return False

    def update_frame(self, index):
        if index < 0 or index >= len(self.pcd_files):
            return

        file_path = self.pcd_files[index]
        file_name = os.path.basename(file_path)

        # === 1. 读取点云 (含强度处理) ===
        try:
            pcd_t = o3d.t.io.read_point_cloud(file_path)
            if 'intensity' in pcd_t.point:
                intensities = pcd_t.point['intensity'].numpy().flatten()
            else:
                intensities = np.zeros(len(pcd_t.point.positions))
            new_cloud = pcd_t.to_legacy()
        except Exception as e:
            print(f"强度读取失败: {e}")
            new_cloud = o3d.io.read_point_cloud(file_path)
            intensities = np.zeros(len(new_cloud.points))

        # 坐标变换
        transform_mat = parse_pcd_viewpoint(file_path)
        new_cloud.transform(transform_mat)
        
        # 打印坐标
        pos = transform_mat[:3, 3]
        print(f"[{index+1:03d}/{len(self.pcd_files)}] {file_name} | Origin: ({pos[0]:6.2f}, {pos[1]:6.2f}, {pos[2]:6.2f})", flush=True)

        # === 2. 颜色与层级逻辑 ===
        points = np.asarray(new_cloud.points)
        if len(points) > 0:
            # 2.1 颜色设置
            new_cloud.paint_uniform_color([0.0, 0.75, 1.0]) # 底色：天蓝色
            colors = np.asarray(new_cloud.colors)
            
            # 筛选高强度点
            mask = intensities > 250
            colors[mask] = [1.0, 0.0, 0.0] # 高亮色：红色
            new_cloud.colors = o3d.utility.Vector3dVector(colors)

            # 2.2 Z轴分层 (关键修改！)
            # 先把所有点压平到 0
            points[:, 2] = 0.0
            
            # 【核心改动】把红色的点稍微抬高 (例如 0.2米)
            # 这样在渲染时，红色点会物理位于橙色点上方，确保不被遮挡
            points[mask, 2] = 0.2
            
            new_cloud.points = o3d.utility.Vector3dVector(points)

        # === 3. 箭头 (保持在最高层，避免被红色点遮挡) ===
        arrow = o3d.geometry.TriangleMesh.create_arrow(
            cylinder_radius=0.2, cone_radius=0.5, cylinder_height=1.0, cone_height=0.5
        )
        arrow.paint_uniform_color([0.0, 0.0, 1.0]) 
        arrow.compute_vertex_normals()
        
        R_fix = o3d.geometry.get_rotation_matrix_from_axis_angle([0, np.pi/2, 0])
        arrow.rotate(R_fix, center=[0,0,0])
        arrow.transform(transform_mat)
        
        # 箭头设为更高的位置 (例如 0.5)，确保它是最顶层的
        arrow_verts = np.asarray(arrow.vertices)
        arrow_verts[:, 2] = 0.5 
        arrow.vertices = o3d.utility.Vector3dVector(arrow_verts)

        # === 4. 刷新显示 ===
        if self.current_frame.is_empty():
            self.current_frame = new_cloud
            self.vis.add_geometry(self.current_frame)
        else:
            self.vis.remove_geometry(self.current_frame, reset_bounding_box=False)
            self.current_frame = new_cloud
            self.vis.add_geometry(self.current_frame, reset_bounding_box=False)

        if self.current_arrow is not None:
            self.vis.remove_geometry(self.current_arrow, reset_bounding_box=False)
        self.current_arrow = arrow
        self.vis.add_geometry(self.current_arrow, reset_bounding_box=False)

    def next_frame(self, vis):
        if self.current_index < len(self.pcd_files) - 1:
            self.current_index += 1
            self.update_frame(self.current_index)
        else:
            print("已经是最后一帧了", flush=True)
        return False

    def prev_frame(self, vis):
        if self.current_index > 0:
            self.current_index -= 1
            self.update_frame(self.current_index)
        else:
            print("已经是第一帧了", flush=True)
        return False

    def run(self):
        self.vis.poll_events()
        self.vis.update_renderer()
        self.vis.run()
        self.vis.destroy_window()

if __name__ == "__main__":
    # 配置路径
    MAP_PATH = "./map/global_map.pcd"      
    FRAMES_FOLDER = "scans_directory" 
    
    if not os.path.exists(MAP_PATH):
        with open("test_map.pcd", "w") as f: pass 
    if not os.path.exists(FRAMES_FOLDER):
        os.makedirs(FRAMES_FOLDER, exist_ok=True)

    try:
        player = PointCloudPlayer(MAP_PATH, FRAMES_FOLDER)
        player.run()
    except Exception as e:
        print(f"发生错误: {e}")