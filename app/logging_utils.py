import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class DetailedFormatter(logging.Formatter):
    def format(self, record):
        log_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        level_color = Colors.OKBLUE
        if record.levelno >= logging.ERROR:
            level_color = Colors.FAIL
        elif record.levelno >= logging.WARNING:
            level_color = Colors.WARNING
        elif record.levelno <= logging.DEBUG:
            level_color = Colors.OKCYAN

        prefix = f"{Colors.BOLD}{log_time}{Colors.ENDC} | {level_color}{record.levelname:<8}{Colors.ENDC} | {Colors.HEADER}{record.name}{Colors.ENDC}"
        
        message = record.getMessage()
        
        # If message is valid JSON, pretty print it
        try:
            if message.startswith('{') or message.startswith('['):
                parsed = json.loads(message)
                message = "\n" + json.dumps(parsed, indent=2)
        except:
            pass

        return f"{prefix} -> {message}"

def setup_logger(name: str):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(DetailedFormatter())
        logger.addHandler(handler)
    
    return logger

# Global loggers
logger = setup_logger("NeuralNexusV2")
db_logger = setup_logger("Database")
ai_logger = setup_logger("AIService")
