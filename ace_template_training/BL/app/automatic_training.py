import os
from scipy.spatial import distance
import cv2
import pdb
import json

# from pdf_plumber import ocr



def print_dirs_recursively(root_dir, files):
    # root_dir = os.path.abspath(root_dir)
    # print(root_dir)

    for item in os.listdir(root_dir):
        item_full_path = os.path.join(root_dir, item)
        files.append(item_full_path)
        if os.path.isdir(item_full_path):
            print_dirs_recursively(item_full_path, files)

    return files

def find_center(word):
    x = word['left'] + (word['right'] - word['left'])/2
    y = word['top'] + (word['bottom'] - word['top'])/2

    return (x, y)

def eculidean_distance(word_1, word_2):
    a = find_center(word_1)
    b = find_center(word_2)

    dst = distance.euclidean(a, b)

    return dst

def segregate_acc_coord(words_cons):
    segregated_word = []
    words = list(words_cons)
    # word_dis = [[0 for x in range(len(words))] for y in range(len(words))]
    for idx_1, word_1 in enumerate(words):

        
        if not word_1['used']:
            word_1['used'] = True
        else:
            continue
        
        temp_list = [word_1]
        for idx_2, word_2 in enumerate(words):
            if word_2['used']:
                continue

            dis = eculidean_distance(word_1, word_2)
                
            if dis < 20:
                word_2['used'] = True
                temp_list.append(word_2)

        segregated_word.append(temp_list)

    return segregated_word 



# print(ocr("/home/akshat/program/automatic_training/input/spicejet_A4CLWY_12719_0000184045147.pdf", 670))

# exit()
# files = []
# files = print_dirs_recursively("/home/akshat/program/automatic_training/finnair", files)

# no_of_files = len(files)

# # print(files)
# files_ocr = []

# for file in files:
#     files_ocr.append(ocr(file, 670))




def cluster_similar_words(files_ocr):
    words = {}
    # pdb.set_trace()
    no_of_files = len(files_ocr)

    for file_ocr in files_ocr:
        # file_ocr = json.loads(file_ocr)
        for page in file_ocr:
            for word in page:
                word['used'] = False
                # if word['word'].lower() in "date:".lower():
                #     print(word)
                    # pass
                if word['word'].lower() in words:
                    words[word['word'].lower()].append(word)
                else:
                    words[word['word'].lower()] = [word]

    max_len = 0
    max_word = ''
    # print(words)

    final_list = []

    for key, word in words.items():
        if len(word) >= no_of_files:
            # print(word)
            s_w = segregate_acc_coord(word)
            # print(s_w)
            for wor in s_w:
                    if len(wor) >= no_of_files:
                        # for i in wor:
                        final_list.append(wor[0])
                            # print(i)
                        if len(wor) > max_len:
                            max_len = len(wor)
                            max_word = wor
    return final_list


# img = cv2.imread('/home/akshat/program/automatic_training/0001.jpg')
# w,h,c = img.shape
# rf = 670/int(h)
# # img = cv2.resize(img, (0,0), fx=rf, fy=rf)
# # img = cv2.resize(img, (0,0))
# for word in final_list:
#     # print(word['word'])
#     t = int(word['top']/rf)
#     l = int(word['left']/rf)
#     b = int(word['bottom']/rf)
#     r = int(word['right']/rf)
#     cv2.rectangle(img, (l,t), (r,b), (0,0,255),2)


# img = cv2.resize(img, (600,600), interpolation = cv2.INTER_AREA)
# cv2.imshow('img',img)
# cv2.waitKey()