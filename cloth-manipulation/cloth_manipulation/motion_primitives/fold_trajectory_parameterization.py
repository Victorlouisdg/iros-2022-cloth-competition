from typing import List

import numpy as np


def transformation_matrix_from_position_and_vecs(pos, x, y, z):
    transformation_matrix = np.eye(4)
    transformation_matrix[:3, 0] = x
    transformation_matrix[:3, 1] = y
    transformation_matrix[:3, 2] = z
    transformation_matrix[:3, 3] = pos
    return transformation_matrix


class FoldTrajectory:
    def __init__(self, start: np.ndarray, end: np.ndarray) -> None:

        # create local Frame
        self.center = (start + end) / 2
        self.x = end - start
        self.len = np.linalg.norm(self.x)
        self.x /= self.len
        self.z = np.array([0, 0, 1])

        self.y = np.cross(self.z, self.x)
        self.fold_frame_in_robot_frame = transformation_matrix_from_position_and_vecs(
            self.center, self.x, self.y, self.z
        )

    def _fold_pose(self, t):
        raise NotImplementedError

    def get_grasp_pose(self):
        return self._fold_pose(0)

    def get_pregrasp_pose(self, alpha=0.10):
        raise NotImplementedError

    def get_fold_retreat_pose(self):
        pose = self._fold_pose(1.0)
        pose[2, 3] += 0.05  # move up
        pose[1, 3] += 0.01
        return pose

    def get_fold_path(self, n_waypoints: int = 50) -> List[np.ndarray]:
        """Samples n_waypoints from the fold path and return them as a list of 4x4 poses."""
        waypoints = [self._fold_pose(completion) for completion in np.linspace(0, 1, n_waypoints)]
        return np.array(waypoints)


class CircularFoldTrajectory(FoldTrajectory):
    def __init__(self, start, end) -> None:
        super().__init__(start, end)

    def _fold_pose(self, t) -> np.ndarray:
        """Parameterization of the fold trajectory
        t = 0 is the grasp pose, t = 1 is the final (release) pose
        """
        assert t <= 1 and t >= 0
        position_angle = np.pi - t * np.pi
        # the radius was manually tuned on a cloth to find a balance between grasp width along the cloth and grasp robustness given the gripper fingers.
        radius = self.len / 2.0 - 0.015
        position = np.array([radius * np.cos(position_angle), 0, radius * np.sin(position_angle)])

        grasp_angle = np.pi / 10
        # bring finger tip down to zero.
        position[2] += (0.085 / 2 * np.sin(grasp_angle) - 0.008) * np.cos(
            grasp_angle
        )  # want the low finger to touch the table so offset from TCP
        position[2] -= 0.008  # 8mm compliance for better grasping

        orientation_angle = max(grasp_angle - t * 2 * grasp_angle, -np.pi / 6)
        x = np.array([np.cos(orientation_angle), 0, np.sin(orientation_angle)])
        x /= np.linalg.norm(x)
        y = np.array([0, -1, 0])

        z = np.cross(x, y)
        return self.fold_frame_in_robot_frame @ transformation_matrix_from_position_and_vecs(position, x, y, z)

    def get_pregrasp_pose(self, offset=0.02):
        grasp_pose = self._fold_pose(0)
        pregrasp_pose = grasp_pose
        # create offset in y-axis for grasp approach (linear motion along +y)
        pregrasp_pose[1, 3] = pregrasp_pose[1, 3] - offset

        return pregrasp_pose


class VLFoldLine(FoldTrajectory):
    def __init__(self, start: np.ndarray, end: np.ndarray) -> None:
        super().__init__(start, end)
        raise NotImplementedError
        # TODO: allow for time parameterization (through linear velocity at each waypoint) in the trajectory generation.


if __name__ == "__main__":
    s = CircularFoldTrajectory(np.array([0.20, -0.2, 0.2]), np.array([0.2, 0.2, 0.2]))
    print(s.get_pregrasp_pose())
    print(s.get_grasp_pose())
    print(s.get_fold_path(4))
    print(s.get_fold_retreat_pose())
