import os
from celery import shared_task


# Verse image 생성 작업
@shared_task
def create_verse_image_task(verse_text, uploaded_image_path=None):
    try:
        from easygo_review.utils.verse_image import create_verse_image 
        create_verse_image(verse_text, uploaded_image_path)
    except Exception as e:
        print(f"Verse image task error: {e}")
    finally:
        # 임시 파일 삭제.
        if uploaded_image_path and os.path.exists(uploaded_image_path):
            try:
                os.remove(uploaded_image_path)
                # temp 폴더가 비어 있으면 삭제
                temp_dir = os.path.dirname(uploaded_image_path)
                if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                    os.rmdir(temp_dir)
            except Exception as e:
                print(f"Error deleting temp file: {e}")