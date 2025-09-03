import os, logging
from datetime import datetime, UTC
from discord.utils import setup_logging

import config

LOGGING_LEVEL = logging.INFO

# Move old log and timestamp
if not os.path.exists(config.LOG_FOLDER): os.mkdir(f"./{config.LOG_FOLDER}")
if os.path.exists(config.LOG_PATH): os.rename(config.LOG_PATH, f"{config.LOG_FOLDER}/{datetime.now(UTC).strftime('%Y-%m-%d_%H-%M-%S_hornet.log')}")
# Setup logging
filehandler = logging.FileHandler(filename=config.LOG_PATH, encoding="utf-8", mode="w")
filehandler.setFormatter(logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', '%Y-%m-%d %H:%M:%S', style='{'))
logging.getLogger().addHandler(filehandler)  # file log
logging.getLogger().handlers

setup_logging(level=LOGGING_LEVEL)  # add stream to stderr & set for discord.py
