import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage

# Driver ID/licence scans are sensitive PII. Kept outside MEDIA_ROOT so they
# are never reachable under /media/ (which the web server may serve directly,
# bypassing Django auth) — only the staff-only admin view in
# blog/admin.py (DriverAdmin.license_scan_view) can read them back.
private_driver_docs_storage = FileSystemStorage(
    location=os.path.join(settings.BASE_DIR, 'private_media', 'driver_docs'),
    base_url=None,
)
