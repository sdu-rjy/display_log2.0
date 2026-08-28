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
        
        # 统一兼容新旧日志格式：
        # 新: 2026-08-27 16:40:02.223 ... Location_state = ... score = ... type = ... (...)
        # 旧: 2024-01-15 10:30:45,123 ... Location_state = ... score = ... type = ... (...)
        number_pattern = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
        time_pattern = re.compile(r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[.,]\d{3})")
        location_pattern = re.compile(
            rf"Location_state\s*=\s*(?P<state>[\w:]+)"
            rf".*?score\s*=\s*(?P<score>{number_pattern})"
            rf".*?type\s*=\s*(?P<type>\d+)"
            rf"\s*\(\s*(?P<coords>[^)]*)\)"
        )
        
        if not os.path.exists(file_path):
            return [], {}, None, None

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            for line in lines:
                if "Location_state" in line:
                    t_match = time_pattern.search(line)
                    loc_match = location_pattern.search(line)

                    # 时间、状态/得分/type、位姿必须来自同一条 Location_state 日志
                    if t_match and loc_match:
                        time_str = t_match.group(1)
                        loc_state = loc_match.group("state")
                        loc_score = float(loc_match.group("score"))
                        loc_type = loc_match.group("type")
                        floats = [float(v) for v in re.findall(number_pattern, loc_match.group("coords"))]

                        if len(floats) >= 6:
                            data_list.append({
                                'timestamp': time_str,
                                'loc_state': loc_state,
                                'loc_score': loc_score,
                                'loc_type': loc_type,
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
            if os.path.splitext(f)[1].lower() in ('.txt', '.log'):
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