# -*- coding:utf-8 -*-

from distutils.core import setup


setup(
    name="aioquant",
    version="1.2.0",
    packages=[
        "aioquant",
        "aioquant.utils",
        "aioquant.platform",
        "aioquant.markets",
    ],
    description="Asynchronous event I/O driven quantitative trading framework.",
    url="https://github.com:paulran/aioquant",
    author="PaulRan",
    author_email="xiaomaoln@gmail.com",
    license="MIT",
    keywords=[
        "aioquant", "quant", "framework", "async", "asynchronous", "digiccy", "digital", "currency", "marketmaker",
        "binance", "okex", "huobi", "bitmex", "deribit", "kraken", "gemini", "kucoin"
    ],
    install_requires=[
        "aiohttp",
        "aioamqp"
    ],
)
