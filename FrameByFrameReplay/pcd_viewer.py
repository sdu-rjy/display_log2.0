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
        self.vis.get_render_option().point_size = 8.0  # 增大全局点大小，让 reflector 地图更明显
        
        self.current_arrow = None
        self.map_geometries = {}  # 存储所有地图的几何体对象
        self.map_styles = {}  # 存储所有地图的样式信息
        
        # 加载静态地图（支持单个文件或文件夹）
        if os.path.isdir(map_path):
            # 如果是文件夹，加载所有 .pcd 文件
            self.load_all_maps(map_path)
        else:
            # 如果是单个文件，直接加载
            self.load_single_map(map_path)
            
        # 计算地图中心（用于回正）
        if self.map_geometries:
            # 合并所有地图的点来计算中心
            all_points = []
            for pcd in self.map_geometries.values():
                if not pcd.is_empty():
                    all_points.append(np.asarray(pcd.points))
            if all_points:
                combined = np.vstack(all_points)
                self.map_center = np.mean(combined, axis=0)
            else:
                self.map_center = np.array([0, 0, 0])
        else:
            self.map_center = np.array([0, 0, 0])
            
        print(f"地图中心: ({self.map_center[0]:.2f}, {self.map_center[1]:.2f}, {self.map_center[2]:.2f})")

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

    def get_map_style(self, filename):
        """根据地图文件名返回颜色和点大小"""
        name_lower = filename.lower()
        
        if 'global' in name_lower or 'normal_map' in name_lower:
            # 全局地图：灰色，点大小 1（细密）
            return {'color': [0.5, 0.5, 0.5], 'point_size': 1.0, 'description': '全局地图（灰色，小点）', 'z_offset': 0.0}
        elif 'reflector' in name_lower or 'mark' in name_lower or 'feature' in name_lower:
            # 反光板/特征地图：橙色，点大小 10（醒目），Z 轴抬高
            return {'color': [1.0, 0.5, 0.0], 'point_size': 10.0, 'description': '反光板地图（橙色，大点）', 'z_offset': 0.3}
        elif 'local' in name_lower:
            # 局部地图：绿色，点大小 3
            return {'color': [0.0, 0.8, 0.0], 'point_size': 3.0, 'description': '局部地图（绿色，中点）', 'z_offset': 0.0}
        else:
            # 其他地图：蓝色，点大小 5
            return {'color': [0.0, 0.5, 1.0], 'point_size': 5.0, 'description': f'其他地图（蓝色，中点）', 'z_offset': 0.0}

    def load_single_map(self, file_path):
        """加载单个地图文件"""
        filename = os.path.basename(file_path)
        print(f"正在加载地图: {filename} ...")
        
        pcd = o3d.io.read_point_cloud(file_path)
        if pcd.is_empty():
            print(f"警告: 地图文件 {filename} 为空或读取失败")
            return
            
        # 根据文件名设置样式
        style = self.get_map_style(filename)
        print(f"  - {style['description']}")
        
        # 应用颜色
        pcd.paint_uniform_color(style['color'])
        
        # 如果有 Z 轴偏移，调整点的位置
        if style.get('z_offset', 0.0) != 0.0:
            points = np.asarray(pcd.points)
            z_offset = style['z_offset']
            # 抬高 Z 轴，使该图层显示在其他图层上方
            points[:, 2] += z_offset
            pcd.points = o3d.utility.Vector3dVector(points)
        
        # Open3D 的点大小是全局设置，无法为不同的点云设置不同的点大小
        # 因此我们使用颜色和 Z 轴分层来区分
        self.map_styles[filename] = style
        
        self.vis.add_geometry(pcd)
        self.map_geometries[filename] = pcd

    def load_all_maps(self, folder_path):
        """加载文件夹中的所有地图文件"""
        print(f"\n正在加载文件夹中的所有地图: {folder_path}")
        map_files = sorted(glob.glob(os.path.join(folder_path, "*.pcd")))
        
        if not map_files:
            print(f"警告: 在 {folder_path} 中没有找到 .pcd 文件")
            return
            
        print(f"找到 {len(map_files)} 个地图文件:")
        
        for map_file in map_files:
            self.load_single_map(map_file)
            
        print(f"成功加载 {len(self.map_geometries)} 个地图文件\n")

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
            cylinder_radius=0.1, cone_radius=0.25, cylinder_height=0.5, cone_height=0.25
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
    # 配置路径 - 支持文件夹路径或单个文件路径
    MAP_PATH = "./map"      # 修改为文件夹路径，会加载所有地图文件
    FRAMES_FOLDER = "scans_directory" 
    
    # 检查并创建必要目录
    if not os.path.exists(MAP_PATH):
        os.makedirs(MAP_PATH, exist_ok=True)
        print(f"创建地图目录: {MAP_PATH}")
    if not os.path.exists(FRAMES_FOLDER):
        os.makedirs(FRAMES_FOLDER, exist_ok=True)

    try:
        player = PointCloudPlayer(MAP_PATH, FRAMES_FOLDER)
        player.run()
    except Exception as e:
        print(f"发生错误: {e}")
        import traceback
        traceback.print_exc()