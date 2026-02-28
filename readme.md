# Display_Log 2.0 - 机器人定位日志分析工具集

## 📑 项目简介

本项目是一套专为机器人定位系统设计的日志分析和可视化工具集。基于 Python 开发，完美兼容 Windows 环境。项目包含多个独立的功能模块，旨在帮助研发和测试人员高效分析、可视化以及验证机器人定位系统的性能指标。

## 📂 目录结构

```text
f:\display_log2.0\
├── Display_location\          # 定位轨迹可视化工具 (二维轨迹、播放回放)
├── FrameByFrameReplay\        # 点云逐帧回放工具 (3D点云、激光雷达)
├── LinearOscillation\         # 轨迹拟合与线性度分析工具 (PCA直线拟合、横向误差)
├── ShowLidarRangingError\     # 激光雷达测距误差分析工具 (距离偏差统计)
├── StaticPose\                # 静态位姿分析工具 (静止状态漂移与波动)
└── readme.md                  # 本文档

```

---

## 🛠️ 环境配置规范（首次运行必看）

### 1. 硬件与系统要求

* **操作系统**: Windows 10 / Windows 11 (64位)
* **Python 版本**: 推荐 Python 3.9 - 3.11（`tool` 文件夹已提供 3.11.6 安装包）
* **硬件配置**: 建议 4 核 CPU + 8GB 内存以上，需配备支持 OpenGL 的独立显卡（用于 3D 点云渲染）。

### 2. Python 环境安装与命令说明

> **💡 【重要必读】关于 `python` 与 `py` 命令的区别**
> 在 Windows 下打开命令行（`Win + R` 输入 `cmd`），由于安装习惯不同，调用 Python 的命令可能不同：
> * `python`：标准命令。但前提是安装时**必须**勾选了 "Add Python to PATH"。如果没勾选，系统会报错或弹出微软应用商店。
> * `py`：Windows 专用的 Python 启动器魔法命令。即便你忘了配环境变量，只要正常安装了 Python，敲 `py` 也能 100% 成功唤醒 Python。
> 
> 
> **本教程后续统一推荐使用 `py` 前缀以避免由于环境变量带来的麻烦。**

#### 2.1 安装 Python

1. 进入 `tool` 文件夹，双击运行 `python-3.11.6-amd64.exe`。
2. **【极其关键】**：在安装界面底部，**务必勾选 "Add python.exe to PATH"**。
3. 点击 "Install Now" 完成安装。

#### 2.2 验证安装

按下 `Win + R` 键，输入 `cmd` 并回车，输入以下命令验证：

```bash
py --version
py -m pip --version

```

*(如果正常输出版本号如 `Python 3.11.6` 和 `pip 23.x.x`，说明安装完美成功！)*

#### 2.3 创建与激活虚拟环境（强烈推荐）

为了不污染你电脑上的全局环境，建议为本项目单独创建一个虚拟环境。在刚才的 `cmd` 窗口中依次执行：

```bash
# 1. 进入项目根目录 (请根据你的实际存放路径修改)
cd /d F:\display_log2.0

# 2. 创建名为 venv 的虚拟环境
py -m venv venv

# 3. 激活虚拟环境 (激活成功后，命令行前面会多出一个 (venv) 标识)
.\venv\Scripts\activate

```

### 3. 安装依赖库

在**确保虚拟环境已激活**（命令行带有 `(venv)` 前缀）的情况下，执行以下命令一键安装所有需要的依赖。
*(注：已默认添加清华镜像源，解决国内下载缓慢或超时报错的问题)*

```bash
py -m pip install PyQt5 pyqtgraph open3d numpy matplotlib -i https://pypi.tuna.tsinghua.edu.cn/simple

```

**验证依赖是否安装成功：**

```bash
py -c "import PyQt5, pyqtgraph, open3d, numpy, matplotlib; print('✅ 所有依赖安装成功！')"

```

---

## 🚀 各模块使用指南

### 1. Display_location - 定位轨迹可视化工具

**功能描述**: 二维可视化机器人定位轨迹，支持多轨迹对比、点击跳转、时间段筛选，并能叠加显示 Landmark（如反光板、二维码）。

* **数据准备**:
* 日志文件（`.log` 或 `.txt`）放入 `Display_location/logs/`
* 地图文件（`.pcd`）放入 `Display_location/map/`


* **启动命令**:
```bash
cd Display_location
py main.py

```


* **操作快捷键**:
* `←` / `→` : 上一帧 / 下一帧
* `↑` / `↓` : 上一个日志 / 下一个日志
* **鼠标左键**: 在右侧图表中点击轨迹点，左侧数据会自动跳转并同步。



### 2. FrameByFrameReplay - 点云逐帧回放工具

**功能描述**: 3D 逐帧播放激光雷达点云，高亮显示高强度点（如反光柱），并实时展示机器人的坐标原点与朝向。

* **数据准备**:
* 单帧点云（`.pcd` 格式，建议按时间戳命名）放入 `FrameByFrameReplay/scans_directory/`
* 全局地图命名为 `global_map.pcd` 放入 `FrameByFrameReplay/map/`


* **启动命令**:
```bash
cd FrameByFrameReplay
py pcd_viewer.py

```


* **操作快捷键**:
* `←` / `→` : 切换点云帧
* `R` : 一键视角回正（XY平面俯视）
* `Q` : 退出查看器



### 3. LinearOscillation - 轨迹拟合与线性度分析工具

**功能描述**: 基于 PCA 算法对机器人的直线运动进行完美直线拟合，计算小车偏离直线的**横向位置误差 (距离)** 以及 **朝向角波动 (RZ)**。

* **启动命令**:
```bash
cd LinearOscillation
py main.py

```


* **使用流程**: 点击【选择文件夹】加载日志 -> 在左侧下拉框选择起始时间与 `type` -> 点击【拟合分析与绘图】。
* **指标解读**:
* **位置误差 (MAE)**: 车体质心偏离理想直线的平均绝对垂直距离。
* **朝向误差**: 车体实际偏航角与拟合直线走向的夹角。



### 4. ShowLidarRangingError - 激光雷达测距误差分析工具

**功能描述**: 以特定帧为基准，分析雷达在不同距离段的绝对测距精度，自动生成误差分布散点图。

* **数据准备**: 点云文件放入 `ShowLidarRangingError/logs/`
* **启动命令**:
```bash
cd ShowLidarRangingError
py main.py

```


* *(注：距离区间及误差阈值过滤条件可在 `main.py` 源码头部快速修改)*

### 5. StaticPose - 静态位姿分析工具

**功能描述**: 专项分析机器人在**静止状态**下的定位漂移现象。通过统计 X、Y、RZ 的极值与标准差，评估定位系统的绝对稳定性和抗噪能力。

* **启动命令**:
```bash
cd StaticPose
py main.py

```


* **指标解读**: 标准差（Standard Deviation）越接近 0，说明静态无波动，定位系统越优秀。

---

## ❓ 常见问题与排错 (FAQ)

**Q1: 命令行提示 `'pip' 或 'py' 不是内部或外部命令**`

* **A**: 安装 Python 时忘记勾选 `Add to PATH`。请重新运行安装包，选择 `Modify` -> `Advanced Options`，勾选 `Add Python to environment variables`。

**Q2: 导入 Open3D 时报错或系统提示缺少 DLL**

* **A**: 某些精简版 Windows 可能缺少 C++ 运行库。请下载并安装 [微软 Visual C++ 可再发行组件包](https://www.google.com/search?q=https://aka.ms/vs/17/release/vc_redist.x64.exe)。

**Q3: 处理海量点云时程序闪退（内存溢出）**

* **A**: `Open3D` 非常吃内存。请在代码中尝试增加点云降采样（Voxel Downsampling）逻辑，或关闭后台高内存占用软件。

---

*内部工具，未经授权请勿外传。*
*最后更新：2026年2月*
