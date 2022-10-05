from cloth_manipulation.setup_hw import setup_hw
from cloth_manipulation.motion_primitives.pull import execute_pull_primitive, select_towel_pull
from camera_toolkit.zed2i import Zed2i
from camera_toolkit.reproject import reproject_to_world_z_plane


import numpy as np
if __name__ == "__main__":
    dual_arm =setup_hw()
    from camera_toolkit.reproject import reproject_to_world_z_plane
    from cloth_manipulation.manual_keypoints import get_manual_keypoints, aruco_in_camera_transform


    # open ZED (and assert it is available)
    Zed2i.list_camera_serial_numbers()
    zed = Zed2i()

    # L move to home to avoid collisions with other robot?
    dual_arm.dual_moveL(dual_arm.victor_ur.home_pose,dual_arm.louise_ur.home_pose, vel = 2*dual_arm.DEFAULT_LINEAR_VEL)
    dual_arm.dual_moveL(dual_arm.victor_ur.out_of_way_pose,dual_arm.louise_ur.out_of_way_pose, vel = 2* dual_arm.DEFAULT_LINEAR_VEL)
    while(True):


        keypoints_in_camera = np.array(get_manual_keypoints(zed, 4))
        keypoints_in_world = reproject_to_world_z_plane(keypoints_in_camera,zed.get_camera_matrix(),aruco_in_camera_transform)

        pullprimitive = select_towel_pull(keypoints_in_world)
        if np.linalg.norm(pullprimitive.start_position - pullprimitive.end_position) < 0.05:
            print("pull was less than 5cm, no need to execute")
            break
        print(pullprimitive)
        execute_pull_primitive(pullprimitive,dual_arm)

    dual_arm.dual_moveL(dual_arm.victor_ur.home_pose,dual_arm.louise_ur.home_pose, vel = 2*dual_arm.DEFAULT_LINEAR_VEL)