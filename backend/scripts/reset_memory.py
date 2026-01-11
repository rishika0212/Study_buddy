import shutil
import os
import sys
# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.config import settings
from backend.app.utils.logger import logger

def reset_all_memory():
    logger.info("Resetting all user memory and summaries...")
    if os.path.exists(settings.USER_DATA_DIRECTORY):
        shutil.rmtree(settings.USER_DATA_DIRECTORY)
        os.makedirs(settings.USER_DATA_DIRECTORY)
        logger.info("Memory reset completed.")
    else:
        logger.info("No memory directory found.")

if __name__ == "__main__":
    reset_all_memory()
