import carla
import os
import queue
import random
import math  
import numpy as np  

#helper function to save the point cloud in .ply from the lidar sensor
def save_filtered_ply(points, filename):
    """Saves a filtered numpy array of points to a standard .ply file."""
    with open(filename, 'w') as f:
        f.write("ply\nformat ascii 1.0\n")
        f.write(f"element vertex {len(points)}\n")
        f.write("property float x\nproperty float y\nproperty float z\n")
        f.write("end_header\n")
        for p in points:
            f.write(f"{p[0]:.4f} {p[1]:.4f} {p[2]:.4f}\n")

#configure sensors, vehicles, pedestrians 
SENSOR_CONFIG = [
    {"name": "Intersection_North", "x": 140, "y": .52, "z": 2.65, "yaw": -6},
    {"name": "Intersection_Alternate",    "x": -2.22, "y": 95.37,  "z": 2.65, "yaw": 92.94}
]

NUM_VEHICLES = 20
NUM_PEDESTRIANS = 50

SPEC_X, SPEC_Y, SPEC_Z, SPEC_YAW = 0.0, -30.0, 20.0, 90.0
DELTA_SECONDS = 0.05 

#main loop for simulation
def main():
    client = carla.Client('127.0.0.1', 2000)
    client.set_timeout(60.0) 
    
    actor_list = []      
    sensor_hubs = []     
    original_settings = None
    speed_file = None    

    try:
        print("Loading Town03...")
        world = client.load_world('Town03') 
        bp_lib = world.get_blueprint_library()
        
        original_settings = world.get_settings()
        settings = world.get_settings()
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = DELTA_SECONDS
        world.apply_settings(settings)

        tm = client.get_trafficmanager(8005)
        tm.set_synchronous_mode(True)
        #vehicles stop for pedestrians
        tm.set_global_distance_to_leading_vehicle(1.0)

        #spawn vehicles in roundabout and near sensor packages
        print(f"Spawning {NUM_VEHICLES} vehicles along approaches to the intersection...")
        all_spawn_points = world.get_map().get_spawn_points()
        
        targeted_spawn_points = []
        for sp in all_spawn_points:
            dist_center = math.hypot(sp.location.x, sp.location.y)
            dist_cam_north = math.hypot(sp.location.x - 140, sp.location.y - 0.52)
            dist_cam_alt = math.hypot(sp.location.x - (-2.22), sp.location.y - 95.37)
            
            #accept points within the roundabout (~40m) OR near the cameras (~80m to catch cars before they pass)
            if dist_center < 40.0 or dist_cam_north < 80.0 or dist_cam_alt < 80.0:
                targeted_spawn_points.append(sp)
                
        # Shuffle to distribute them randomly across these specific zones
        random.shuffle(targeted_spawn_points)
        
        spawned_cars = 0
        vehicle_blueprints = bp_lib.filter('vehicle.*')
        
        for sp in targeted_spawn_points:
            if spawned_cars >= NUM_VEHICLES:
                break
                
            v_bp = random.choice(vehicle_blueprints)
            vehicle = world.try_spawn_actor(v_bp, sp)
            
            if vehicle:
                vehicle.set_autopilot(True, tm.get_port())
                actor_list.append(vehicle)
                
                #40% chance the car will be speeding aggressively into the intersection
                is_speeding = random.random() < 0.40 
                
                #Force vehicles to stop for pedestrians
                tm.ignore_walkers_percentage(vehicle, 0.0) 
                
                if is_speeding:
                    tm.vehicle_percentage_speed_difference(vehicle, -100.0) # Go much faster than speed limit
                    print(f"Spawned {v_bp.id} (SPEEDING) with ID: {vehicle.id}")
                else:
                    tm.vehicle_percentage_speed_difference(vehicle, 10.0) # Drive normally/slightly slower
                    print(f"Spawned {v_bp.id} at normal speed with ID: {vehicle.id}")
                    
                spawned_cars += 1

        #spawn pedestrians with AI controllers
        print(f"Finding valid sidewalk spawn locations for {NUM_PEDESTRIANS} pedestrians...")
        
        valid_transforms = []
        attempts = 0
        
        while len(valid_transforms) < NUM_PEDESTRIANS and attempts < 5000:
            attempts += 1
            loc = world.get_random_location_from_navigation()
            
            if loc is not None:
                dist_to_center = math.sqrt(loc.x**2 + loc.y**2)
                dist_to_cam_alt = math.sqrt((loc.x - (-2.22))**2 + (loc.y - 95.37)**2)
                dist_to_cam_north = math.sqrt((loc.x - 140)**2 + (loc.y - 0.52)**2)
                
                if (15.0 < dist_to_center < 45.0) or (dist_to_cam_alt < 35.0) or (dist_to_cam_north < 35.0):
                    safe_loc = carla.Location(x=loc.x, y=loc.y, z=loc.z + 1.0)
                    rand_yaw = random.uniform(0.0, 360.0)
                    valid_transforms.append(carla.Transform(safe_loc, carla.Rotation(yaw=rand_yaw)))
        
        print(f"Found {len(valid_transforms)} valid sidewalk locations in view.")
        
        walker_ai_bp = bp_lib.find('controller.ai.walker')
        ai_controllers = []

        for w_transform in valid_transforms:
            try:
                walker_bp = random.choice(bp_lib.filter('walker.pedestrian.*'))
                if walker_bp.has_attribute('is_invincible'):
                    walker_bp.set_attribute('is_invincible', 'false')

                walker = world.try_spawn_actor(walker_bp, w_transform)
                
                if walker:
                    actor_list.append(walker)
                    ai_controller = world.try_spawn_actor(walker_ai_bp, carla.Transform(), walker)
                    if ai_controller:
                        actor_list.append(ai_controller)
                        ai_controllers.append(ai_controller)
            except Exception as e:
                pass 

        print(f"Total spawned actors (vehicles + pedestrians + AI): {len(actor_list)}")

        world.tick()
        
        for ai in ai_controllers:
            ai.start()
            target_loc = world.get_random_location_from_navigation()
            if target_loc:
                ai.go_to_location(target_loc)
            ai.set_max_speed(random.uniform(1.2, 2.5)) 

        #spawn sensors in simulation
        for s_cfg in SENSOR_CONFIG:
            name = s_cfg["name"]
            base_transform = carla.Transform(
                carla.Location(x=s_cfg["x"], y=s_cfg["y"], z=s_cfg["z"]),
                carla.Rotation(yaw=s_cfg["yaw"])
            )

            cam_path, lid_path = f"out_{name}_rgb", f"out_{name}_lidar"
            for folder in [cam_path, lid_path]:
                if not os.path.exists(folder): os.makedirs(folder)

            cam_bp = bp_lib.find('sensor.camera.rgb')
            camera = world.spawn_actor(cam_bp, base_transform)
            
            #configure 2d semantic lidar
            lidar_bp = bp_lib.find('sensor.lidar.ray_cast_semantic')
            lidar_bp.set_attribute('channels', '1')                
            lidar_bp.set_attribute('upper_fov', '0.0')             
            lidar_bp.set_attribute('lower_fov', '0.0')             
            
            lidar_bp.set_attribute('points_per_second', '100000')   
            lidar_bp.set_attribute('rotation_frequency', '20') 
            lidar_bp.set_attribute('range', '100')             
            
            lid_transform = carla.Transform(
                base_transform.location + carla.Location(z=-1.5),  
                base_transform.rotation
            )

            lidar = world.spawn_actor(lidar_bp, lid_transform)

            q_cam, q_lid = queue.Queue(), queue.Queue()
            camera.listen(q_cam.put)
            lidar.listen(q_lid.put)

            sensor_hubs.append({
                "name": name, 
                "lidar_actor": lidar,  
                "q_cam": q_cam, 
                "q_lid": q_lid,
                "path_cam": cam_path, 
                "path_lid": lid_path
            })
            
            actor_list.extend([camera, lidar])

        spectator = world.get_spectator()
        spec_transform = carla.Transform(
            carla.Location(x=SPEC_X, y=SPEC_Y, z=SPEC_Z), 
            carla.Rotation(pitch=-30.0, yaw=SPEC_YAW)
        )

        print("Recording... Press Ctrl+C to stop.")
        
        speed_file = open("actual_speeds.txt", "w")
        
        while True:
            frame = world.tick() 
            spectator.set_transform(spec_transform)

            trackable_actors = [actor for actor in actor_list if 'vehicle' in actor.type_id or 'walker' in actor.type_id]
            for actor in trackable_actors:
                vel = actor.get_velocity() 
                speed_mps = math.sqrt(vel.x**2 + vel.y**2 + vel.z**2)
                speed_file.write(f"{frame},{actor.id},{actor.type_id},{speed_mps}\n")

            for hub in sensor_hubs:
                try:
                    image = hub["q_cam"].get(timeout=2.0)
                    while image.frame < frame: 
                        image = hub["q_cam"].get(timeout=2.0)
                    
                    lidar_data = hub["q_lid"].get(timeout=2.0)
                    while lidar_data.frame < frame: 
                        lidar_data = hub["q_lid"].get(timeout=2.0)

                    if image.frame == frame and lidar_data.frame == frame:
                        image.save_to_disk(f"{hub['path_cam']}/{frame:06d}.png")
                        
                        semantic_dtype = np.dtype([
                            ('x', np.float32), ('y', np.float32), ('z', np.float32),
                            ('cos_angle', np.float32), ('obj_idx', np.uint32), ('obj_tag', np.uint32)
                        ])
                        p_cloud = np.frombuffer(lidar_data.raw_data, dtype=semantic_dtype)

                        mask = np.isin(p_cloud['obj_tag'], [4, 10])
                        target_points = p_cloud[mask]

                        unique_ids = np.unique(target_points['obj_idx'])
                        
                        for uid in unique_ids:
                            obj_pts = target_points[target_points['obj_idx'] == uid]
                            obj_points_only = np.column_stack((obj_pts['x'], obj_pts['y'], obj_pts['z']))
                            if len(obj_points_only) > 0:
                                save_filtered_ply(obj_points_only, f"{hub['path_lid']}/{frame:06d}_v{uid}.ply")

                except queue.Empty:
                    pass 

            print(f"Frame {frame} Synced for all sensors" + " " * 10, end="\r")

    except KeyboardInterrupt:
        print("\nStopping simulation via user command...")
    finally:
        print("\nStopping sensors...")
        for actor in actor_list:
            if actor.type_id.startswith('sensor.'):
                if actor.is_alive:
                    actor.stop()
                    
        if original_settings: 
            world.apply_settings(original_settings)
            
        if speed_file:
            speed_file.close()
            
        print("Destroying actors...")
        client.apply_batch([carla.command.DestroyActor(x) for x in actor_list])
        
        world.tick()
        print("Cleanup finished.")

if __name__ == '__main__':
    main()