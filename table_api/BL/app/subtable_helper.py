import ast
import cv2
import json
import operator
import re

from collections import Counter as counter
from functools import reduce
try:
    from app.ace_logger import Logging
except:
    from ace_logger import Logging

logging = Logging().getLogger('ace')

def subtable_helper(haystack, needle, img):
	if needle:
		needle = re.sub(' +',' ',needle)
		lefts = []
		tops = []
		rights = []
		for each_token in needle.split():

			for each_hay in haystack:
				if(each_token.lower() == each_hay['word'].lower()):
					lefts.append(each_hay['left'])
					tops.append(each_hay['top'])
					rights.append(each_hay['right'])


		left_avg = reduce(lambda x,y : x+y , lefts)/len(lefts)-5
		top_avg = reduce(lambda x,y : x+y , tops)/len(tops)-5
		right_avg = reduce(lambda x,y : x+y , rights)/len(rights)+5

		left_data_left_avg = ''
		right_data_left_avg = ''
		left_data_right_avg = ''
		right_data_right_avg = ''

		for each_hay in haystack:
			if(each_hay['left']>=left_avg and each_hay['top']>=top_avg and each_hay['word'] in needle.split()):
				right_data_left_avg += str(each_hay)+','

		for each_hay in haystack:
			if(each_hay['left']<=left_avg and each_hay['top']>=top_avg and each_hay['word'] in needle.split()):
				left_data_left_avg += str(each_hay)+ ','

		for each_hay in haystack:
			if(each_hay['left']<=right_avg and each_hay['top']>=top_avg and each_hay['word'] in needle.split()):
				left_data_right_avg += str(each_hay)+ ','

		for each_hay in haystack:
			if(each_hay['left']>=right_avg and each_hay['top']>=top_avg and each_hay['word'] in needle.split()):
				right_data_right_avg += str(each_hay)+ ','

		counts = {}
		sects = [right_data_left_avg,left_data_left_avg,right_data_right_avg,left_data_right_avg]

		for sect in sects:
			c = 0
			for each_word in needle.split():
				if(each_word in sect):
					c += 1
			counts[sect] = c

		words = max(counts.items(), key = operator.itemgetter(1))[0]
		words = words[:-1]
		words = '['+words+']'
		str_words = words
		words = ast.literal_eval(words)
		words_matched = ''

		for word in words:
			words_matched += word['word'] + ' '
		words_matched = words_matched.strip()

		needle_first_word = needle.split()[0]
		search_range =  [0, words[0]['top']]
		if len(words_matched.split()) < len(needle.split()):
			for i in range(len(haystack)-1,-1,-1):
				if(haystack[i]['top'] in range(search_range[0],search_range[1])
					and haystack[i]['word'].lower() in needle.lower()):
					if(len(' '.join([word['word'] for word in words]).split()) != len(needle.split())):
						words.insert(0,haystack[i])
					else:
						break

		elif(len(words_matched.split()) > len(needle.split())):
			k = 0
			for i,word in enumerate(words):
				if words[i+k]['word'].lower() != needle.split()[0].lower():
					words.pop(0)
					k -= 1
				else:
					break
		return words
	return []
