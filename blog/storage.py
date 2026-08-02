import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage


# Driver ID/licence scans are sensitive PII. Kept outside MEDIA_ROOT so they
# are never reachable under /media/ (which the web server may serve directly,
# bypassing Django auth) — only the staff-only admin view in
# blog/admin.py (DriverAdmin.license_scan_view) can read them back.
#
# This is a callable, not a FileSystemStorage instance, on purpose: FileField
# deconstructs a storage *instance* by value, baking location=<absolute path>
# into the migration. BASE_DIR differs per machine (/home/sung vs /home/horeb),
# so every makemigrations on a different host emitted another AlterField —
# 0069, 0070, 0073 are all that same no-op churn, and the duplicates collided
# at deploy time. A callable is deconstructed by reference, so the path stays
# out of migrations. Django evaluates it once when the model is loaded.
def private_driver_docs_storage():
    return FileSystemStorage(
        location=os.path.join(settings.BASE_DIR, 'private_media', 'driver_docs'),
        base_url=None,
    )
