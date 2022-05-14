import logging
import os
import sys
from datetime import date


os.makedirs('./log', exist_ok=True)
_error_log_file = os.path.expanduser('./log/error.txt')
_critical_log_file = os.path.expanduser('./log/critical.txt')

formatter = logging.Formatter('[%(asctime)s %(name)s] %(levelname)s: %(message)s')
default_handler = logging.StreamHandler(sys.stdout)
default_handler.setFormatter(formatter)
error_handler = logging.FileHandler(_error_log_file, encoding='utf8')
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(formatter)
critical_handler = logging.FileHandler(_critical_log_file, encoding='utf8')
critical_handler.setLevel(logging.CRITICAL)
critical_handler.setFormatter(formatter)


def new_logger(name, debug=True):
    logger = logging.getLogger(name)
    logger.addHandler(default_handler)
    logger.addHandler(error_handler)
    logger.addHandler(critical_handler)
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    return logger


def logger(prefix=None):
    log_dir = './log/' + (prefix + '-' if prefix else '') + date.today().strftime('%Y-%m') + '/'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_file_name = date.today().strftime('%Y-%m-%d') + '.txt'
    log_print = open(log_dir + log_file_name, 'a', encoding="utf-8")
    sys.stdout = log_print
    sys.stderr = log_print
    logger_name = 'farm'
    if prefix:
        logger_name = prefix
    return new_logger(logger_name, False)
