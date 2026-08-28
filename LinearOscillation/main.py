# -*- coding: utf-8 -*-

import os
import re
from datetime import datetime
import statistics
import math
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from pathlib import Path

# 导入科学计算库
import numpy as np

# 导入绘图库以及 Tkinter 嵌入相关的模块
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

# ==================== 配置 ====================
LOG_FOLDER = ""
all_records = []  

# 统一日志解析：兼容新格式 `HH:MM:SS.mmm` 与旧格式 `HH:MM:SS,mmm`
NUMBER_PATTERN = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
LOCATION_PATTERN = re.compile(
    rf"(?P<timestamp>\d{{4}}-\d{{2}}-\d{{2}}\s+\d{{2}}:\d{{2}}:\d{{2}}[.,]\d{{3}}).*?"
    rf"Location_state\s*=\s*(?P<state>[\w:]+)"
    rf".*?score\s*=\s*(?P<score>{NUMBER_PATTERN})"
    rf".*?type\s*=\s*(?P<type>\d+)"
    rf"\s*\(\s*(?P<coords>[^)]*)\)"
)

def parse_log_timestamp(value):
    """解析新旧日志时间戳，并保留毫秒精度。"""
    normalized = value.replace(',', '.')
    return datetime.strptime(normalized, "%Y-%m-%d %H:%M:%S.%f")

def format_log_timestamp(value):
    """用于下拉框显示，固定输出到毫秒。"""
    return value.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

def parse_location_line(line):
    if "Location_state" not in line:
        return None
    match = LOCATION_PATTERN.search(line)
    if not match:
        return None
    coords = [float(v) for v in re.findall(NUMBER_PATTERN, match.group("coords"))]
    if len(coords) < 6:
        return None
    return {
        'time': parse_log_timestamp(match.group("timestamp")),
        'state': match.group("state"),
        'score': float(match.group("score")),
        'type': int(match.group("type")),
        'x': coords[0],
        'y': coords[1],
        'rz': coords[5],
    }

def load_all_logs_from_folder(folder_path):
    global all_records
    all_records.clear()
    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        raise ValueError("指定路径不是有效文件夹")

    log_files = []
    for ext in ('*.log', '*.txt', '*.LOG', '*.TXT'):  
        log_files.extend(folder.rglob(ext))
    log_files.extend([f for f in folder.rglob('*') if f.is_file() and not f.suffix])
    log_files = list(set(log_files))

    matched_lines = 0
    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    try:
                        record = parse_location_line(line)
                        if record is not None:
                            all_records.append(record)
                            matched_lines += 1
                    except Exception:
                        # 单行格式异常只跳过该行，不影响后续日志。
                        continue
        except Exception:
            continue

    all_records.sort(key=lambda r: r['time'])
    if matched_lines > 0:
        messagebox.showinfo("加载成功", f"扫描了 {len(log_files)} 个文件\n共成功提取了 {matched_lines} 条定位数据！")
    return matched_lines > 0

def get_unique_times():
    return sorted({format_log_timestamp(r['time']) for r in all_records})

def get_unique_types():
    return sorted(set(r['type'] for r in all_records))

def analyze_and_plot():
    start_str = combo_start.get()
    end_str = combo_end.get()
    try:
        target_type = int(combo_type.get())
    except ValueError:
        messagebox.showwarning("警告", "请选择有效的类型（type）")
        return

    start_dt = parse_log_timestamp(start_str)
    end_dt = parse_log_timestamp(end_str)

    if start_dt > end_dt:
        messagebox.showwarning("警告", "起始时间不能晚于结束时间")
        return

    filtered = [r for r in all_records if start_dt <= r['time'] <= end_dt and r['type'] == target_type]

    if len(filtered) < 2:
        messagebox.showwarning("数据不足", "所选范围内数据少于2条，无法拟合直线。")
        return

    # 1. 提取数据转换为 Numpy 数组
    xs = np.array([r['x'] for r in filtered])
    ys = np.array([r['y'] for r in filtered])
    rzs = np.array([r['rz'] for r in filtered])
    points = np.column_stack((xs, ys))

    # 2. PCA 拟合直线 (正交距离回归)
    mean_pt = points.mean(axis=0)
    centered = points - mean_pt
    cov_matrix = np.cov(centered, rowvar=False)
    evals, evecs = np.linalg.eigh(cov_matrix)
    direction = evecs[:, 1]  
    dx, dy = direction

    # 统一方向
    traj_vec = points[-1] - points[0]
    if np.dot(direction, traj_vec) < 0:
        dx, dy = -dx, -dy

    line_angle = np.arctan2(dy, dx)

    # 3. 计算垂直距离
    normal_vec = np.array([-dy, dx])
    distances = np.abs(np.dot(centered, normal_vec))

    # 4. 计算朝向角误差
    heading_errors = rzs - line_angle
    heading_errors = (heading_errors + np.pi) % (2 * np.pi) - np.pi

    # 5. 统计结果输出
    def format_stats(data, unit="m"):
        return (
            f"  最大值: {np.max(data):.6f} {unit}\n"
            f"  最小值: {np.min(data):.6f} {unit}\n"
            f"  平均值: {np.mean(data):.6f} {unit}\n"
            f"  绝对平均误差(MAE): {np.mean(np.abs(data)):.6f} {unit}\n"
            f"  标准差(波动): {np.std(data):.6f} {unit}\n"
        )

    output = (
        f"✅ 分析完成！\n"
        f"数据量: {len(filtered)} 条 | 类型: {target_type}\n"
        f"拟合直线朝向角: {line_angle:.6f} rad ({np.degrees(line_angle):.2f}°)\n"
        f"-------------------------------------\n"
        f"【位置误差（点到直线垂直距离）】\n"
        + format_stats(distances, "m") +
        f"-------------------------------------\n"
        f"【朝向误差（车体 RZ - 直线朝向）】\n"
        + format_stats(heading_errors, "rad")
    )
    result_text.delete(1.0, tk.END)
    result_text.insert(tk.END, output)

    # 6. 在右侧 Frame 中绘制图像
    plot_on_canvas(xs, ys, mean_pt, dx, dy, target_type)

def plot_on_canvas(xs, ys, mean_pt, dx, dy, target_type):
    # 清空右侧之前画的图表
    for widget in right_frame.winfo_children():
        widget.destroy()

    # 创建一个 Figure 对象，而不是用 plt.subplots()，这样不会弹出新窗口
    fig = Figure(figsize=(6, 5), dpi=100)
    ax = fig.add_subplot(111)
    
    # 绘制散点
    ax.scatter(xs, ys, c='blue', s=10, label='Location Points', alpha=0.6)
    
    # 计算拟合直线的两个端点
    t_min = np.min((xs - mean_pt[0]) * dx + (ys - mean_pt[1]) * dy)
    t_max = np.max((xs - mean_pt[0]) * dx + (ys - mean_pt[1]) * dy)
    line_x = [mean_pt[0] + t_min * dx, mean_pt[0] + t_max * dx]
    line_y = [mean_pt[1] + t_min * dy, mean_pt[1] + t_max * dy]
    
    # 绘制拟合直线
    ax.plot(line_x, line_y, color='red', linewidth=2, label='Fitted Line')
    
    # 标记起点和终点
    ax.scatter(xs[0], ys[0], c='green', s=80, marker='^', label='Start', zorder=5)
    ax.scatter(xs[-1], ys[-1], c='purple', s=80, marker='s', label='End', zorder=5)

    # 设置图表属性
    ax.set_title(f'Trajectory & Line Fitting (Type: {target_type})')
    ax.set_xlabel('X Coordinate (m)')
    ax.set_ylabel('Y Coordinate (m)')
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.axis('equal') # 保证 X 和 Y 的比例尺相同，看图才不会变形
    
    fig.tight_layout()

    # 将 Figure 嵌入到 Tkinter 的 right_frame 中
    canvas = FigureCanvasTkAgg(fig, master=right_frame)
    canvas.draw()
    
    # 添加原生的 Matplotlib 工具栏（方便缩放、拖拽、保存图片）
    toolbar = NavigationToolbar2Tk(canvas, right_frame)
    toolbar.update()
    
    # 放置组件
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

# ==================== GUI 主程序 ====================
def select_folder_and_load():
    global LOG_FOLDER
    folder = filedialog.askdirectory(title="请选择包含日志文件的文件夹")
    if not folder:
        return
    LOG_FOLDER = folder
    try:
        success = load_all_logs_from_folder(LOG_FOLDER)
        if success:
            init_gui()
        else:
            messagebox.showwarning("提示", "未在该文件夹及其子目录中找到符合格式的定位数据。")
    except Exception as e:
        messagebox.showerror("加载失败", f"无法加载日志：{e}")

def init_gui():
    global combo_start, combo_end, combo_type, result_text, right_frame
    times = get_unique_times()
    types = get_unique_types()
    if not times or not types: return

    for widget in root.winfo_children():
        widget.destroy()

    # 创建主容器：左右分栏
    main_frame = tk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # 左侧：控制面板和结果文本
    left_frame = tk.Frame(main_frame, width=400)
    left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
    # 阻止左侧框架根据内容自动缩放变窄
    left_frame.pack_propagate(False) 

    # 右侧：用于放置图表
    right_frame = tk.Frame(main_frame, bg="white", relief=tk.SUNKEN, bd=1)
    right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    # ========== 左侧组件搭建 ==========
    controls_frame = tk.Frame(left_frame)
    controls_frame.pack(fill=tk.X, pady=(0, 10))

    tk.Label(controls_frame, text="起始时间:", font=("Arial", 10)).grid(row=0, column=0, pady=5, sticky='w')
    combo_start = ttk.Combobox(controls_frame, values=times, state="readonly", width=22)
    combo_start.set(times[0])
    combo_start.grid(row=0, column=1, pady=5, sticky='w', padx=5)

    tk.Label(controls_frame, text="结束时间:", font=("Arial", 10)).grid(row=1, column=0, pady=5, sticky='w')
    combo_end = ttk.Combobox(controls_frame, values=times, state="readonly", width=22)
    combo_end.set(times[-1])
    combo_end.grid(row=1, column=1, pady=5, sticky='w', padx=5)

    tk.Label(controls_frame, text="定位类型 (type):", font=("Arial", 10)).grid(row=2, column=0, pady=5, sticky='w')
    combo_type = ttk.Combobox(controls_frame, values=types, state="readonly", width=22)
    combo_type.set(types[0])
    combo_type.grid(row=2, column=1, pady=5, sticky='w', padx=5)

    btn_analyze = tk.Button(left_frame, text="拟合分析与绘图", command=analyze_and_plot, bg="#2196F3", fg="white", font=("Arial", 11, "bold"))
    btn_analyze.pack(fill=tk.X, pady=10)

    tk.Label(left_frame, text="分析与统计结果:", font=("Arial", 10, "bold")).pack(anchor='w', pady=(5,0))
    result_text = scrolledtext.ScrolledText(left_frame, wrap=tk.WORD, font=("Consolas", 10))
    result_text.pack(fill=tk.BOTH, expand=True)

    # 初始状态在右侧提示一句
    tk.Label(right_frame, text="点击左侧【拟合分析与绘图】在此处显示轨迹", font=("Arial", 12), fg="gray").pack(expand=True)

if __name__ == "__main__":
    root = tk.Tk()
    root.title("定位数据分析与轨迹拟合系统")
    # 因为变成了左右布局，所以我把默认窗口调宽了
    root.geometry("1100x650")
    root.resizable(True, True)

    initial_frame = tk.Frame(root)
    initial_frame.pack(expand=True, fill='both')
    
    tk.Label(initial_frame, text="请选择包含日志文件的文件夹", font=("Arial", 14, "bold")).pack(pady=60)
    tk.Button(initial_frame, text="选择文件夹", command=select_folder_and_load, font=("Arial", 11), width=25, bg="#4CAF50", fg="white").pack(pady=10)
    tk.Label(initial_frame, text="读取完毕后，数据统计与轨迹图将同屏同显", font=("Arial", 10), fg="gray").pack()

    root.mainloop()