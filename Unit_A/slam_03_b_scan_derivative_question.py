# Compute the derivative of a scan.
# 03_b_scan_derivative
# Claus Brenner, 09 NOV 2012
import matplotlib.pyplot as plt
from lego_robot import *

# Find the derivative in scan data, ignoring invalid measurements.
def compute_derivative(scan, min_dist):
    jumps = [ 0 ]
    for i in range(1, len(scan) - 1):
        # --->>> Insert your code here.
        # Compute derivative using formula "(f(i+1) - f(i-1)) / 2".
        # Do not use erroneous scan values, which are below min_dist.
        derivative = 0
        if(scan[i+1] > min_dist and scan[i-1] > min_dist):
            derivative = (scan[i+1] - scan[i-1])/2
        jumps.append(derivative)

    jumps.append(0)
    return jumps


if __name__ == '__main__':

    minimum_valid_distance = 20.0

    # Read the logfile which contains all scans.
    logfile = LegoLogfile()
    logfile.read("robot4_scan.txt")

    # Pick one scan.
    scan_no = 7
    scan = logfile.scan_data[scan_no]

    # Compute derivative, (-1, 0, 1) mask.
    der = compute_derivative(scan, minimum_valid_distance)

    # Plot scan and derivative.
    plt.title("Plot of scan %d" % scan_no)
    plt.plot(scan)
    plt.plot(der)
    plt.show()
