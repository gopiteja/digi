import ntpath
import requests

# give any path...platform independent...get the base name
def path_leaf(path):
    """give any path...platform independent...get the base name"""
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)

def abby_sdk_ouput(url, abs_path):
    file_name = path_leaf(abs_path)
    files_data = {'file':(file_name, open(abs_path, 'rb'))}
    output = requests.post(url, files=files_data).json()
    return output

# abby_sdk_ouput("https://abbyocr.localtunnel.me", "absolute/path/to/the/file")