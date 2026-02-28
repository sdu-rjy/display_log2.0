# -*- coding: utf-8 -*-

import os
import re
from datetime import datetime
import statistics
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from pathlib import Path

# ==================== 配置 ====================
LOG_FOLDER = ""  # 日志文件夹路径

# 全局变量：存储所有解析出的定位记录
all_records = []  

# 终极版正则表达式：对多余的空格完全免疫
pattern = re.compile(
    r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d{3}.*?'  # 组1：提取时间
    r'type\s*=\s*(\d+)\s*\(\s*'                        # 组2：提取 type（例如 20）
    r'([-+]?\d*\.?\d+)\s+'                             # 组3：提取 X
    r'([-+]?\d*\.?\d+)\s+'                             # 组4：提取 Y
    r'[-+]?\d*\.?\d+\s+'                               # 忽略 Z 
    r'[-+]?\d*\.?\d+\s+'                               # 忽略 Roll
    r'[-+]?\d*\.?\d+\s+'                               # 忽略 Pitch
    r'([-+]?\d*\.?\d+)\s*\)'                           # 组5：提取 RZ / Yaw (偏航角)
)

def load_all_logs_from_folder(folder_path):
    """从指定文件夹加载所有日志文件并解析定位记录"""
    global all_records
    all_records.clear()
    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        raise ValueError("指定路径不是有效文件夹")

    # 深度搜索文件夹内所有的日志文件（包含子文件夹）
    log_files = []
    for ext in ('*.log', '*.txt', '*.LOG', '*.TXT'):  
        log_files.extend(folder.rglob(ext))
    # 补充查找没有后缀名的文件
    log_files.extend([f for f in folder.rglob('*') if f.is_file() and not f.suffix])
    
    # 文件路径去重
    log_files = list(set(log_files))

    matched_lines = 0

    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    match = pattern.search(line)
                    if match:
                        try:
                            time_str = match.group(1)
                            log_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                            log_type = int(match.group(2))
                            x = float(match.group(3))
                            y = float(match.group(4))
                            rz = float(match.group(5))
                            all_records.append({
                                'time': log_time,
                                'type': log_type,
                                'x': x,
                                'y': y,
                                'rz': rz
                            })
                            matched_lines += 1
                        except Exception:
                            # 如果这单行数据转换出错，只跳过这一行，绝不跳过整个文件！
                            continue
        except Exception:
            # 文件如果是二进制或系统文件打不开，直接跳过处理下一个
            continue

    all_records.sort(key=lambda r: r['time'])
    
    if matched_lines > 0:
        messagebox.showinfo("加载成功", f"扫描了 {len(log_files)} 个文件\n共成功提取了 {matched_lines} 条定位数据！")
    return matched_lines > 0

def get_unique_times():
    return sorted({r['time'].strftime("%Y-%m-%d %H:%M:%S") for r in all_records})

def get_unique_types():
    return sorted(set(r['type'] for r in all_records))

def analyze_data():
    start_str = combo_start.get()
    end_str = combo_end.get()
    try:
        target_type = int(combo_type.get())
    except ValueError:
        messagebox.showwarning("警告", "请选择有效的类型（type）")
        return

    try:
        start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
        end_dt = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")
    except Exception:
        messagebox.showwarning("警告", "请选择有效的时间范围")
        return

    if start_dt > end_dt:
        messagebox.showwarning("警告", "起始时间不能晚于结束时间")
        return

    filtered = [
        r for r in all_records
        if start_dt <= r['time'] <= end_dt and r['type'] == target_type
    ]

    if not filtered:
        result_text.delete(1.0, tk.END)
        result_text.insert(tk.END, "! 在所选时间段和类型下，未找到任何定位数据。\n")
        return

    xs = [r['x'] for r in filtered]
    ys = [r['y'] for r in filtered]
    rzs = [r['rz'] for r in filtered]

    def stats(values, name):
        max_v = max(values)
        min_v = min(values)
        mean_v = statistics.mean(values)
        std_v = statistics.stdev(values) if len(values) > 1 else 0.0
        range_v = max_v - min_v
        return (
            f"{name} 统计:\n"
            f"  最大值: {max_v:.6f}\n"
            f"  最小值: {min_v:.6f}\n"
            f"  平均值: {mean_v:.6f}\n"
            f"  波动范围: {range_v:.6f}\n"
            f"  标准差: {std_v:.6f}\n\n"
        )

    output = (
        f"✅ 分析完成！\n"
        f"时间段: {start_str} ~ {end_str}\n"
        f"类型: type = {target_type}\n"
        f"共 {len(filtered)} 条记录\n\n"
        + stats(xs, "X")
        + stats(ys, "Y")
        + stats(rzs, "RZ (偏航角)")
    )

    result_text.delete(1.0, tk.END)
    result_text.insert(tk.END, output)

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
            messagebox.showwarning("提示", "未在该文件夹及其子目录中找到符合格式的定位数据。\n请确认日志内容是否真实包含目标字段。")
    except Exception as e:
        messagebox.showerror("加载失败", f"无法加载日志：{e}")

def init_gui():
    global combo_start, combo_end, combo_type, result_text

    times = get_unique_times()
    types = get_unique_types()

    if not times or not types:
        return

    # 清空初始提示
    for widget in root.winfo_children():
        widget.destroy()

    # 设置行列权重，让第5行（文本框所在行）可以随窗口自动拉伸
    root.grid_rowconfigure(5, weight=1)
    root.grid_columnconfigure(0, weight=1)
    root.grid_columnconfigure(1, weight=1)

    # 起始时间
    tk.Label(root, text="起始时间:", font=("Arial", 10)).grid(row=0, column=0, padx=10, pady=5, sticky='w')
    combo_start = ttk.Combobox(root, values=times, state="readonly", width=25)
    combo_start.set(times[0])
    combo_start.grid(row=0, column=1, padx=10, pady=5, sticky='w')

    # 结束时间
    tk.Label(root, text="结束时间:", font=("Arial", 10)).grid(row=1, column=0, padx=10, pady=5, sticky='w')
    combo_end = ttk.Combobox(root, values=times, state="readonly", width=25)
    combo_end.set(times[-1])
    combo_end.grid(row=1, column=1, padx=10, pady=5, sticky='w')

    # 类型选择
    tk.Label(root, text="定位类型 (type):", font=("Arial", 10)).grid(row=2, column=0, padx=10, pady=5, sticky='w')
    combo_type = ttk.Combobox(root, values=types, state="readonly", width=25)
    combo_type.set(types[0])
    combo_type.grid(row=2, column=1, padx=10, pady=5, sticky='w')

    # 分析按钮
    btn_analyze = tk.Button(root, text="开始分析", command=analyze_data, bg="#4CAF50", fg="white", font=("Arial", 10))
    btn_analyze.grid(row=3, column=0, columnspan=2, pady=15)

    # 结果显示区域 (加大了 width 和 height，并加上了 sticky='nsew' 允许拉伸)
    tk.Label(root, text="分析结果:", font=("Arial", 10, "bold")).grid(row=4, column=0, sticky='w', padx=10)
    result_text = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=100, height=30, font=("Consolas", 10))
    result_text.grid(row=5, column=0, columnspan=2, padx=10, pady=(0, 10), sticky='nsew')

# ==================== 启动程序 ====================
if __name__ == "__main__":
    root = tk.Tk()
    root.title("定位日志批量分析工具")
    
    # 【修改这里】把初始窗口调大，比如 850x650
    root.geometry("850x650")
    root.resizable(True, True)

    # 这里的组件用 pack 布局（仅用于初始界面）
    initial_frame = tk.Frame(root)
    initial_frame.pack(expand=True, fill='both')
    
    tk.Label(initial_frame, text="请选择包含日志文件的文件夹", font=("Arial", 12, "bold")).pack(pady=50)
    tk.Button(initial_frame, text="选择文件夹", command=select_folder_and_load, font=("Arial", 10), width=20).pack(pady=10)
    tk.Label(initial_frame, text="支持 .log / .txt，自动扫描所有子文件夹", font=("Arial", 9), fg="gray").pack()

    root.mainloop()