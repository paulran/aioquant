# -*- coding:utf-8 -*-

from distutils.core import setup


setup(
    name="aioquant",
    version="1.0.0",
    packages=[
        "aioquant",
        "aioquant.utils",
        "aioquant.platform",
    ],
    description="Asynchronous event I/O driven quantitative trading framework.",
    url="https://github.com/JiaoziMatrix/aioquant",
    author="HuangTao",
    author_email="huangtao@ifclover.com",
    license="MIT",
    keywords=[
        "aioquant", "quant", "framework", "async", "asynchronous", "digiccy", "digital", "currency", "marketmaker",
        "binance", "okex", "huobi", "bitmex", "deribit", "kraken", "gemini", "kucoin"
    ],
    install_requires=[
        "aiohttp==3.6.2",
        "aioamqp==0.13.0"
    ],
)
