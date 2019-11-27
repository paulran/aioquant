# -*- coding:utf-8 -*-

"""
Error Message.

Author: HuangTao
Date:   2018/05/17
Email:  huangtao@ifclover.com
"""


class Error:

    def __init__(self, msg):
        self._msg = msg

    @property
    def msg(self):
        return self._msg

    def __str__(self):
        return str(self._msg)

    def __repr__(self):
        return str(self)
