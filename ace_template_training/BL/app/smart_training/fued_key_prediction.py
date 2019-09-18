from utils import centroid_hunt
from utils import find_closest_mate

def feud_keywords_prediction(values, file_keywords):
	"""
	Author : Akshat Goyal

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
				}
			]

	"""
	keywords = []

	values = centroid_hunt(values)

	file_keywords = centroid_hunt(file_keywords)

	closest_keywords = []

	if values:
		closest_keywords = find_closest_mate(values[0], file_keywords, no_of_mate=4)


	return closest_keywords
