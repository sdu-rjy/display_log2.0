# Display_Log 2.0 - 机器人定位日志分析工具集

## 项目简介

本项目是一套用于机器人定位系统日志分析和可视化的工具集，基于 Python 开发，在 Windows 环境下运行。项目包含多个功能模块，用于分析、可视化和验证机器人定位系统的性能。

## 目录结构

```
f:\display_log2.0\
├── Display_location\          # 定位轨迹可视化工具
├── FrameByFrameReplay\        # 点云逐帧回放工具
├── LinearOscillation\         # 轨迹拟合与线性度分析工具
├── ShowLidarRangingError\     # 激光雷达测距误差分析工具
├── StaticPose\                # 静态位姿分析工具
└── readme.md                  # 本文档
```

## 环境配置规范

### 1. 操作系统要求

- **操作系统**: Windows 10/11 (64位)
- **Python 版本**: Python 3.7 或更高版本
- **CPU**: 建议 4 核心以上
- **内存**: 建议 8GB 以上
- **显卡**: 支持 OpenGL 的独立显卡（用于点云可视化）

### 2. Python 环境安装

#### 2.1 安装 Python

1. 下载 Python 安装包: https://www.python.org/downloads/
2. 安装时**务必勾选** "Add Python to PATH"
3. 验证安装:
   ```bash
   python --version
   pip --version
   ```

#### 2.2 创建虚拟环境（推荐）

```bash
# 进入项目目录
cd f:\display_log2.0

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
venv\Scripts\activate

# 看到命令行前缀有 (venv) 即表示激活成功
```

### 3. 依赖库安装

在激活虚拟环境后，执行以下命令安装所需的依赖库：

#### 3.1 核心依赖

```bash
# GUI 框架
pip install PyQt5

# 点云处理库
pip install open3d

# 数值计算库
pip install numpy

# 绘图库
pip install matplotlib
```

如果存在冲突的情况下，请使用这个安装规格
```bash
python --version
pip --version
pip install numpy matplotlib
py -m pip install numpy matplotlib
py -m pip install PyQt5
py -m pip install pyqtgraph
```


#### 3.2 完整安装命令

一次性安装所有依赖：

```bash
pip install PyQt5 open3d numpy matplotlib
```

#### 3.3 验证安装

```bash
python -c "import PyQt5; import open3d; import numpy; import matplotlib; print('所有依赖安装成功！')"
```

### 4. 目录结构配置

各模块需要以下目录结构（程序会自动创建，但也可以手动预先创建）：

#### Display_location 模块：
```
Display_location/
├── logs/          # 日志文件目录
├── map/           # 地图文件目录（.pcd格式）
└── out/           # 输出文件目录
```

#### FrameByFrameReplay 模块：
```
FrameByFrameReplay/
├── scans_directory/  # 点云帧文件目录（.pcd格式）
└── map/              # 全局地图文件（global_map.pcd）
```

#### ShowLidarRangingError 模块：
```
ShowLidarRangingError/
├── logs/          # 点云文件目录
├── out/           # 输出目录（保存分析结果和图表）
```

#### LinearOscillation 和 StaticPose 模块：
- 不需要特定目录结构，通过界面选择日志文件目录

### 5. 环境变量配置（可选）

如果遇到模块导入错误，可以设置 PYTHONPATH：

```bash
set PYTHONPATH=f:\display_log2.0\Display_location;f:\display_log2.0\FrameByFrameReplay;f:\display_log2.0\LinearOscillation;f:\display_log2.0\ShowLidarRangingError;f:\display_log2.0\StaticPose
```

## 各模块使用规范

### 1. Display_location - 定位轨迹可视化工具

#### 功能描述
- 可视化机器人定位轨迹
- 支持多轨迹对比显示
- 点击轨迹点快速跳转
- 轨迹时间范围筛选
- 显示 landmark（QR码、反射板等）

#### 使用步骤

1. **准备数据**：
   - 将日志文件（`.log` 或 `.txt`）放入 `Display_location/logs/` 目录
   - 将地图文件（`.pcd` 格式）放入 `Display_location/map/` 目录
   
2. **日志格式要求**：
   ```
   时间戳: 2024-01-15 10:30:45,123
   Location_state = RealTimeLocation:10 type = 20 (x y z roll pitch yaw)
   ```

3. **运行程序**：
   ```bash
   cd Display_location
   python main.py
   ```

4. **操作说明**：
   - 左侧为控制面板，右侧为轨迹显示区
   - **点击轨迹**：点击任意轨迹点自动跳转到对应位置
   - **上一/下一日志**：切换不同的日志文件
   - **播放控制**：使用滑块或按钮逐帧查看
   - **键盘快捷键**：
     - `←` : 上一帧
     - `→` : 下一帧
     - `↑` : 上一个日志
     - `↓` : 下一个日志
   - **时间范围筛选**：选择起始和结束时间，筛选显示的轨迹段
   - **导出帧**：点击"Export Frame"导出当前帧信息

#### 注意事项
- 日志文件必须包含 `Location_state` 字段
- 支持 landmark 显示，在代码中配置 `LANDMARK_CONFIGS`
- 导出的帧信息保存在 `out/` 目录

---

### 2. FrameByFrameReplay - 点云逐帧回放工具

#### 功能描述
- 逐帧播放点云数据
- 显示激光雷达扫描点云
- 高强度点高亮显示（红色）
- 实时显示坐标原点位置
- 支持视角一键回正

#### 使用步骤

1. **准备数据**：
   - 将连续帧的点云文件（`.pcd` 格式）放入 `FrameByFrameReplay/scans_directory/` 目录
   - 将全局地图文件命名为 `global_map.pcd` 放入 `FrameByFrameReplay/map/` 目录

2. **点云文件命名**：
   - 建议按时间戳命名，如：`312000819_20.pcd`
   - 文件会自动按名称排序播放

3. **运行程序**：
   ```bash
   cd FrameByFrameReplay
   python pcd_viewer.py
   ```

4. **操作说明**：
   - **右箭头 (→)**: 下一帧
   - **左箭头 (←)**: 上一帧
   - **R 键**: 视角回正（XY平面俯视）
   - **鼠标操作**: 支持旋转、缩放、平移视图
   - **Q 键**: 退出程序

5. **显示说明**：
   - 蓝色点：普通激光雷达点云
   - 红色点：高强度点（intensity > 250）
   - 蓝色箭头：机器人朝向（显示在最高层）
   - 灰色背景：全局地图

#### 注意事项
- 确保所有点云文件的点数一致（坐标对应）
- 点云文件应包含 `.pcd` 格式的 VIEWPOINT 字段
- 推荐分辨率：1280x720 或以上
- 内存不足时考虑降低点云分辨率

---

### 3. LinearOscillation - 轨迹拟合与线性度分析工具

#### 功能描述
- 分析机器人直线运动的线性度
- PCA算法拟合最佳直线
- 计算位置误差（点到直线垂直距离）
- 计算朝向误差（车体朝向与拟合直线的夹角）
- 可视化轨迹与拟合直线

#### 使用步骤

1. **运行程序**：
   ```bash
   cd LinearOscillation
   python main.py
   ```

2. **选择数据**：
   - 点击"选择文件夹"按钮
   - 选择包含日志文件的目录（支持递归搜索子目录）

3. **设置分析参数**：
   - **起始时间**: 选择分析的起始时间点
   - **结束时间**: 选择分析的结束时间点
   - **定位类型 (type)**: 选择要分析的定位类型（如 20, 50, 70 等）

4. **执行分析**：
   - 点击"拟合分析与绘图"按钮
   - 左侧显示统计分析结果
   - 右侧显示轨迹与拟合直线

5. **图表操作**：
   - 支持鼠标拖拽平移
   - 支持滚轮缩放
   - 点击工具栏保存图片

6. **分析结果解读**：
   - **位置误差**: 点到拟合直线的垂直距离
   - **朝向误差**: 车体RZ角度与拟合直线角度的差值
   - **MAE**: 平均绝对误差
   - **标准差**: 波动程度

#### 日志格式要求
```
2024-01-15 10:30:45,123 ... type = 20 (x y z roll pitch yaw)
```

#### 注意事项
- 需要至少2条数据点才能拟合直线
- 数据量越多，拟合效果越好
- 使用 PCA（主成分分析）正交距离回归
- 支持 .log、.txt 及无后缀文件

---

### 4. ShowLidarRangingError - 激光雷达测距误差分析工具

#### 功能描述
- 分析激光雷达在不同距离的测距精度
- 计算多帧点云的最大欧式距离误差
- 筛选特定距离范围的数据
- 生成误差散点图和导出数据

#### 使用步骤

1. **准备数据**：
   - 将多帧点云文件（`.pcd` 格式）放入 `ShowLidarRangingError/logs/` 目录
   - 确保点数一致，点云点序对应

2. **配置参数**（修改 `main.py`）：
   ```python
   # 配置点云文件夹路径
   PCD_FOLDER = "./logs"
   
   # 配置距离范围（单位：米）
   dist_range=(1.0, 20.0)
   
   # 配置输出文件
   output_txt="./out/lidar_error_data.txt"
   ```

3. **运行程序**：
   ```bash
   cd ShowLidarRangingError
   python main.py
   ```

4. **结果说明**：
   - 自动生成散点图（显示误差 vs 距离）
   - 数据保存到 `out/lidar_error_data.txt`
   - 图表保存到 `out/lidar_error_plot.png`

5. **分析逻辑**：
   - 以第0帧为基准计算测距长度
   - 计算所有帧两两之间的最大欧式距离作为误差
   - 筛选满足距离范围且误差 <= 0.041m 的点

#### 注意事项
- 需要至少2个PCD文件进行误差计算
- 点数不一致会导致对应错误
- 输出目录会自动创建
- 图表会自动显示，关闭后程序结束

---

### 5. StaticPose - 静态位姿分析工具

#### 功能描述
- 批量分析静态场景下的定位数据
- 统计位置和角度的漂移、波动
- 按时间和类型筛选数据
- 快速评估定位系统稳定性和重复性

#### 使用步骤

1. **运行程序**：
   ```bash
   cd StaticPose
   python main.py
   ```

2. **选择数据**：
   - 点击"选择文件夹"按钮
   - 选择包含日志文件的目录（支持递归搜索子目录）

3. **设置分析参数**：
   - **起始时间**: 选择分析的起始时间点
   - **结束时间**: 选择分析的结束时间点
   - **定位类型 (type)**: 选择要分析的定位类型

4. **执行分析**：
   - 点击"开始分析"按钮
   - 查看分析结果

5. **分析结果解读**：
   - **X/Y**: 位置坐标，观察静态场景下的位置漂移
   - **RZ**: 偏航角，观察角度稳定性
   - **平均值**: 理想情况下应接近真值
   - **波动范围**: 范围越小，稳定性越好
   - **标准差**: 波动程度，越小越优

#### 日志格式要求
```
2024-01-15 10:30:45,123 ... type = 20 (x y z roll pitch yaw)
```

#### 注意事项
- 适用于机器人静止时采集的数据
- 数据量越大，统计结果越可靠
- 支持 .log、.txt 及无后缀文件
- 标准差接近0表示定位系统非常稳定

---

## 常见问题与解决方案

### 1. 依赖安装失败

**问题**: `pip install` 速度慢或失败

**解决方案**:
```bash
# 使用国内镜像源
pip install 包名 -i https://pypi.tuna.tsinghua.edu.cn/simple

# 或升级pip
python -m pip install --upgrade pip
```

### 2. Open3D 安装问题

**问题**: Open3D 安装后导入失败

**解决方案**:
```bash
# 卸载重装
pip uninstall open3d
pip install open3d

# 或尝试特定版本
pip install open3d==0.17.0
```

### 3. 中文乱码问题

**问题**: 控制台输出中文乱码

**解决方案**:
- 本项目已通过设置 UTF-8 编码解决
- 如仍有问题，确保终端编码为 UTF-8

### 4. PyQt5 显示问题

**问题**: 窗口无法显示或界面卡死

**解决方案**:
- 确保显卡驱动已更新
- 尝试使用不同分辨率
- 降低点云数量

### 5. 内存不足

**问题**: 处理大量点云时内存溢出

**解决方案**:
- 减少同时处理的帧数
- 降低点云分辨率
- 增加系统虚拟内存

### 6. 文件路径问题

**问题**: 找不到文件或路径错误

**解决方案**:
- 使用绝对路径而非相对路径
- 确保路径中不包含中文字符（某些库可能不支持）
- 检查文件扩展名是否正确（.log, .txt, .pcd）

---

## 开发与调试

### 调试模式

在代码中添加调试信息：
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 性能优化

- 对于大量数据处理，考虑使用 NumPy 向量化操作
- Open3D 可使用 GPU 加速（需支持 CUDA）
- 减少 GUI 刷新频率

### 日志管理

- **注意**: 本项目会自动生成 `logs/` 目录并保存运行日志
- 日志可能很大，建议定期清理或添加到 `.gitignore`

---

## 版本历史

### Version 2.0
- 新增轨迹时间范围筛选功能
- 新增点击跳转功能
- 改进GUI界面布局
- 优化点云显示性能
- 添加更多统计分析指标

---

## 技术支持

如有问题或建议，请联系开发团队。

---

## 许可证

本项目仅供内部使用，未经授权不得外传。

---

**最后更新**: 2026年2月
**运行环境**: Windows 11 + Python 3.9+