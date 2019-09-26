import operator
import cv2
try:
    from app.ace_logger import Logging
except:
    from ace_logger import Logging

logging = Logging().getLogger('ace')

def find_intersections(horizontal_lines,vertical_lines):
	intersections = []
	horizontal_lines.sort(key=operator.itemgetter(1))
	vertical_lines.sort(key=operator.itemgetter(0))

	for hor in horizontal_lines:
		for ver in vertical_lines:
			if((hor[0][1]>=ver[0][1] and hor[0][1]<=ver[1][1]) and (hor[0][0]<=ver[0][0] and hor[1][0]>=ver[0][0])):
				intersections.append([ver[0][0],hor[0][1]])

	expected_points = len(horizontal_lines) * len(vertical_lines)
	found_points = len(intersections)
	message = u'\nSomething wrong in number of intersections point. Found {}, Expected {}\U0001F914'.format(found_points, expected_points)

	return intersections
