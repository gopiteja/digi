'''
Logging initialization
'''

import logging

def logger():
    logging.basicConfig(level=logging.WARNING,format='%(levelname)-8s %(filename)s:%(lineno)-5d %(funcName)-5s() \n\t\t\t\t\t\t  %(message)s \n')
    logger = logging.getLogger(__name__)
    return logger
