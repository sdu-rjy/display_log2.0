import os
import glob
import re
import numpy as np

class EvaluatorData:
    def __init__(self, log_dir):
        self.log_dir = log_dir
        self.trajectories = {}  
        self.file_names = []    
        self.max_len = 0        

    def load_data(self):
        self.trajectories.clear()
        self.file_names.clear()
        self.max_len = 0

        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            return False, f"Please put log files in: {self.log_dir}"

        files = sorted(glob.glob(os.path.join(self.log_dir, "*.txt")) + 
                       glob.glob(os.path.join(self.log_dir, "*.log")))
        
        if not files:
            return False, "No log files found in the directory."

        time_pattern = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})")
        state_pattern = re.compile(r"Location_state\s*=\s*(?P<state>[\w:]+).*?type\s*=\s*(?P<type>\d+)")
        coord_pattern = re.compile(r"\(([-+\d\s.,]+)\)")

        for filepath in files:
            fname = os.path.basename(filepath)
            
            x_list, y_list, t_list = [], [], []
            ts_list, state_list, type_list = [], [], []
            
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    
                    coord_match = coord_pattern.search(line)
                    if coord_match:
                        nums_str = coord_match.group(1).replace(',', ' ')
                        parts = [float(p) for p in nums_str.split() if p.strip()]
                        
                        if len(parts) >= 3:
                            x_list.append(parts[0])     
                            y_list.append(parts[1])     
                            t_list.append(parts[-1])    
                            
                            time_match = time_pattern.search(line)
                            ts_list.append(time_match.group(1) if time_match else "--")
                            
                            state_match = state_pattern.search(line)
                            state_list.append(state_match.group('state') if state_match else "--")
                            type_list.append(state_match.group('type') if state_match else "--")
                            
            if len(x_list) > 0:
                self.trajectories[fname] = {
                    'x': np.array(x_list), 'y': np.array(y_list), 't': np.array(t_list),
                    'timestamps': ts_list, 'states': state_list, 'types': type_list
                }
                self.file_names.append(fname)
                self.max_len = max(self.max_len, len(x_list))

        if not self.file_names:
            return False, "Found files, but no valid coordinate data extracted."

        return True, f"Loaded {len(self.file_names)} trajectories successfully."

    def compute_evaluation_report(self, ref_name, est_name):
        """ 综合计算 APE (绝对位姿误差) 和 RPE (相对位姿误差) """
        if ref_name not in self.trajectories or est_name not in self.trajectories:
            return "Invalid trajectory selection."

        ref_data = self.trajectories[ref_name]
        est_data = self.trajectories[est_name]
        
        min_len = min(len(ref_data['x']), len(est_data['x']))
        if min_len < 2:
            return "Not enough matched points for evaluation."

        ref_pts = np.vstack((ref_data['x'][:min_len], ref_data['y'][:min_len])).T
        est_pts = np.vstack((est_data['x'][:min_len], est_data['y'][:min_len])).T
        
        # --- 1. APE (Absolute Pose Error) 计算 ---
        ape_errors = np.linalg.norm(ref_pts - est_pts, axis=1)
        ape_rmse = np.sqrt(np.mean(ape_errors**2))
        
        out_text = f"=== APE (Absolute Pose Error) ===\n"
        out_text += f"Evaluate global consistency.\n"
        out_text += f"  RMSE : {ape_rmse:.6f} m\n"
        out_text += f"  Mean : {np.mean(ape_errors):.6f} m\n"
        out_text += f"  Max  : {np.max(ape_errors):.6f} m\n"
        out_text += f"  Min  : {np.min(ape_errors):.6f} m\n"
        out_text += f"  Std  : {np.std(ape_errors):.6f} m\n"
        out_text += "-"*40 + "\n"

        # --- 2. RPE (Relative Pose Error) 计算 ---
        ref_t = ref_data['t'][:min_len]
        est_t = est_data['t'][:min_len]
        
        rpe_errors = []
        for i in range(min_len - 1):
            # 将第 i 到 i+1 步的世界坐标位移，转换到第 i 步的局部坐标系下
            dx_ref, dy_ref = ref_pts[i+1, 0] - ref_pts[i, 0], ref_pts[i+1, 1] - ref_pts[i, 1]
            c_ref, s_ref = np.cos(ref_t[i]), np.sin(ref_t[i])
            rel_x_ref = c_ref * dx_ref + s_ref * dy_ref
            rel_y_ref = -s_ref * dx_ref + c_ref * dy_ref

            dx_est, dy_est = est_pts[i+1, 0] - est_pts[i, 0], est_pts[i+1, 1] - est_pts[i, 1]
            c_est, s_est = np.cos(est_t[i]), np.sin(est_t[i])
            rel_x_est = c_est * dx_est + s_est * dy_est
            rel_y_est = -s_est * dx_est + c_est * dy_est

            # 计算两个相对位移向量之间的差异
            err = np.hypot(rel_x_ref - rel_x_est, rel_y_ref - rel_y_est)
            rpe_errors.append(err)

        rpe_errors = np.array(rpe_errors)
        rpe_rmse = np.sqrt(np.mean(rpe_errors**2))

        out_text += f"=== RPE (Relative Pose Error) ===\n"
        out_text += f"Evaluate local accuracy (Step = 1).\n"
        out_text += f"  RMSE : {rpe_rmse:.6f} m\n"
        out_text += f"  Mean : {np.mean(rpe_errors):.6f} m\n"
        out_text += f"  Max  : {np.max(rpe_errors):.6f} m\n"
        out_text += f"  Min  : {np.min(rpe_errors):.6f} m\n"
        out_text += f"  Std  : {np.std(rpe_errors):.6f} m\n"

        return out_text