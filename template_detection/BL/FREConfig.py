import sys

## Folder with FRE dll
def get_dll_folder():
    if( is_64bit_configuration() ):
        return "C:\\Program Files\\ABBYY SDK\\12\\FineReader Engine\\Bin64"
    else:
        return "C:\\Program Files\\ABBYY SDK\\12\\FineReader Engine\\Bin"

## Return full path to Samples directory
def get_samples_folder():
    return "D:\\algonox\\ABBYY\\ABBYY\\SDK\\12\\FineReader Engine\\Samples"

## Return full path to Samples directory
def get_customer_project_id():
    return "83FyunWvCj4nuegsxyjY"

## Return full path to Samples directory
def get_license_path():
    return ""

## Return full path to Samples directory
def get_license_password():
    return ""

## Determines whether the current configuration is a 64-bit configuration
def is_64bit_configuration():
    return sys.maxsize > 2**32