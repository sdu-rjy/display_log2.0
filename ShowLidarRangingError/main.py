import open3d as o3d
import numpy as np
import matplotlib.pyplot as plt
import glob
import os
import sys
import io

# --- 修复 UnicodeEncodeError ---
# 强制将标准输出和错误输出设置为 UTF-8，防止在某些 Windows 环境下打印中文报错
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def process_lidar_data(pcd_folder, dist_range=(3.0, 5.0), output_txt="./out/lidar_error_data.txt"):
    # --- 步骤 2.1: 加载指定文件的全部pcl点云数据 ---
    pcd_files = sorted(glob.glob(os.path.join(pcd_folder, "*.pcd")))
    if len(pcd_files) < 2:
        print(f"错误: 在 {pcd_folder} 中需要至少 2 个 PCD 文件来进行误差计算。")
        return

    print(f"开始加载 {len(pcd_files)} 个 PCD 文件...")
    
    # --- 步骤 2.2: 将这些点云数据放在一个数据结构中 ---
    point_clouds_vector = []
    
    for i, f in enumerate(pcd_files):
        pcd = o3d.io.read_point_cloud(f)
        points = np.asarray(pcd.points)
        
        if i > 0 and len(points) != len(point_clouds_vector[0]):
            print(f"警告: 文件 {os.path.basename(f)} 点数不一致，这可能导致 ID 对应错误！")
            return

        point_clouds_vector.append(points)
        # 打印进度
        sys.stdout.write(f"\r已加载: {i+1}/{len(pcd_files)}")
        sys.stdout.flush()
    print("\n数据加载完成，开始计算...")

    # 转换为 numpy 矩阵: [帧数 N, 点数 M, 坐标 3]
    data_stack = np.array(point_clouds_vector)
    num_frames, num_points, _ = data_stack.shape

    # --- 步骤 2.3: 计算测距长度和测量误差 ---
    
    # 1. 计算 "测距长度" (X轴) - 基于第0帧
    frame_0_points = data_stack[0] 
    dist_lengths = np.linalg.norm(frame_0_points, axis=1)

    # 2. 计算 "测量误差" (Y轴) - 所有帧两两之间的最大欧式距离
    max_errors = np.zeros(num_points)
    
    print("正在计算最大欧式误差 (两两帧对比)...")
    for i in range(num_frames):
        for j in range(i + 1, num_frames):
            diff = data_stack[i] - data_stack[j]
            pair_dists = np.linalg.norm(diff, axis=1)
            max_errors = np.maximum(max_errors, pair_dists)

    # --- 步骤 2.4: 筛选范围、导出TXT、绘图 ---
    
    min_r, max_r = dist_range
    
    # 核心修改：增加了 (max_errors <= 0.1) 的条件
    # 只有同时满足：距离在指定范围内 且 误差小于等于 0.1m 的点才会被保留
    mask = (dist_lengths >= min_r) & \
           (dist_lengths <= max_r) & \
           (max_errors <= 0.041)
    
    valid_dists = dist_lengths[mask]
    valid_errors = max_errors[mask]
    
    print(f"\n筛选条件: 距离 {min_r}-{max_r}m 且 误差 <= 0.041m")
    print(f"满足条件的点数: {len(valid_dists)}")

    # 1. 写入 TXT 文件 (加入 encoding='utf-8' 修复编码错误)
    try:
        with open(output_txt, "w", encoding="utf-8") as f:
            f.write("Distance(m)\tMaxError(m)\n")
            for d, e in zip(valid_dists, valid_errors):
                f.write(f"{d:.6f}\t{e:.6f}\n")
        print(f"数据已保存到: {output_txt}")
    except IOError as e:
        print(f"保存文件失败: {e}")

    # 2. 绘制图表
    if len(valid_dists) == 0:
        print("没有满足条件的点，无法绘图。")
        return

    plt.figure(figsize=(10, 6))
    
    # 绘制散点 (移除 Average Trend)
    plt.scatter(valid_dists, valid_errors, s=2, c='blue', alpha=0.5, label='Point Error')
    
    plt.title(f"LiDAR Measurement Error ({min_r}m - {max_r}m)")
    plt.xlabel("Distance from Origin (m)")
    plt.ylabel("Measurement Error (m)")
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    
    # 强制设置Y轴范围稍微大一点点，以免0.1就在最顶端看不清
    plt.ylim(0, 0.11) 

    plt.savefig("./out/lidar_error_plot.png")
    print("图表已保存为 ./out/lidar_error_plot.png")
    plt.show()

if __name__ == "__main__":
    # 配置区域
    PCD_FOLDER = "./logs" 
    
    # 自动生成测试数据 (如果文件夹不存在)
    if not os.path.exists(PCD_FOLDER):
        print(f"未找到 {PCD_FOLDER}...")
    
    # 运行: 展示 3m 到 5m 范围内的误差
    process_lidar_data(PCD_FOLDER, dist_range=(1.0, 20.0))