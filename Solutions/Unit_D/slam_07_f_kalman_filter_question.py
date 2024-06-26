# The full Kalman filter, consisting of prediction and correction step.
#
# slam_07_f_kalman_filter
# Claus Brenner, 12.12.2012
from lego_robot import *
from math import sin, cos, pi, atan2, sqrt
from numpy import *
from slam_d_library import get_observations, write_cylinders


class ExtendedKalmanFilter:
    def __init__(self, state, covariance,
                 robot_width, scanner_displacement,
                 control_motion_factor, control_turn_factor,
                 measurement_distance_stddev, measurement_angle_stddev):
        # The state. This is the core data of the Kalman filter.
        self.state = state
        self.covariance = covariance

        # Some constants.
        self.robot_width = robot_width
        self.scanner_displacement = scanner_displacement
        self.control_motion_factor = control_motion_factor
        self.control_turn_factor = control_turn_factor
        self.measurement_distance_stddev = measurement_distance_stddev
        self.measurement_angle_stddev = measurement_angle_stddev

    @staticmethod
    def g(state, control, w):
        x, y, theta = state
        l, r = control
        if r != l:
            alpha = (r - l) / w
            rad = l/alpha
            g1 = x + (rad + w/2.)*(sin(theta+alpha) - sin(theta))
            g2 = y + (rad + w/2.)*(-cos(theta+alpha) + cos(theta))
            g3 = (theta + alpha + pi) % (2*pi) - pi
        else:
            g1 = x + l * cos(theta)
            g2 = y + l * sin(theta)
            g3 = theta

        return array([g1, g2, g3])

    @staticmethod
    def dg_dstate(state, control, w):

        # --->>> Put your method from 07_d_kalman_predict here.
        theta = state[2]
        l, r = control
        if r != l:
            alpha = (r - l) / w
            alpha = (alpha + pi) % (2*pi) - pi
            rad = l/alpha
            m = array([[1, 0, (rad + w/2)*(cos(theta + alpha)-cos(theta))], 
                       [0, 1, (rad + w/2)*(sin(theta + alpha)-sin(theta))], 
                       [0, 0, 1]])
        else:
            m = array([[1, 0, -l*sin(theta)],
                       [0, 1, l*cos(theta)],
                       [0, 0, 1]])

        return m

    @staticmethod
    def dg_dcontrol(state, control, w):

        # --->>> Put your method from 07_d_kalman_predict here.
        theta = state[2]
        l, r = tuple(control)
        if r != l:
            alpha = (r - l) / w
            alpha = (alpha + pi) % (2*pi) - pi
            co_1 = (w*r)/(r-l)**2
            co_2 = (r+l)/(2*(r-l))
            co_3 = (w*l)/(r-l)**2
            m = array([[(co_1*(sin(theta+alpha)-sin(theta)))-(co_2*cos(theta+alpha)), (-co_3*(sin(theta+alpha)-sin(theta)))+(co_2*cos(theta+alpha))],
                       [(co_1*(-cos(theta+alpha)+cos(theta)))-(co_2*sin(theta+alpha)), (-co_3*(-cos(theta+alpha)+cos(theta)))+(co_2*sin(theta+alpha))],
                       [-1/w, 1/w]])
        else:
            m = array([[(1/2)*(cos(theta)+((l/w)*sin(theta))), (1/2)*((-(l/w)*sin(theta))+cos(theta))],
                       [(1/2)*(sin(theta)-((l/w)*cos(theta))), (1/2)*((-(l/w)*cos(theta))+sin(theta))],
                       [-1/w, 1/w]])     
            
        return m

    @staticmethod
    def get_error_ellipse(covariance):
        """Return the position covariance (which is the upper 2x2 submatrix)
           as a triple: (main_axis_angle, stddev_1, stddev_2), where
           main_axis_angle is the angle (pointing direction) of the main axis,
           along which the standard deviation is stddev_1, and stddev_2 is the
           standard deviation along the other (orthogonal) axis."""
        eigenvals, eigenvects = linalg.eig(covariance[0:2,0:2])
        angle = atan2(eigenvects[1,0], eigenvects[0,0])
        return (angle, sqrt(eigenvals[0]), sqrt(eigenvals[1]))        

    def predict(self, control):

        # --->>> Put your method from 07_d_kalman_predict here.
        left, right = control

        sigma_l_sq = (self.control_motion_factor*left)**2 + (self.control_turn_factor*(left-right))**2
        sigma_r_sq = (self.control_motion_factor*right)**2 + (self.control_turn_factor*(left-right))**2
        control_covariance = diag([sigma_l_sq, sigma_r_sq])
        
        G = self.dg_dstate(self.state, control, self.robot_width)
        V = self.dg_dcontrol(self.state, control, self.robot_width)
        self.covariance = G@self.covariance@G.T + V@control_covariance@V.T

        self.state = self.g(self.state, control, self.robot_width)
        return

    @staticmethod
    def h(state, landmark, scanner_displacement):
        """Takes a (x, y, theta) state and a (x, y) landmark, and returns the
           measurement (range, bearing)."""
        dx = landmark[0] - (state[0] + scanner_displacement * cos(state[2]))
        dy = landmark[1] - (state[1] + scanner_displacement * sin(state[2]))
        r = sqrt(dx * dx + dy * dy)
        alpha = (atan2(dy, dx) - state[2] + pi) % (2*pi) - pi

        return array([r, alpha])

    @staticmethod
    def dh_dstate(state, landmark, scanner_displacement):

        # --->>> Put your method from 07_e_measurement derivative here.
        x, y, theta = state
        x_m, y_m = landmark
        d = scanner_displacement
        x_l = x + scanner_displacement * cos(theta)
        y_l = y + scanner_displacement * sin(theta)
        d_x = x_m - x_l
        d_y = y_m - y_l
        q = d_x**2 + d_y**2
        H = array([[-d_x/sqrt(q), -d_y/sqrt(q), (d/sqrt(q))*(d_x*sin(theta)-d_y*cos(theta))],
                   [d_y/q, -d_x/q, (-(d/q)*(d_x*cos(theta)+d_y*sin(theta)))-1]])
        return H

    def correct(self, measurement, landmark):
        """The correction step of the Kalman filter."""

        # --->>> Put your new code here.
        #
        # You will have to compute:
        # H, using dh_dstate(...).
        H = self.dh_dstate(self.state, landmark, scanner_displacement)
        # Q, a diagonal matrix, from self.measurement_distance_stddev and
        #  self.measurement_angle_stddev (remember: Q contains variances).
        Q = diag([self.measurement_distance_stddev**2, self.measurement_angle_stddev**2])
        # K, from self.covariance, H, and Q.
        #  Use linalg.inv(...) to compute the inverse of a matrix.
        K = self.covariance@H.T@linalg.inv(H@self.covariance@H.T+Q)
        # The innovation: it is easy to make an error here, because the
        #  predicted measurement and the actual measurement of theta may have
        #  an offset of +/- 2 pi. So here is a suggestion:
        #   innovation = array(measurement) -\
        #                self.h(self.state, landmark, self.scanner_displacement)
        #   innovation[1] = (innovation[1] + pi) % (2*pi) - pi
        innovation = array(measurement) - self.h(self.state, landmark, self.scanner_displacement)
        innovation[1] = (innovation[1] + pi) % (2*pi) - pi
        # Then, you'll have to compute the new self.state.
        self.state = self.state + K@innovation
        # And finally, compute the new self.covariance. Use eye(3) to get a 3x3
        #  identity matrix.
        #
        self.covariance = (eye(3)-K@H)@self.covariance
        # Hints:
        # dot(A, B) is the 'normal' matrix product (do not use: A*B).
        # A.T is the transposed of a matrix A (A itself is not modified).
        # linalg.inv(A) returns the inverse of A (A itself is not modified).
        # eye(3) returns a 3x3 identity matrix.

        pass # Remove this.

if __name__ == '__main__':
    # Robot constants.
    scanner_displacement = 30.0
    ticks_to_mm = 0.349
    robot_width = 155.0

    # Cylinder extraction and matching constants.
    minimum_valid_distance = 20.0
    depth_jump = 100.0
    cylinder_offset = 90.0
    max_cylinder_distance = 300.0

    # Filter constants.
    control_motion_factor = 0.35  # Error in motor control.
    control_turn_factor = 0.6  # Additional error due to slip when turning.
    measurement_distance_stddev = 200.0  # Distance measurement error of cylinders.
    measurement_angle_stddev = 15.0 / 180.0 * pi  # Angle measurement error.

    # Measured start position.
    initial_state = array([1850.0, 1897.0, 213.0 / 180.0 * pi])
    # Covariance at start position.
    initial_covariance = diag([100.0**2, 100.0**2, (10.0 / 180.0 * pi) ** 2])
    # Setup filter.
    kf = ExtendedKalmanFilter(initial_state, initial_covariance,
                              robot_width, scanner_displacement,
                              control_motion_factor, control_turn_factor,
                              measurement_distance_stddev,
                              measurement_angle_stddev)

    # Read data.
    logfile = LegoLogfile()
    logfile.read("robot4_motors.txt")
    logfile.read("robot4_scan.txt")
    logfile.read("robot_arena_landmarks.txt")
    reference_cylinders = [l[1:3] for l in logfile.landmarks]

    # Loop over all motor tick records and all measurements and generate
    # filtered positions and covariances.
    # This is the Kalman filter loop, with prediction and correction.
    states = []
    covariances = []
    matched_ref_cylinders = []
    for i in range(len(logfile.motor_ticks)):
        # Prediction.
        control = array(logfile.motor_ticks[i]) * ticks_to_mm
        kf.predict(control)

        # Correction.
        observations = get_observations(
            logfile.scan_data[i],
            depth_jump, minimum_valid_distance, cylinder_offset,
            kf.state, scanner_displacement,
            reference_cylinders, max_cylinder_distance)
        
        #observations = observations[-1:]
        for j in range(len(observations)):
            kf.correct(*observations[j])

        # Log state, covariance, and matched cylinders for later output.
        states.append(kf.state)
        covariances.append(kf.covariance)
        matched_ref_cylinders.append([m[1] for m in observations])

    # Write all states, all state covariances, and matched cylinders to file.
    f = open("kalman_prediction_and_correction.txt", "w")
    for i in range(len(states)):
        # Output the center of the scanner, not the center of the robot.
        displaced_state = states[i] + [scanner_displacement * cos(states[i][2]),
                                       scanner_displacement * sin(states[i][2]),
                                       0.0]
        f.write(f"F {displaced_state[0]} {displaced_state[1]} {displaced_state[2]}\n")
        # Convert covariance matrix to angle stddev1 stddev2 stddev-heading form
        e = ExtendedKalmanFilter.get_error_ellipse(covariances[i])
        filterred_data = e + (sqrt(covariances[i][2,2]),)
        f.write(f"E {filterred_data[0]} {filterred_data[1]} {filterred_data[2]} {filterred_data[3]}\n")
        # Also, write matched cylinders.
        write_cylinders(f, "W C", matched_ref_cylinders[i])        

    f.close()
