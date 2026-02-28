import matplotlib.pyplot as plt
import numpy as np
import glob
import os
import sys
import io

# 解决控制台输出乱码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def plot_connected_lines(folder_path, interval=0.5):
    """
    读取txt文件，按X轴排序，每隔 interval(0.5m) 采样一个点，并绘制折线图。
    """
    
    # 1. 寻找文件
    txt_files = sorted(glob.glob(os.path.join(folder_path, "*.txt")))
    if not txt_files:
        print(f"错误: 在 {folder_path} 下未找到 .txt 文件")
        return

    print(f"找到 {len(txt_files)} 个文件，准备绘制折线图...")

    plt.figure(figsize=(12, 8))
    
    # 使用 tab10 色盘，支持10种不同颜色自动循环
    colors = plt.cm.tab10(np.linspace(0, 1, len(txt_files)))
    
    has_valid_data = False

    for i, file_path in enumerate(txt_files):
        filename = os.path.basename(file_path)
        try:
            # 读取数据 (skiprows=1 跳过表头，如果没有表头请改为 0)
            data = np.loadtxt(file_path, skiprows=1)
            
            if data.ndim == 1: data = data.reshape(1, -1)
            if data.shape[0] == 0: continue

            raw_x = data[:, 0] # 第一列：距离
            raw_y = data[:, 1] # 第二列：误差

            # --- 关键步骤 1: 排序 ---
            # 画折线图必须按 X 轴排序，否则线条会左右乱窜
            sort_idx = np.argsort(raw_x)
            sorted_x = raw_x[sort_idx]
            sorted_y = raw_y[sort_idx]

            # --- 关键步骤 2: 稀疏化 (采样) ---
            keep_x = []
            keep_y = []
            
            # 初始化一个极小值，保证第一个点能被选中
            last_val = -9999.0
            
            for k in range(len(sorted_x)):
                curr_x = sorted_x[k]
                # 只有当 当前距离 与 上一次记录的距离 相差超过 0.5 时才记录
                if curr_x - last_val >= interval:
                    keep_x.append(curr_x)
                    keep_y.append(sorted_y[k])
                    last_val = curr_x
            
            # 转为 numpy 数组
            plot_x = np.array(keep_x)
            plot_y = np.array(keep_y)

            if len(plot_x) < 2:
                print(f"警告: 文件 {filename} 采样后点数不足以画线。")
                continue

            # --- 关键步骤 3: 绘制折线 ---
            # marker='o': 显示数据点的小圆圈
            # linestyle='-': 实线连接 (这是默认值，写出来明确一下)
            plt.plot(plot_x, plot_y, 
                     marker='o', markersize=4, linestyle='-', linewidth=1.5,
                     label=filename, color=colors[i % 10], alpha=0.8)

            print(f"已绘制: {filename} (原始点数 {len(raw_x)} -> 采样后 {len(plot_x)})")
            has_valid_data = True

        except Exception as e:
            print(f"处理文件 {filename} 失败: {e}")

    if has_valid_data:
        # 图表设置
        plt.title(f"Lidar Error Trend (Sampled every {interval}m)", fontsize=16)
        plt.xlabel("Distance (m)", fontsize=12)
        plt.ylabel("Error (m)", fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.legend()
        
        output_name = "./out/connected_lines_plot.png"
        plt.savefig(output_name, dpi=150)
        print(f"\n图表已保存为: {output_name}")
        plt.show()
    else:
        print("没有有效数据可绘图。")

if __name__ == "__main__":
    # 当前目录
    TXT_FOLDER = "./out/"
    # 设置采样间隔为 0.5 米
    plot_connected_lines(TXT_FOLDER, interval=0.2)