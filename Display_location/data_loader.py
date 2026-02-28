import re
import os
import numpy as np

class DataLoader:
    def __init__(self):
        self.trajectory_data = [] 
        self.all_logs_data = {} 
        self.all_logs_np = {}
        self.landmarks = {}
        self.all_landmarks = {}
        self.maps_data = {} 

    def _parse_single_file(self, file_path, landmark_configs=None):
        data_list = []
        landmarks_dict = {cfg['keyword']: [] for cfg in landmark_configs} if landmark_configs else {}
        
        # [修改] 定义更详细的正则
        # 1. 提取时间
        time_pattern = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})")
        # 2. 提取状态和类型 (例如: Location_state = ... type = 20)
        state_pattern = re.compile(r"Location_state\s*=\s*(?P<state>[\w:]+).*?type\s*=\s*(?P<type>\d+)")
        # 3. 提取括号内的坐标数据
        coords_pattern = re.compile(r"\((.*?)\)")
        
        if not os.path.exists(file_path):
            return [], {}, None, None

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            for line in lines:
                # [修改] 判断条件改为包含 Location_state 即可，这样能捕获所有状态
                if "Location_state =" in line:
                    t_match = time_pattern.search(line)
                    s_match = state_pattern.search(line)
                    c_match = coords_pattern.search(line)

                    # 只有当 时间、状态、坐标 都匹配成功时才添加
                    if t_match and s_match and c_match:
                        time_str = t_match.group(1)
                        loc_state = s_match.group("state") # [新增] 获取状态字符串
                        loc_type = s_match.group("type")   # [新增] 获取类型数字
                        
                        floats = list(map(float, c_match.group(1).strip().split()))
                        
                        if len(floats) >= 6:
                            data_list.append({
                                'timestamp': time_str,
                                'loc_state': loc_state, # [新增] 存入字典
                                'loc_type': loc_type,   # [新增] 存入字典
                                'x': floats[0], 'y': floats[1], 'z': floats[2],
                                'p': floats[3], 'param_y': floats[4], 't': floats[5],
                                'raw_floats': floats
                            })

                if landmark_configs:
                    for cfg in landmark_configs:
                        kw = cfg['keyword']
                        if kw in line:
                            try:
                                nums = [float(s) for s in re.findall(r"[-+]?\d*\.\d+|\d+", line)]
                                idx_x, idx_y = cfg['indices']
                                if len(nums) > max(idx_x, idx_y):
                                    landmarks_dict[kw].append([nums[idx_x], nums[idx_y]])
                            except:
                                pass
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")

        if data_list:
            x_arr = np.array([d['x'] for d in data_list])
            y_arr = np.array([d['y'] for d in data_list])
            return data_list, landmarks_dict, x_arr, y_arr
        else:
            return [], {}, None, None

    def load_all_logs_in_folder(self, folder_path, landmark_configs):
        self.all_logs_data = {}
        self.all_landmarks = {}
        self.all_logs_np = {} 
        
        if not os.path.exists(folder_path):
            return 0

        count = 0
        for f in sorted(os.listdir(folder_path)):
            if f.endswith('.txt') or f.endswith('.log'):
                full_path = os.path.join(folder_path, f)
                data, lms, x_arr, y_arr = self._parse_single_file(full_path, landmark_configs)
                
                if data:
                    self.all_logs_data[f] = data
                    self.all_landmarks[f] = lms
                    self.all_logs_np[f] = {'x': x_arr, 'y': y_arr}
                    count += 1
        return count

    def select_log(self, log_name):
        if log_name in self.all_logs_data:
            self.trajectory_data = self.all_logs_data[log_name]
            self.landmarks = self.all_landmarks[log_name]
            return len(self.trajectory_data)
        return 0

    def load_pcd_file(self, file_path):
        points = []
        header_passed = False
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if header_passed:
                        try:
                            vals = list(map(float, line.strip().split()))
                            if len(vals) >= 2:
                                points.append(vals[:2])
                        except:
                            continue
                    if line.startswith('DATA ascii'):
                        header_passed = True
            return np.array(points) if points else None
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return None

    def load_all_maps(self, folder_path):
        self.maps_data = {}
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            return
        for f in os.listdir(folder_path):
            if f.endswith('.pcd'):
                full_path = os.path.join(folder_path, f)
                pts = self.load_pcd_file(full_path)
                if pts is not None:
                    self.maps_data[f] = pts
        return self.maps_data