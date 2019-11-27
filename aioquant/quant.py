# -*- coding:utf-8 -*-

"""
Asynchronous event I/O driven quantitative trading framework.

Author: HuangTao
Date:   2017/04/26
Email:  huangtao@ifclover.com
"""

import signal
import asyncio
import inspect

from aioquant.utils import logger
from aioquant.configure import config


class AIOQuant:
    """Asynchronous event I/O driven quantitative trading framework.
    """

    def __init__(self) -> None:
        self.loop = None
        self.event_center = None

    def _initialize(self, config_file):
        """Initialize."""
        self._get_event_loop()
        self._load_settings(config_file)
        self._init_logger()
        self._init_event_center()
        self._do_heartbeat()
        return self

    def start(self, config_file=None, entrance_func=None) -> None:
        """Start the event loop."""
        def keyboard_interrupt(s, f):
            print("KeyboardInterrupt (ID: {}) has been caught. Cleaning up...".format(s))
            self.stop()
        signal.signal(signal.SIGINT, keyboard_interrupt)

        self._initialize(config_file)
        if entrance_func:
            if inspect.iscoroutinefunction(entrance_func):
                self.loop.create_task(entrance_func())
            else:
                entrance_func()

        logger.info("start io loop ...", caller=self)
        self.loop.run_forever()

    def stop(self) -> None:
        """Stop the event loop."""
        logger.info("stop io loop.", caller=self)
        # TODO: clean up running coroutine
        self.loop.stop()

    def _get_event_loop(self) -> asyncio.events.get_event_loop():
        """Get a main io loop."""
        if not self.loop:
            self.loop = asyncio.get_event_loop()
        return self.loop

    def _load_settings(self, config_module) -> None:
        """Load config settings.

        Args:
            config_module: config file path, normally it's a json file.
        """
        config.loads(config_module)

    def _init_logger(self) -> None:
        """Initialize logger."""
        logger.initLogger(**config.log)

    def _init_event_center(self) -> None:
        """Initialize event center."""
        if not config.rabbitmq:
            return
        from aioquant.event import EventCenter
        self.event_center = EventCenter()

    def _do_heartbeat(self) -> None:
        """Start server heartbeat."""
        from aioquant.heartbeat import heartbeat
        self.loop.call_later(0.5, heartbeat.ticker)
