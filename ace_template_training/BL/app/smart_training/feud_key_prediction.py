import pdb

try:
	from app.smart_training.utils import centroid_hunt
	from app.smart_training.utils import find_closest_mate
	from app.smart_training.utils import calculate_limit
	from app.smart_training.utils import ocrDataLocal
	from app.smart_training.utils import make_scope
	from app.smart_training.utils import get_rel_info
except:
	from smart_training.utils import centroid_hunt
	from smart_training.utils import find_closest_mate
	from smart_training.utils import calculate_limit
	from smart_training.utils import ocrDataLocal
	from smart_training.utils import make_scope
	from smart_training.utils import get_rel_info

threshold_loop = 5
increment = 20
small_increment = 5

def check_for_orientation(key, value, orientation=''):
	direction = get_rel_info(key, value, direction=True)
	if direction == orientation:
		return True
	else:
		return False

def finding_top_soul(lonely_soul, top, left, right, bottom, world, width, height, value_ocr):

	global threshold_loop
	global increment
	global small_increment

	left_distance = lonely_soul['mid_x'] - left
	top_distance = lonely_soul['mid_y'] - top
	right_distance = right - lonely_soul['mid_x']
	bottom_distance = bottom - lonely_soul['mid_y']


	closest_soul = []

	while(top_distance < left_distance):
		top_distance += small_increment

		temp = lonely_soul['mid_x'] - top_distance
		if temp > 0:
			if not ocrDataLocal(temp, left, right, bottom, value_ocr):
				new_top = temp
			else:
				break
		else:
			break
		# we have to increase the top
		local_world = ocrDataLocal(new_top, left, right, bottom, world)
		closest_soul = find_closest_mate(lonely_soul, local_world, 1)
		if closest_soul:
			if check_for_orientation(closest_soul[0], lonely_soul, 'top'):
				break
			else:
				closest_soul = []

	pdb.set_trace()
	if not closest_soul:
		left_distance = top_distance

		for i in range(threshold_loop):
			left_distance += increment
			top_distance += increment
			right_distance += increment

			new_left = left
			new_top = top
			new_bottom = bottom
			new_right = right

			temp = lonely_soul['mid_y'] - top_distance
			if temp > 0:
				if not ocrDataLocal(temp, new_left, new_right, bottom, value_ocr):
					new_top = temp

			temp = lonely_soul['mid_x'] - left_distance 
			if temp > 0:
				if not ocrDataLocal(new_top, temp, new_right, bottom, value_ocr):
					new_left = temp

			temp = lonely_soul['mid_x'] + right_distance 
			if temp < width:
				if not ocrDataLocal(new_top, new_left, temp, bottom, value_ocr):
					new_right = temp


			local_world = ocrDataLocal(new_top, new_left, new_right, bottom, world)
			closest_soul = find_closest_mate(lonely_soul, local_world, 1)

			if closest_soul:
				if check_for_orientation(closest_soul[0], lonely_soul, 'top'):
					break
				else:
					closest_soul = []


	return closest_soul

def finding_bottom_soul(lonely_soul, top, left, right, bottom, world, width, height, value_ocr):
	"""
	"""
	global threshold_loop
	global increment
	global small_increment

	left_distance = lonely_soul['mid_x'] - left
	top_distance = lonely_soul['mid_y'] - top
	right_distance = right - lonely_soul['mid_x']
	bottom_distance = bottom - lonely_soul['mid_y']

	new_bottom = bottom
	while(bottom_distance < left_distance):
		bottom_distance += small_increment

		temp = lonely_soul['mid_y'] + bottom_distance
		if temp < height:
			if not ocrDataLocal(top, left, right, temp, value_ocr):
				new_bottom = temp
			else:
				break
		else:
			break

		local_world = ocrDataLocal(top, left, right, new_bottom, world)
		closest_soul = find_closest_mate(lonely_soul, local_world, no_of_mate=1)
		if closest_soul:
			if check_for_orientation(closest_soul[0], lonely_soul, 'bottom'):
				break
			else:
				closest_soul = []

	if not closest_soul:
		left_distance = bottom_distance

		for i in range(threshold_loop):
			left_distance += increment
			bottom_distance += increment
			right_distance += increment
			
			new_left = left
			new_top = top
			new_bottom = bottom
			new_right = right

			temp = lonely_soul['mid_y'] + bottom_distance
			if temp < height:
				if not ocrDataLocal(top, new_left, new_right, temp, value_ocr):
					new_bottom = temp

			temp = lonely_soul['mid_x'] - left_distance 
			if temp > 0:
				if not ocrDataLocal(top, temp, new_right, new_bottom, value_ocr):
					new_left = temp
			

			temp = lonely_soul['mid_x'] + right_distance 
			if temp < width:
				if not ocrDataLocal(top, new_left, temp, new_bottom, value_ocr):
					new_right = temp

			
			local_world = ocrDataLocal(top, new_left, new_right, new_bottom, world)
			closest_soul = find_closest_mate(lonely_soul, local_world, no_of_mate=1)

			if closest_soul:
				if check_for_orientation(closest_soul[0], lonely_soul, 'bottom'):
					break
				else:
					closest_soul = []


	return closest_soul


def finding_right_soul(lonely_soul, top, left, right, bottom, world, width, height, value_ocr):
	"""
	"""

	global threshold_loop
	global increment
	global small_increment

	left_distance = lonely_soul['mid_x'] - left
	top_distance = lonely_soul['mid_y'] - top
	right_distance = right - lonely_soul['mid_x']
	bottom_distance = bottom - lonely_soul['mid_y']

	closest_soul = []
	while(right_distance < top_distance):
		right_distance += small_increment

		temp = lonely_soul['mid_x'] + right_distance 
		if temp < width:
			if not ocrDataLocal(top, left, tmep, bottom, value_ocr):
				new_right = temp
			else:
				break
		else:
			break

		local_world = ocrDataLocal(top, left, new_right, bottom, world)
		closest_soul = find_closest_mate(lonely_soul, local_world, no_of_mate=1)
		if closest_soul:
			if check_for_orientation(closest_soul[0], lonely_soul, 'right'):
				break
			else:
				closest_soul = []

	if not closest_soul:
		top_distance = right_distance
		bottom_distance = right_distance

		for i in range(threshold_loop):
			top_distance += increment
			bottom_distance += increment
			right_distance += increment

			new_left = left
			new_top = top
			new_bottom = bottom
			new_right = right

			temp = lonely_soul['mid_y'] + bottom_distance
			if temp < height:
				if not ocrDataLocal(new_top, left, new_right, temp, value_ocr):
					new_bottom = temp

			temp = lonely_soul['mid_y'] - top_distance 
			if temp > 0:
				if not ocrDataLocal(temp, left, new_right, new_bottom, value_ocr):
					new_top = temp
			

			temp = lonely_soul['mid_x'] + right_distance 
			if temp < width:
				if not ocrDataLocal(new_top, left, temp, new_bottom, value_ocr):
					new_right = temp
			
			local_world = ocrDataLocal(new_top, left, new_right, new_bottom, world)
			closest_soul = find_closest_mate(lonely_soul, local_world, no_of_mate=1)

			if closest_soul:
				if check_for_orientation(closest_soul[0], lonely_soul, 'right'):
					break
				else:
					closest_soul = []


	return closest_soul

def finding_left_soul(lonely_soul, top, left, right, bottom, world, width, height, value_ocr):

	global threshold_loop
	global increment
	global small_increment

	left_distance = lonely_soul['mid_x'] - left
	top_distance = lonely_soul['mid_y'] - top
	right_distance = right - lonely_soul['mid_x']
	bottom_distance = bottom - lonely_soul['mid_y']

	while(left_distance < top_distance):
		left_distance += small_increment

		temp = lonely_soul['mid_x'] - left_distance 
		if temp > 0:
			if not ocrDataLocal(top, temp, right, bottom, value_ocr):
				new_left = temp
			else:
				break
		else:
			break

		local_world = ocrDataLocal(top, new_left, right, bottom, world)
		closest_soul = find_closest_mate(lonely_soul, local_world, 1)
		if closest_soul:
			if check_for_orientation(closest_soul[0], lonely_soul, 'left'):
				break
			else:
				closest_soul = []

	if not closest_soul:
		top_distance = left_distance

		for i in range(threshold_loop):
			left_distance += increment
			top_distance += increment
			bottom_distance += increment

			new_left = left
			new_top = top
			new_bottom = bottom
			new_right = right

			temp = lonely_soul['mid_y'] + bottom_distance
			if temp < height:
				if not ocrDataLocal(new_top, new_left, right, temp, value_ocr):
					new_bottom = temp

			temp = lonely_soul['mid_x'] - left_distance 
			if temp > 0:
				if not ocrDataLocal(new_top, temp, right, new_bottom, value_ocr):
					new_left = temp
			

			temp = lonely_soul['mid_y'] - top_distance 
			if temp > 0:
				if not ocrDataLocal(temp, new_left, right, new_bottom, value_ocr):
					new_top = temp

			local_world = ocrDataLocal(new_top, new_left, right, new_bottom, world)
			closest_soul = find_closest_mate(lonely_soul, local_world, 1)

			if closest_soul:
				if check_for_orientation(closest_soul[0], lonely_soul, 'left'):
					break
				else:
					closest_soul = []


	return closest_soul

def restricted_closest_mate_left(lonely_soul, world, value_ocr, first_closest_soul={},no_of_mate=1):
	mates = {}
	mates['left'] = first_closest_soul

	top = lonely_soul['top']
	bottom = lonely_soul['bottom']
	right = lonely_soul['right']
	#because nothing can be left than this for starting
	left = first_closest_soul['right']

	closest_soul = []
	

	width, height = calculate_limit(world)


	closest_soul = finding_top_soul(lonely_soul, top, left, right, bottom, world, width, height, value_ocr)
	if closest_soul:
		mates['top'] = closest_soul[0]

	pdb.set_trace()
	closest_soul = finding_bottom_soul(lonely_soul, top, left, right, bottom, world, width, height, value_ocr)
	if closest_soul:
		mates['bottom'] = closest_soul[0]	

		
	closest_soul = finding_right_soul(lonely_soul, top, left, right, bottom, world, width, height, value_ocr)
	if closest_soul:
		mates['right'] = closest_soul[0]

	return mates



def restricted_closest_mate_top(lonely_soul, world, value_ocr, first_closest_soul={},no_of_mate=1):
	mates = {}
	mates['top'] = first_closest_soul

	top = first_closest_soul['bottom']
	bottom = lonely_soul['bottom']
	right = lonely_soul['right']
	#because nothing can be left than this for starting
	left = lonely_soul['left']

	closest_soul = []
	

	width, height = calculate_limit(world)


	closest_soul = finding_left_soul(lonely_soul, top, left, right, bottom, world. width, height, value_ocr)
	if closest_soul:
		mates['left'] = closest_soul[0]


	closest_soul = finding_bottom_soul(lonely_soul, top, left, right, bottom, world, width, height, value_ocr)
	if closest_soul:
		mates['bottom'] = closest_soul[0]	

		
	closest_soul = finding_right_soul(lonely_soul, top, left, right, bottom, world, width, height, value_ocr)
	if closest_soul:
		mates['right'] = closest_soul[0]

	return mates



def find_closest_mate_feud(lonely_soul, world, value_ocr, first_closest_mate={}):
	"""
	"""
	mates = {}
	if first_closest_mate:
		if 'left' in first_closest_mate:
			mates = restricted_closest_mate_left(lonely_soul, world, value_ocr, first_closest_mate['left'])
		else:
			mates = restricted_closest_mate_top(lonely_soul, world, value_ocr, first_closest_mate['top'])
	else:
		top = lonely_soul['top']
		bottom = lonely_soul['bottom']
		right = lonely_soul['right']
		#because nothing can be left than this for starting
		left = lonely_soul['left']

		closest_soul = []
		

		width, height = calculate_limit(world)


		closest_soul = finding_left_soul(lonely_soul, top, left, right, bottom, world, width, height, value_ocr)
		if closest_soul:
			mates['left'] = closest_soul[0]


		closest_soul = finding_bottom_soul(lonely_soul, top, left, right, bottom, world, width, height, value_ocr)
		if closest_soul:
			mates['bottom'] = closest_soul[0]	

			
		closest_soul = finding_right_soul(lonely_soul, top, left, right, bottom, world, width, height, value_ocr)
		if closest_soul:
			mates['right'] = closest_soul[0]

		closest_soul = finding_top_soul(lonely_soul, top, left, right, bottom, world, width, height, value_ocr)
		if closest_soul:
			mates['top'] = closest_soul[0]

	return mates


def feud_keywords_prediction(values, file_keywords, kv_keywords, value_ocr):
	"""
	Author : Akshat Goyal
	
	Todo : this will not take keyword if keyword and some other value are in same alignment
	Args:
		values : the value for which the keyword has to be extracted
			[
				{
					word,
					coordinates				
				},

			]

		file_keywords : all the potential keyword in the file
			[
				{
					word,
					coordinates
				},
			]

	"""
	keywords = []

	values = centroid_hunt(values)

	file_keywords = centroid_hunt(file_keywords)

	value_ocr = centroid_hunt(value_ocr)

	closest_keywords = {}

	if values:
		#if keyword then we can take that as a starting point for feud
		if kv_keywords:
			direction = get_rel_info(kv_keywords[0], values[0],direction=True)

			if direction == 'left':
				closest_keywords = {'left' : kv_keywords[0]}
			else:
				closest_keywords = {'top' : kv_keywords[0]}
			
			closest_keywords = find_closest_mate_feud(values[0], file_keywords, value_ocr, closest_keywords)

		else:
			closest_keywords = find_closest_mate_feud(values[0], file_keywords, value_ocr)



	return closest_keywords
