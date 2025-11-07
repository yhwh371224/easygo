import os
from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task
def create_verse_image_task(verse_text, uploaded_image_path=None):
    try:
        from easygo_review.utils.verse_image import create_verse_image 
        file_name = create_verse_image(verse_text, uploaded_image_path)
        logger.info(f"Verse image created: {file_name}")
        return file_name
    except Exception as e:
        logger.error(f"Verse image task error: {e}", exc_info=True)
        return None
    finally:
        # 임시 파일 삭제
        if uploaded_image_path and os.path.exists(uploaded_image_path):
            try:
                os.remove(uploaded_image_path)
                temp_dir = os.path.dirname(uploaded_image_path)
                if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                    os.rmdir(temp_dir)
            except Exception as e:
                logger.warning(f"Error deleting temp file: {e}", exc_info=True)
