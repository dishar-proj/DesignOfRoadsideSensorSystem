import os
import json
import glob
import re
import numpy as np
import shutil  
import cv2  

#constants=
DELTA_SECONDS   = 0.05   
LOOKBACK_FRAMES = 10     
SPEED_LIMIT     = 4 # 35 miles/h  

#helper functions
def sort_nicely(l):
    """ Sorts lists of strings with numbers the way a human would """
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(l, key=alphanum_key)

def read_ply(file_path):
    with open(file_path, 'rb') as f:
        header      = []
        is_binary   = False
        vertex_count = 0
        while True:
            line = f.readline().strip()
            header.append(line)
            if line.startswith(b'format binary'):
                is_binary = True
            elif line.startswith(b'element vertex'):
                vertex_count = int(line.split()[2])
            elif line == b'end_header':
                break
        if vertex_count == 0:
            return np.empty((0, 4))
        if is_binary:
            raw  = f.read()
            cols = len(raw) // (4 * vertex_count)
            data = np.frombuffer(raw, dtype=np.float32).reshape(-1, cols)
            return data[:, :4]
        else:
            rows = []
            for _ in range(vertex_count):
                line = f.readline().decode('ascii').strip().split()
                rows.append([float(v) for v in line[:4]])
            return np.array(rows)

def get_vehicle_center(ply_file_path):
    pts = read_ply(ply_file_path)
    if len(pts) < 5: 
        return None, False
    bmin = np.min(pts[:, :2], axis=0)
    bmax = np.max(pts[:, :2], axis=0)
    max_length = np.max(bmax - bmin)
    is_side_occluded = bool(max_length < 2.5)
    return np.mean(pts[:, :2], axis=0), is_side_occluded

#main loop
if __name__ == "__main__":
    json_output = {
        "summary": {},
        "vehicles": [],
        "pedestrian_frames": []
    }

    lidar_folder  = "out_Intersection_North_lidar"
    camera_folder = "out_Intersection_North_rgb" 
    
    # --- FOLDER SETUP AND CLEANUP ---
    speeding_output_dir = os.path.join("videos", "speeding_events")
    live_output_dir = os.path.join("videos", "live")

    ####
    speeding_output_dir = "/home/capstone/Documents/CarlaPSim/CapstoneUI/my-Capstone-UI/public/videos/speeding_events"
    live_output_dir = "/home/capstone/Documents/CarlaPSim/CapstoneUI/my-Capstone-UI/public/videos/live"
    ####

    # 1. Empty the speeding_events folder on startup
    if os.path.exists(speeding_output_dir):
        print(f"Cleaning up old directory: {speeding_output_dir}")
        shutil.rmtree(speeding_output_dir)
    os.makedirs(speeding_output_dir, exist_ok=True)
    
    # 2. Make sure the live folder exists
    os.makedirs(live_output_dir, exist_ok=True)

    ply_files = glob.glob(os.path.join(lidar_folder, "*.ply"))

    actual_speeds = {}
    vehicle_names = {}
    
    if os.path.exists("actual_speeds.txt"):
        with open("actual_speeds.txt") as f:
            for line in f:
                parts = line.strip().split(',')
                if len(parts) == 4:
                    frame, vid, v_name, spd = int(parts[0]), int(parts[1]), parts[2], float(parts[3])
                    if vid not in actual_speeds:
                        actual_speeds[vid] = {}
                    actual_speeds[vid][frame] = spd
                    vehicle_names[vid] = v_name 

    if not ply_files:
        print(f"Error: Could not find any .ply files in '{lidar_folder}'.")
        exit()

    vehicle_files = {} 
    for fp in ply_files:
        basename = os.path.basename(fp)
        match = re.match(r"(\d+)_v(\d+)\.ply", basename)
        if match:
            frame_num = int(match.group(1))
            vid = int(match.group(2))
            if vid not in vehicle_files:
                vehicle_files[vid] = []
            vehicle_files[vid].append((frame_num, fp))
            
    total_pedestrians = 0
    total_vehicles = 0
    pedestrians_in_frame = {}
    vehicles_in_frame = {}
    
    for vid, files in vehicle_files.items():
        v_name = vehicle_names.get(vid, "").lower()
        is_ped = False
        
        if 'walker' in v_name:
            is_ped = True
        elif 'vehicle' in v_name:
            is_ped = False
        else:
            max_seen_length = 0.0
            for _, fp in files:
                pts = read_ply(fp)
                if len(pts) >= 5:
                    bmin = np.min(pts[:, :2], axis=0)
                    bmax = np.max(pts[:, :2], axis=0)
                    length = np.max(bmax - bmin)
                    if length > max_seen_length:
                        max_seen_length = length
            
            if max_seen_length < 3.0:
                is_ped = True
            else:
                is_ped = False

        if is_ped:
            total_pedestrians += 1
            if not v_name: vehicle_names[vid] = "walker.unknown"
            for frame_num, _ in files:
                pedestrians_in_frame[frame_num] = pedestrians_in_frame.get(frame_num, 0) + 1
        else:
            total_vehicles += 1
            if not v_name: vehicle_names[vid] = "vehicle.unknown"
            for frame_num, _ in files:
                vehicles_in_frame[frame_num] = vehicles_in_frame.get(frame_num, 0) + 1

    print("="*60)
    print(f"LIDAR SCAN COMPLETE: {len(ply_files)} total frames analyzed.")
    print(f"--> DETECTED OBJECTS: {total_vehicles} Vehicles and {total_pedestrians} Pedestrians")
    print("="*60)
            
    for vid, files in vehicle_files.items():
        files.sort(key=lambda x: x[0]) 
        current_vehicle_name = vehicle_names.get(vid, f"Unknown_Object_{vid}")
        is_human = 'walker' in current_vehicle_name.lower()
        obj_type_label = "PEDESTRIAN" if is_human else "VEHICLE"
        
        print(f"\n" + "-"*60)
        print(f"TRACKING {obj_type_label}: {current_vehicle_name} (ID: {vid})")
        print(f"Total Frames in View: {len(files)}")
        print("-"*60)
        
        speed_history_buffer = []
        centers = {}
        occluded_states = {}
        continuous_tracked_frames = 0
        speeding_frames_to_copy = set()
        
        for frame_num, fp in files:
            c, is_occ = get_vehicle_center(fp)
            centers[frame_num] = c
            occluded_states[frame_num] = is_occ

        for i in range(len(files) - 1):
            f1_frame, f1_path = files[i]
            f2_frame, f2_path = files[i+1]
            f1_name = os.path.basename(f1_path)
            f2_name = os.path.basename(f2_path)
            
            actual_speed_mps = actual_speeds.get(vid, {}).get(f2_frame, None)
            valid_past_frame = None
            valid_past_c = None
            
            lookback_start = max(0, i + 1 - LOOKBACK_FRAMES)
            for j in range(lookback_start, i + 1):
                past_frame = files[j][0]
                if centers[past_frame] is not None:
                    valid_past_frame = past_frame
                    valid_past_c = centers[past_frame]
                    break

            sensor_speed_mps = None
            c_curr = centers[f2_frame]

            if is_human:
                if c_curr is not None and valid_past_c is not None and valid_past_frame < f2_frame:
                    continuous_tracked_frames += 1
                else:
                    continuous_tracked_frames = 0
                    
                tracked_time_seconds = continuous_tracked_frames * DELTA_SECONDS
                print(f"Frames: {f1_name} -> {f2_name} | TRACKING PEDESTRIAN")
                print(f"  > Time in View: {tracked_time_seconds:.2f} seconds")
                print("-" * 60)
            else:
                if c_curr is not None and valid_past_c is not None and valid_past_frame < f2_frame:
                    real_delta_time = (f2_frame - valid_past_frame) * DELTA_SECONDS
                    dist = np.linalg.norm(c_curr - valid_past_c)
                    inst_speed = dist / real_delta_time
                    
                    if 0.0 <= inst_speed <= 55.0:
                        speed_history_buffer.append(inst_speed)
                        if len(speed_history_buffer) > 10:          
                            speed_history_buffer.pop(0)
                        sensor_speed_mps = float(np.mean(speed_history_buffer))
                        continuous_tracked_frames += 1
                else:
                    speed_history_buffer.clear()
                    continuous_tracked_frames = 0

                if sensor_speed_mps is not None and actual_speed_mps is not None:
                    tracked_time_seconds = continuous_tracked_frames * DELTA_SECONDS
                    error_margin = abs((sensor_speed_mps - actual_speed_mps) / actual_speed_mps) * 100 if actual_speed_mps > 0.1 else 0.0
                    
                    is_speeding = bool(sensor_speed_mps > SPEED_LIMIT)
                    if is_speeding:
                        speeding_frames_to_copy.add(f1_frame)
                        speeding_frames_to_copy.add(f2_frame)

                    vehicle_data = {
                        "frame_start": f1_name,
                        "frame_end": f2_name,
                        "vehicle_id": vid,
                        "name": current_vehicle_name,
                        "time_in_view_sec": round(tracked_time_seconds, 2),
                        "actual_speed_mps": round(actual_speed_mps, 2),
                        "sensor_speed_mps": round(sensor_speed_mps, 2),
                        "error_margin_percent": round(error_margin, 2),
                        "is_speeding": is_speeding, 
                        "occluded": bool(occluded_states[f2_frame])
                    }
                    json_output["vehicles"].append(vehicle_data)

                    print(f"Frames: {f1_name} -> {f2_name}")
                    if occluded_states[f2_frame]:
                        print(f"  > [ALERT] Side of car occluded (Rear/Front profile only)")
                        
                    concurrent_pedestrians = pedestrians_in_frame.get(f2_frame, 0)
                    if concurrent_pedestrians > 0:
                        print(f"  > [WARNING] {concurrent_pedestrians} Pedestrian(s) in view alongside this vehicle!")

                    print(f"  > Time in View: {tracked_time_seconds:.2f} seconds")
                    print(f"  > Actual Speed: {actual_speed_mps:.2f} m/s")
                    print(f"  > Sensor Speed: {sensor_speed_mps:.2f} m/s")
                    print(f"  > Error Margin: {error_margin:.2f} %")
                    
                    if is_speeding: 
                        print("  > IS_Speeding: YES (Above Speed Limit)")
                    else:                    
                        print("  > IS_Speeding: NO (Within Speed Limit)")
                    print("-" * 60)
                elif actual_speed_mps is None:
                    print(f"Frames: {f1_name} -> {f2_name} | MISSING ACTUAL SPEED DATA")
                    print("-" * 60)
                else:
                    print(f"Frames: {f1_name} -> {f2_name} | FAILED TO DETECT VEHICLE")
                    print("-" * 60)
                    
        total_time_in_view = len(files) * DELTA_SECONDS
        print(f"-> Finished logging {current_vehicle_name}.")
        print(f"-> Total Time in Sensor View: {total_time_in_view:.2f} seconds\n")

        #video export
        if speeding_frames_to_copy:
            safe_name = current_vehicle_name.replace(" ", "_").replace("/", "_")
            event_folder_name = f"{safe_name}_ID{vid}"
            event_folder_path = os.path.join(speeding_output_dir, event_folder_name)
            
            os.makedirs(event_folder_path, exist_ok=True)
            
            sorted_frames = sorted(list(speeding_frames_to_copy))
            copied_images = []
            copied_count = 0
            
            #1) copy images
            for frame_num in sorted_frames:
                img_filename = f"{frame_num:06d}.png" 
                img_file_path = os.path.join(camera_folder, img_filename)
                
                if os.path.exists(img_file_path):
                    shutil.copy(img_file_path, event_folder_path)
                    copied_images.append(img_filename)
                    copied_count += 1
                else:
                    fallback_path = os.path.join(camera_folder, f"{frame_num}.png")
                    if os.path.exists(fallback_path):
                        shutil.copy(fallback_path, event_folder_path)
                        copied_images.append(f"{frame_num}.png")
                        copied_count += 1
                    else:
                        print(f"  [DEBUG] Could not find image! Looked for: '{img_file_path}' AND '{fallback_path}'")
                        
            print(f"-> [!] Exported {copied_count} camera frames to '{event_folder_path}'")

            #2)Stitch the copied images into an mp4 video using OpenCV
            if copied_images:
                video_name = f"{event_folder_name}.webm"
                video_path = os.path.join(event_folder_path, video_name)
                
                first_img_path = os.path.join(event_folder_path, copied_images[0])
                first_frame = cv2.imread(first_img_path)
                
                if first_frame is not None:
                    height, width, layers = first_frame.shape
                    fps = int(1.0 / DELTA_SECONDS)  # Usually 20 fps if DELTA_SECONDS is 0.05
                    
                    fourcc = cv2.VideoWriter_fourcc(*'VP80')
                    video_writer = cv2.VideoWriter(video_path, fourcc, fps, (width, height))
                    
                    for img_name in copied_images:
                        img_path = os.path.join(event_folder_path, img_name)
                        frame_to_write = cv2.imread(img_path)
                        if frame_to_write is not None:
                            video_writer.write(frame_to_write)
                            
                    video_writer.release()
                    print(f"-> [!] Successfully created video: '{video_path}'")
                    
                    #3)Clean up the images
                    deleted_count = 0
                    for img_name in copied_images:
                        img_path_to_delete = os.path.join(event_folder_path, img_name)
                        try:
                            os.remove(img_path_to_delete)
                            deleted_count += 1
                        except OSError as e:
                            print(f"  [X] Could not delete '{img_path_to_delete}': {e}")
                    print(f"-> [!] Cleaned up {deleted_count} temporary image frames.")

                else:
                    print(f"-> [X] Error: Could not read the first frame ({first_img_path}) to initialize video writer.")

    #Live Video generation
    print("="*60)
    print("GENERATING FULL LIVE SIMULATION VIDEO...")
    print("="*60)
    
    all_images = [img for img in os.listdir(camera_folder) if img.endswith(".png")]
    all_images = sort_nicely(all_images)
    
    if all_images:
        live_video_path = os.path.join(live_output_dir, "live_simulation.webm")
        first_frame_path = os.path.join(camera_folder, all_images[0])
        first_frame_img = cv2.imread(first_frame_path)
        
        if first_frame_img is not None:
            height, width, layers = first_frame_img.shape
            fps = int(1.0 / DELTA_SECONDS)
            
            fourcc = cv2.VideoWriter_fourcc(*'VP80')
            live_video_writer = cv2.VideoWriter(live_video_path, fourcc, fps, (width, height))
            
            print(f"-> Stitching {len(all_images)} frames into {live_video_path}")
            for img_name in all_images:
                img_path = os.path.join(camera_folder, img_name)
                frame_to_write = cv2.imread(img_path)
                if frame_to_write is not None:
                    live_video_writer.write(frame_to_write)
            
            live_video_writer.release()
            print(f"-> [!] Successfully created LIVE video: '{live_video_path}'")
        else:
            print("-> [X] Error: Could not read the first frame to initialize the LIVE video writer.")
    else:
        print(f"-> [X] Error: No PNG images found in '{camera_folder}' to create the live video.")

    #JSON for UI visibility
    json_output["summary"] = {
        "total_vehicles": total_vehicles,
        "total_pedestrians": total_pedestrians
    }

    all_frames = sorted(list(set(list(pedestrians_in_frame.keys()) + list(vehicles_in_frame.keys()))))
    print("="*60)
    print("                 PEDESTRIAN PRESENCE TAB                 ")
    print("="*60)
    print(f"{'FRAME':<10} | {'PEDESTRIANS IN VIEW':<20} | {'VEHICLES IN VIEW':<20}")
    print("-" * 60)
    for frame in all_frames:
        p_count = pedestrians_in_frame.get(frame, 0)
        v_count = vehicles_in_frame.get(frame, 0)
        print(f"{frame:<10} | {p_count:<20} | {v_count:<20}")
        
        json_output["pedestrian_frames"].append({
            "frame": frame,
            "pedestrians_in_view": p_count,
            "vehicles_in_view": v_count
        })
    print("="*60)

    react_src_path = "/home/capstone/Documents/CarlaPSim/CapstoneUI/my-Capstone-UI/src/carla_results.json"
    try:
        with open(react_src_path, "w") as json_file:
            json.dump(json_output, json_file, indent=4)
        print(f"Successfully exported data to {react_src_path}")
    except FileNotFoundError:
        with open("carla_results.json", "w") as json_file:
            json.dump(json_output, json_file, indent=4)
