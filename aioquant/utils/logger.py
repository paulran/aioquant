# -*- coding:utf-8 -*-

"""
Log printer.

Author: HuangTao
Date:   2018/04/08
Email:  huangtao@ifclover.com
"""

import os
import sys
import shutil
import logging
import traceback
from logging.handlers import TimedRotatingFileHandler

initialized = False


def initLogger(level="DEBUG", path=None, name=None, clear=False, backup_count=0, console=True):
    """Initialize logger.

    Args:
        level: Log level, `DEBUG` or `INFO`, default is `DEBUG`.
        path: Log path, default is `/var/log/aioquant`.
        name: Log file name, default is `quant.log`.
        clear: If clear all history log file when initialize, default is `False`.
        backup_count: How many log file to be saved. We will save log file per day at middle nigh,
            default is `0` to save file permanently.
        console: If print log to console, otherwise print to log file.
    """
    global initialized
    if initialized:
        return
    path = path or "/var/log/aioquant"
    name = name or "quant.log"
    logger = logging.getLogger()
    logger.setLevel(level)
    if console:
        print("init logger ...")
        handler = logging.StreamHandler()
    else:
        if clear and os.path.isdir(path):
            shutil.rmtree(path)
        if not os.path.isdir(path):
            os.makedirs(path)
        logfile = os.path.join(path, name)
        handler = TimedRotatingFileHandler(logfile, "midnight", backupCount=backup_count)
        print("init logger ...", logfile)
    fmt_str = "%(levelname)1.1s [%(asctime)s] %(message)s"
    fmt = logging.Formatter(fmt=fmt_str, datefmt=None)
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    initialized = True


def info(*args, **kwargs):
    func_name, kwargs = _log_msg_header(*args, **kwargs)
    logging.info(_log(func_name, *args, **kwargs))


def warn(*args, **kwargs):
    msg_header, kwargs = _log_msg_header(*args, **kwargs)
    logging.warning(_log(msg_header, *args, **kwargs))


def debug(*args, **kwargs):
    msg_header, kwargs = _log_msg_header(*args, **kwargs)
    logging.debug(_log(msg_header, *args, **kwargs))


def error(*args, **kwargs):
    logging.error("*" * 60)
    msg_header, kwargs = _log_msg_header(*args, **kwargs)
    logging.error(_log(msg_header, *args, **kwargs))
    logging.error("*" * 60)


def exception(*args, **kwargs):
    logging.error("*" * 60)
    msg_header, kwargs = _log_msg_header(*args, **kwargs)
    logging.error(_log(msg_header, *args, **kwargs))
    logging.error(traceback.format_exc())
    logging.error("*" * 60)


def _log(msg_header, *args, **kwargs):
    _log_msg = msg_header
    for l in args:
        if type(l) == tuple:
            ps = str(l)
        else:
            try:
                ps = "%r" % l
            except:
                ps = str(l)
        if type(l) == str:
            _log_msg += ps[1:-1] + " "
        else:
            _log_msg += ps + " "
    if len(kwargs) > 0:
        _log_msg += str(kwargs)
    return _log_msg


def _log_msg_header(*args, **kwargs):
    """Fetch log message header.

    NOTE:
        logger.xxx(... , caller=self) for instance method.
        logger.xxx(... , caller=cls) for class method.
    """
    cls_name = ""
    func_name = sys._getframe().f_back.f_back.f_code.co_name
    session_id = "-"
    try:
        _caller = kwargs.get("caller", None)
        if _caller:
            if not hasattr(_caller, "__name__"):
                _caller = _caller.__class__
            cls_name = _caller.__name__
            del kwargs["caller"]
    except:
        pass
    finally:
        msg_header = "[{session_id}] [{cls_name}.{func_name}] ".format(cls_name=cls_name, func_name=func_name,
                                                                       session_id=session_id)
        return msg_header, kwargs
