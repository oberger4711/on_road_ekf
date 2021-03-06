#!/usr/bin/env python3

import abc
import numpy as np

class ObstacleKF(abc.ABC):
    def __init__(self, x_0, p_0, h, q, r):
        super().__init__()
        self._x_k = x_0
        self._p_k = p_0
        self._h = h
        self._q = q
        self._r = r

    def kf_predict(self, a_k, g_k):
        # Predict state.
        self._x_k = np.matmul(a_k, self._x_k)
        # Predict covariance.
        self._p_k = np.matmul(np.matmul(a_k, self._p_k), a_k.T) + np.matmul(g_k * self._q, g_k.T)
        return self._x_k, self._p_k

    def kf_correct(self, z_k):
        h_t = self._h.T
        # Compute Kalman gain.
        k_k = np.matmul(np.matmul(self._p_k, h_t), np.linalg.inv(np.matmul(np.matmul(self._h, self._p_k), h_t) + self._r))
        print("Kalman Gain:\n {}".format(k_k))
        # Correct state.
        residual = (z_k - np.matmul(self._h, self._x_k))
        print("Residual: {}".format(residual))
        self._x_k = self._x_k + np.matmul(k_k, residual)
        # Correct covariance.
        a = np.eye(3) - np.matmul(k_k, self._h)
        self._p_k = np.matmul(np.matmul(a, self._p_k), a.T) + np.matmul(np.matmul(k_k, self._r), k_k.T)
        print("State Covariance:\n {}".format(self._p_k))
        return self._x_k, self._p_k

    @abc.abstractmethod
    def filter(self, z_k_or_none):
        pass

class FollowTrackObstacleKF(ObstacleKF):

    ACC_VARIANCE = 18000
    MEASUREMENT_VARIANCE = 0.04

    def __init__(self, delta_t, points_lane):
        x_0 = np.array([0, 0, 0]) # p_x [m], p_y [m], v_parallel [cm / s^2]
        p_0 = np.array([[50, 0, 0],
                        [0, 50, 0],
                        [0, 0, 300]])
        h = np.array([[1, 0, 0],
                      [0, 1, 0]])
        q = FollowTrackObstacleKF.ACC_VARIANCE
        r = np.eye(2) * FollowTrackObstacleKF.MEASUREMENT_VARIANCE
        super().__init__(x_0, p_0, h, q, r)
        self._delta_t = delta_t
        self._points_lane = points_lane

    def get_nearest_direction(self):
        # TODO: Interpolate?
        ds = np.linalg.norm(self._points_lane - self._x_k[:2], axis=1)
        i_nn = min(self._points_lane.shape[0] - 2, np.argmin(ds))
        d = self._points_lane[i_nn + 1] - self._points_lane[i_nn]
        d_normalized = d / np.linalg.norm(d)
        return d_normalized

    def predict(self):
        # Linearize lane at nearest neighbour.
        d = self.get_nearest_direction()
        print("Direction", d.T)
        a_k = np.array([[1, 0, (d[0] * self._delta_t) / 100],
                      [0, 1, (d[1] * self._delta_t) / 100],
                      [0, 0, 1]])
        g_k = np.array([[(d[0] * self._delta_t) / 200],
                        [(d[1] * self._delta_t) / 200],
                        [self._delta_t]])
        return self.kf_predict(a_k, g_k)

    def correct(self, z_k):
        return self.kf_correct(z_k)

    def filter(self, z_k_or_none):
        self.predict()
        if z_k_or_none is not None:
            self.correct(z_k_or_none)
        return self._x_k, self._p_k

class SteadyObstacleKF(ObstacleKF):

    PROCESS_NOISE_VARIANCE = 0.01
    MEASUREMENT_VARIANCE = 0.04

    def __init__(self):
        x_0 = np.array([0, 0, 0]) # p_x [m], p_y [m], v_parallel [cm / s^2]
        p_0 = np.array([[50, 0, 0],
                        [0, 50, 0],
                        [0, 0, 0]])
        h = np.array([[1, 0, 0],
                      [0, 1, 0]])
        q = np.eye(3) * SteadyObstacleKF.PROCESS_NOISE_VARIANCE
        r = np.eye(2) * SteadyObstacleKF.MEASUREMENT_VARIANCE
        super().__init__(x_0, p_0, h, q, r)

    def predict(self):
        a_k = np.eye(3)
        g_k = np.eye(3)
        return self.kf_predict(a_k, g_k)

    def correct(self, z_k):
        return self.kf_correct(z_k)

    def filter(self, z_k_or_none):
        self.predict()
        if z_k_or_none is not None:
            self.correct(z_k_or_none)
        return self._x_k, self._p_k
