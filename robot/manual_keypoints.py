
from collections import namedtuple
from tkinter import Y
import numpy as np 
from camera_toolkit.zed2i import Zed2i
from camera_toolkit.aruco_pose import get_aruco_marker_poses
from camera_toolkit.reproject_to_z_plane import reproject_to_ground_plane
import cv2
from fold import TowelFold
from robotiq2f_tcp import Robotiq2F85TCP
from  rtde_control import RTDEControlInterface as RTDEControl
import numpy as np
import scipy.spatial.transform as transform
import pickle
# specify aruco position in UR base frame
aruco_in_robot_x = -0.004
aruco_in_robot_y = -0.23
robot_to_aruco_translation = np.array([aruco_in_robot_x, aruco_in_robot_y, 0.0])

# load camera to marker transform
with open("marker.pickle", "rb") as f:
    aruco_in_camera_position, aruco_in_camera_orientation = pickle.load(f)
print(f"{aruco_in_camera_position=}")
print(f"{aruco_in_camera_orientation=}")

# opencv mouseclick registration
clicked_coords = []

def clicked_callback_cv(event, x, y, flags, param):
    global u_clicked, v_clicked
    if event == cv2.EVENT_LBUTTONDBLCLK:
        print(f"clicked on {x}, {y}")
        clicked_coords.append(np.array([x,y]))
# open ZED (and assert it is available)
Zed2i.list_camera_serial_numbers()
zed = Zed2i()
cam_matrix =  zed.get_mono_camera_matrix()

# get camera to aruco pose 
img= zed.get_mono_rgb_image()
img = zed.image_shape_torch_to_opencv(img)
cam_matrix =  zed.get_mono_camera_matrix()

aruco_in_camera_transform = np.eye(4)
aruco_in_camera_transform[:3,:3] = aruco_in_camera_orientation
aruco_in_camera_transform[:3,3] = aruco_in_camera_position
# mark the keypoints in image plane by clicking
cv2.imshow("img", img)
cv2.setMouseCallback('img',clicked_callback_cv)

while(True):
    print("click the 4 keypointsbefore closing, mark them clockwise starting with the end of the fold line.")

    cv2.waitKey(0)
    if len(clicked_coords) > 4:
        raise IndexError("too many keypoint clicked, aborting.")
    elif len(clicked_coords) == 4:
        break
    
cv2.destroyAllWindows()
# once 4 are clicked transform them to world coords
image_coords = np.array(clicked_coords)
aruco_coords = [reproject_to_ground_plane(image_coords[i,:], cam_matrix, aruco_in_camera_transform)[0] for i in range(4)]
robot_coords = aruco_coords + robot_to_aruco_translation
print(f"{aruco_coords=}")
print(f"{robot_coords=}")
con = input("Continue? Y/N")
if con == "N":
    raise ValueError("not continuing")

kp1,kp2,kp3,kp4 = robot_coords
cloth = TowelFold(kp1,kp2,kp3,kp4)

print(cloth.x)
pregrasp_in_towel = cloth.pregrasp_pose_in_cloth_frame(0.05)
pregrasp = cloth.robot_to_cloth_base_transform @ pregrasp_in_towel
print(pregrasp)
print(cloth.pose_to_rotvec_waypoint(pregrasp))
pregrasp_pose_rotvec = cloth.pose_to_rotvec_waypoint(pregrasp)

vel = 0.2
acc = 0.1
blend = 0.01
wps = []
num_waypoints = 50
for t in range(0,num_waypoints):
    i = t / num_waypoints
    wp = cloth.pose_to_rotvec_waypoint(cloth.robot_to_cloth_base_transform @cloth.fold_pose_in_cloth_frame(i))
    wps.append(wp.tolist() + [vel, acc,blend])

rtde_c = RTDEControl("10.42.0.162")
gripper = Robotiq2F85TCP("10.42.0.162")
gripper.activate_gripper()
gripper.move_to_position(20,250,10)

rtde_c.moveL(pregrasp_pose_rotvec,vel, acc)
check =  input("continue fold? Press Enter")
rtde_c.moveL(cloth.pose_to_rotvec_waypoint(cloth.robot_to_cloth_base_transform @cloth.fold_pose_in_cloth_frame(0)),vel,acc)
gripper.move_to_position(230,255,10)
rtde_c.moveL(wps)

gripper.move_to_position(20,255,10)
gripper.close()
