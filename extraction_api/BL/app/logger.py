import logging
import sys
from logging.handlers import TimedRotatingFileHandler

FORMATTER = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
LOG_FILE = "my_app.log"

def get_console_handler():
   console_handler = logging.StreamHandler(sys.stdout)
   console_handler.setFormatter(FORMATTER)
   return console_handler

def get_file_handler():
   file_handler = TimedRotatingFileHandler(LOG_FILE, when='midnight')
   file_handler.setFormatter(FORMATTER)
   return file_handler

def get_logger(logger_name):
   logger = logging.getLogger(logger_name)
   logger.setLevel(logging.DEBUG) # better to have too much log than not enough
   logger.addHandler(get_console_handler())
   logger.addHandler(get_file_handler())
   # with this pattern, it's rarely necessary to propagate the error up to parent
   logger.propagate = False
   return logger

class custom_logger:
   def __init__(self, file_name):
      self.my_logger = get_logger(file_name)

   def logger_debug(self, frame_info, string):
      self.my_logger.debug("{} - {}".format(frame_info, string))

   def logger_info(self, frame_info, string):
      self.my_logger.info("{} - {}".format(frame_info, string))

   def logger_warning(self, frame_info, string):
      self.my_logger.warning("{} - {}".format(frame_info, string))

   def logger_error(self, frame_info, string):
      self.my_logger.error("{} - {}".format(frame_info, string))

   def logger_exception(self, frame_info, string):
      self.my_logger.exception("{} - {}".format(frame_info, string))

   def logger_critical(self, frame_info, string):
      self.my_logger.critical("{} - {}".format(frame_info, string))