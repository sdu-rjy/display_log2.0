import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# --- 参数设置 ---
L_max = 2.0   # 最大推算距离 (米)
T_max = 90.0  # 最大推算角度 (度)

# --- 生成 2D 独立测试数据 (横坐标延长 20% 以展示截断效果) ---
s_1d = np.linspace(0, L_max * 1.2, 100)
theta_1d = np.linspace(0, T_max * 1.2, 100)

# 单一变量的得分计算
c_dist_only = 100.0 * np.maximum(0, 1.0 - (s_1d / L_max)**2)
c_angle_only = 100.0 * np.maximum(0, 1.0 - (theta_1d / T_max)**2)

# --- 生成 3D 耦合测试数据 ---
s_vals = np.linspace(0, L_max, 100)
theta_vals = np.linspace(0, T_max, 100)
S, Theta = np.meshgrid(s_vals, theta_vals)
C_qr = 100.0 * np.maximum(0, 1.0 - (S / L_max)**2) * np.maximum(0, 1.0 - (Theta / T_max)**2)

# ================= 绘图开始 =================
# 创建一个 1行3列 的宽幅画布
fig = plt.figure(figsize=(18, 5.5))
fig.suptitle('QR Code Odometry Confidence Decay Model', fontsize=18, fontweight='bold', y=1.02)

# --- 子图 1: 纯距离衰减 (2D) ---
ax1 = fig.add_subplot(1, 3, 1)
ax1.plot(s_1d, c_dist_only, color='#1f77b4', linewidth=3)
ax1.fill_between(s_1d, c_dist_only, color='#1f77b4', alpha=0.2)
ax1.axvline(x=L_max, color='red', linestyle='--', alpha=0.7, label=f'Limit (L={L_max}m)')
ax1.set_title('Distance Decay (Angle = 0°)', fontsize=14)
ax1.set_xlabel('Accumulated Distance $\Delta s$ (m)', fontsize=12)
ax1.set_ylabel('Confidence Score', fontsize=12)
ax1.set_ylim(-5, 105)
ax1.grid(True, linestyle=':', alpha=0.7)
ax1.legend()

# --- 子图 2: 纯角度衰减 (2D) ---
ax2 = fig.add_subplot(1, 3, 2)
ax2.plot(theta_1d, c_angle_only, color='#ff7f0e', linewidth=3)
ax2.fill_between(theta_1d, c_angle_only, color='#ff7f0e', alpha=0.2)
ax2.axvline(x=T_max, color='red', linestyle='--', alpha=0.7, label=f'Limit (T={T_max}°)')
ax2.set_title('Angle Decay (Distance = 0m)', fontsize=14)
ax2.set_xlabel('Accumulated Angle $\Delta \\theta$ (deg)', fontsize=12)
ax2.set_ylim(-5, 105)
ax2.grid(True, linestyle=':', alpha=0.7)
ax2.legend()

# --- 子图 3: 双重耦合衰减 (优化版 3D) ---
ax3 = fig.add_subplot(1, 3, 3, projection='3d')
# 绘制 3D 曲面，使用 viridis 色系，增加抗锯齿
surf = ax3.plot_surface(S, Theta, C_qr, cmap='viridis', edgecolor='none', alpha=0.8, antialiased=True)
# 核心优化：在底部 z=-20 的位置投射 2D 等高线，帮助看清耦合下降的趋势
ax3.contourf(S, Theta, C_qr, zdir='z', offset=-20, cmap='viridis', alpha=0.5)

ax3.set_title('Coupled Decay Surface', fontsize=14)
ax3.set_xlabel('Dist $\Delta s$ (m)', fontsize=10)
ax3.set_ylabel('Angle $\Delta \\theta$ (deg)', fontsize=10)
ax3.set_zlabel('Score', fontsize=10)
ax3.set_zlim(-20, 100) # 底部留出空间给等高线

# 调整 3D 视角: 抬高俯视角度，更容易看清等高线和曲面形状
ax3.view_init(elev=25, azim=230)

# 调整整体布局
plt.tight_layout()
plt.show()