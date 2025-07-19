import re


def is_foreign_number(contact):
    if not contact:
        return False
    contact_clean = re.sub(r'[^\d+]', '', contact)
    if contact_clean.startswith('0') or contact_clean.startswith('+61'):
        return False
    if re.match(r'^\d{8}$', contact_clean):
        return False
    return True