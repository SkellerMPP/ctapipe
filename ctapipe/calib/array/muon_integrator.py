from shapely.geometry import Polygon,LineString
import math
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage.filters import correlate1d

__all__ = ['MuonLineIntegrate']


class MuonLineIntegrate(object):
    """
    Object for calculating the expected 2D shape of muon image for a given mirror geometry.
    Geometry is passed to the class as a series of points defining the outer edge of the array
    and a set of points defining the shape of the central hole (if present). Muon profiles are
    then calculated bsed of the line integral along a given axis from the muon impact point.

    Expected 2D images can then be generated when the pixel geometry is passed to the class.
    """
    def __init__(self, mirror_points, hole_points, pixel_width=0.2, oversample_bins = 5):
        """
        Initialisation function, store shapes of mirror and hole
        :param mirror_points: list
            List of points defining mirror shape
        :param hole_points: list
            List of points defining hole shape
        :param pixel_width: float
            width of pixel in camera
        :param oversample_bins: int
            number of angular bins to evaluate for each pixel width
        :return: None
        """
        self.mirror = Polygon(mirror_points)
        self.hole = Polygon(hole_points)
        self.pixel_width = pixel_width
        self.oversample_bins = oversample_bins

    def intersect_polygon(self,impact_x,impact_y, angle):
        """
        Perform line integration along a given axis in the mirror frame given an impact
        point on the mirrot
        :param impact_x: float
            Impact position on mirror (tilted telescope system)
        :param impact_y: float
            Impact position on mirror (tilted telescope system)
        :param angle: float
            Angle along which to integrate mirror
        :return: float
            length from impact point to mirror edge
        """

        #First convert vector on mirror to a line
        x1,y1 = self.dir_to_line(impact_x,impact_y, angle,length=100)
        line = [(impact_x, impact_y), (x1,y1)]

        #Create shapely line
        shapely_line = LineString(line)
        try:
            #intersect with polygon
            intersection_line = list(self.mirror.intersection(shapely_line).coords)
        except:
            # incase no interception found return 0
            return 0
        line_intersect = LineString(intersection_line)

        # then do the same for the hole
        try:
            intersection_hole = list(self.hole.intersection(shapely_line).coords)
            hole_intersect = LineString(intersection_hole)
            length_hole = hole_intersect.length
        except:
            length_hole = 0

        #line integral is the difference of these two
        return line_intersect.length - length_hole

    def dir_to_line(self,centre_x,centre_y,angle, length=500):
        """
        Convert vector style definition of line (point + angle) to two points needed
        for shapely lines
        :param centre_x: float
            Impact point
        :param centre_y: float
            Impact point
        :param angle: float
            Direction of line
        :param length: float
            Length of line
        :return: float,float
            End point of line
        """
        del_x = length * np.sin(angle)
        del_y = length * np.cos(angle)

        x1 = centre_x + del_x
        y1 = centre_y + del_y

        return x1,y1

    def plot_pos(self,impact_x,impact_y,radius):
        """
        Perform intersection over all angles and return length
        :param impact_x: float
            Impact point on mirror
        :param impact_y: float
            Impact point on mirror
        :param ang: ndarray
            Angles over which to integrate
        :return: ndarray
            Chord length for each angle
        """

        #Currently this is don't with a loop, should be made more pythonic later!
        bins = int((2 * math.pi * radius)/self.pixel_width) * self.oversample_bins
        ang = np.linspace(0, 2*math.pi,bins)
        l = np.zeros(bins)

        i=0
        for a in ang:
            l[i] = self.intersect_polygon(impact_x,impact_y,a)
            i += 1
        l = correlate1d(l,np.ones(self.oversample_bins),mode="wrap")
        l /= self.oversample_bins

        return ang,l

    def pos_to_angle(self,centre_x,centre_y,pixel_x,pixel_y):
        """

        :param centre_x:
        :param centre_y:
        :param pixel_x:
        :param pixel_y:
        :return:
        """
        del_x = pixel_x - centre_x
        del_y = pixel_y - centre_y

        ang = np.arctan2(del_x,del_y)
        return ang

    def image_prediction(self,impact_x,impact_y,centre_x,centre_y,radius,width,pixel_x,pixel_y):
        """

        :param impact_x:
        :param impact_y:
        :param centre_x:
        :param centre_y:
        :param radius:
        :param width:
        :param pixel_x:
        :param pixel_y:
        :return:
        """
        ang = self.pos_to_angle(centre_x,centre_y,pixel_x,pixel_y)
        ang = ang + math.pi
        #creat
        #pred = np.zeros(pixel_x.shape)
        ang_prof,profile = self.plot_pos(impact_x,impact_y,radius)

        pred = np.interp(ang,ang_prof,profile)

        radial_dist = np.sqrt(np.power(pixel_x-centre_x,2) + np.power(pixel_y-centre_y,2))
        ring_dist = radial_dist - radius

        pred = pred * np.exp(-np.power(ring_dist/width,2))/(np.sqrt(math.pi*2*np.power(width,2)))

        return pred