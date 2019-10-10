import numpy as np
from PIL import Image
import sys
word_space = 10

try:
    from app.vertical_slider import get_word_space
except:
    from vertical_slider import get_word_space

try:
    from app.ace_logger import Logging
except:
    from ace_logger import Logging

logging = Logging()

def sort_ocr(data):
    data = sorted(data, key = lambda i: (i['top']))
    s = 0
    for i in range(len(data)):
        s += data[i]['height']
    thres = s/len(data)
    for i in range(len(data)-1):
        if abs(data[i]['top'] - data[i+1]['top']) < 1.5*thres :
            data[i+1]['top'] = data[i]['top']
    data = (sorted(data, key = lambda i: (i['top'], i['left'])))
    return data

def crop_ocr_data(ocr_data, left,right,top,bottom):
    cropped_ocr_data = []
    for data in ocr_data:
        if data['top']>= top and data['bottom']<= bottom:
            cropped_ocr_data.append(data)

    return cropped_ocr_data

def cluster_headers(ocrData2,headerLeft,headerRight):
    Sum = 0
    ocrData2 = sort_ocr(ocrData2)
    logging.debug('#'*100)
    for i in range(len(ocrData2)):
        logging.debug(f"{ocrData2[i]['word']}")
    space_thres = 0
    header_first_line_top = ocrData2[0]['top']
    line_thres = 0
    for i in range(len(ocrData2)-1):
        space = abs(ocrData2[i+1]['left'] - ocrData2[i]['right'])
        # print(ocrData2[i+1]['word'])
        logging.debug(ocrData2[i]['word'],space,ocrData2[i+1]['word'])
        space_thres = min(space_thres,space)
        line_space = ocrData2[i+1]['top'] - ocrData2[i]['top']
        line_thres = max(line_thres,line_space)
        Sum+= space
    averageDist = Sum/(len(ocrData2)-1)#threshhold
    vers = []
    vers.append([headerLeft,headerLeft])
    if space_thres<=5:
        space_thres += 10
    for i in range(len(ocrData2)-1):
        if((ocrData2[i+1]['left'] - ocrData2[i]['right']) >= space_thres and ocrData2[i]['top']==header_first_line_top  ):
            vers.append([ocrData2[i]['right'],ocrData2[i+1]['left']])
            k = i
    vers.append([headerRight,headerRight])

    return vers


def create_ocr_mask(ocr, shape, top, left):
    temp = np.zeros(shape)

    for word in ocr:
        for j in range(word['top'] - top, word['bottom'] - top):
            # print("coor", j, word['left'] - left, word['right'] - left)
            # print(temp.shape)
            try:
                temp[j,range(word['left'] - left, word['right'] - left)] = 255
            except Exception as e:
                logging.exception(f'{e}')
            # temp[int(j), range(int(word['left']), int(word['right']))] = 255

    return temp


def find_peaks(peaks):
    """

    :return:
    """
    groups = []
    # if peaks:
    prev = peaks[0]
    start = prev
    forAvg = 0
    for peak in peaks[1:]:
        if prev != peak - 1:
            forAvg += prev - start
            temp_group = [start, prev - start]
            groups.append(temp_group)
            start = peak
        prev = peak

    forAvg += prev - start
    temp_group = [start, prev - start]
    groups.append(temp_group)

    return groups


def peaks_actually_between_header(header_column_wise_data, groups):
    """

    :param header_column_wise_data:
    :param groups:
    :return:
    """
    header_group = []
    for ind, header in enumerate(header_column_wise_data[:-1]):
        # left header right and right header left
        left_right = header_column_wise_data[ind]['coords'][2]
        right_left = header_column_wise_data[ind + 1]['coords'][1]
        header_lines = []
        for value in groups:
            # check_val = value[0]+int(left)
            check_val = value[0]
            if check_val in range(left_right, right_left):
                header_lines.append(value)
        if header_lines:
            header_group.append(header_lines)

    return header_group


def calibrate_peaks(header_group, left):
    """

    :param header_group:
    :return:
    """
    new_group = []
    for ind, header_lines in enumerate(header_group):
        # value = my_max(header_lines, identity)
        # new_group.append(int(value[0] + int(value[1]/2))+int(left))
        if header_lines[1] > word_space:
            new_group.append(int(header_lines[0] + int(header_lines[1] / 2))+int(left))

    return new_group


def show_lines_on_image(new_group, image_arr, left, axis, sum_vals):
    """

    :param new_group:
    :return:
    """
    new_temp = np.ones(image_arr.shape)
    for peak1 in new_group:
        peak = peak1 - int(left)
        if axis == 1:
            new_temp[range(peak - 4, peak + 4)] = 0
        else:
            if peak - 4 > 0 and peak + 4 < len(sum_vals):
                new_temp[:, range(peak - 4, peak + 4)] = 0

    # Image.fromarray(np.uint8(image_arr * new_temp)).show()
    logging.debug("exiting")

def convert_np_image_bw(ndImage, height):
    """

    :param ndImage:
    :param height:
    :return:
    """
    image = Image.fromarray(np.uint8(ndImage))
    image = image.convert('L')
    # image = image.resize((image.width, height))
    # image = PIL.ImageOps.invert(image)
    image_arr = np.asarray(image)

    # image.show()
    return image_arr


def ocrMask(ocr, width, height, left, top, bottom, right, axis=1):
    """

    :param ndImage:
    :param ocr:
    :param width:
    :param height:
    :param left:
    :param top:
    :param bottom:
    :param header_column_wise_data:
    :param axis:
    :return:
    """
    # image_arr = convert_np_image_bw(ndImage, height)

    try:
        temp = create_ocr_mask(ocr, ((bottom-top), (right-left)), top, left)

        temp_img = Image.fromarray(np.uint8(temp))
        # temp_img.show()
        sum_vals = temp.sum(axis=axis)

        val = 0.
        # plot_at_y(sum_vals, val)
        peaks, = np.where(sum_vals == 0)

        groups = find_peaks(peaks)

        # header_group = peaks_actually_between_header(header_column_wise_data, groups)

        new_group = calibrate_peaks(groups, left)

        # show_lines_on_image(new_group, image_arr, left, axis, sum_vals)
    except Exception as e:
        logging.exception(e)
        # print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno), type(e).__name__, e)
        new_group = []
        # print(e.print_stack)

    return new_group

def cluster_headers_chooser(ocrData, headerTop, headerLeft, headerRight, headerBottom):
    """

    :param ocrData:
    :param T_h:
    :param L_h:
    :param R_h:
    :param B_h:
    :return:
    """
    # word_space = get_word_space(ocrData)
    cropped_ocr_data = crop_ocr_data(ocrData, headerLeft, headerRight, headerTop, headerBottom)

    lines = ocrMask(cropped_ocr_data, (headerRight - headerLeft), (headerBottom - headerTop), headerLeft,
                    headerTop, headerBottom, headerRight, axis=0)

    return lines
