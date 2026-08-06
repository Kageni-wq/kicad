import logging
from datetime import datetime
from pathlib import Path

class Logger():
    def __init__(self, dir: Path):
        self.log_dir = dir
        self.logger = None
    
    def setup_logger(self):
        self.logger = logging.getLogger('log')
        self.logger.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s : %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        log_file = self.log_dir / "logs" / f"{datetime.now().strftime('%Y%m%d %H%M%S')}.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        if self.logger.handlers:
            self.logger.handlers.clear()
            
        self.logger.addHandler(file_handler)

    def _debug(self, msg: str):
        self.logger.debug(msg=msg)

    def _info(self, msg: str):
        self.logger.info(msg=msg)

    def _warning(self, msg: str):
        self.logger.warning(msg=msg)

    def _error(self, msg: str):
        self.logger.error(msg=msg)
