import logging
import pathlib

from logging.handlers import RotatingFileHandler


def log_setup(logfile_name="maginkcal.log", log_level=logging.INFO):
    log_path = pathlib.Path(f"{pathlib.Path(__file__).parent.parent.absolute()}/logs/{logfile_name}")
    log_path.touch(exist_ok=True)

    log_handler = RotatingFileHandler(log_path, mode='a', maxBytes=5*1024*1024, backupCount=1, encoding=None, delay=0)
    formatter = logging.Formatter("%(asctime)s %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S")
    log_handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.addHandler(log_handler)
    logger.setLevel(log_level)
