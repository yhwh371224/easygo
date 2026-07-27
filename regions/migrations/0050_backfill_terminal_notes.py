from django.db import migrations

# Carries over the descriptive copy that used to live in the legacy
# Region.terminal_info JSON blob, now that the meeting-point page reads
# from the Terminal model instead.
NOTES = {
    'sydney': {
        'T1 International': "After clearing customs, exit into the Arrivals Hall. Your EasyGo driver will meet you at the designated pick-up area outside the terminal.",
        'T2 Domestic': "After collecting your baggage, exit through the main Arrivals doors. Your driver will meet you at the designated passenger pick-up area.",
        'T3 Qantas Domestic': "After collecting your baggage, proceed outside the terminal to the passenger pick-up area. Your EasyGo driver will meet you there.",
    },
    'melbourne': {
        'T1 Domestic (Qantas)': "Collect your baggage and exit through the main Arrivals door. Your driver meets you on the kerbside directly outside baggage claim.",
        'T2 International': "Arrivals at Level 2 (Ground Level). After clearing customs, exit through the sliding doors into the Arrivals Hall. Your EasyGo driver will be waiting with a name board near the exit.",
        'T3 Domestic (Virgin)': "Connected to T2 via a short walkway. Exit at Ground Level. Your driver meets you at the main kerbside exit.",
        'T4 Domestic (Jetstar, Rex)': "Separate terminal on Departure Drive. After collecting baggage, exit through the main doors. Driver meets you on the pick-up kerbside.",
    },
    'brisbane': {
        'Brisbane International': "After clearing customs, exit into the Arrivals Hall. Your EasyGo driver will meet you at the designated passenger pick-up area outside the terminal.",
        'Brisbane Domestic Airport': "After collecting your baggage, exit through the main Arrivals doors. Your EasyGo driver will meet you at the designated passenger pick-up area.",
    },
    'gold-coast': {
        'Gold Coast Domestic Airport': "After collecting your baggage, proceed to the passenger pick-up area outside the terminal. Your EasyGo driver will meet you there.",
        "Gold Coast Int'l Airport": "After collecting your baggage, proceed to the passenger pick-up area outside the terminal. Your EasyGo driver will meet you there.",
    },
}


def backfill_notes(apps, schema_editor):
    Terminal = apps.get_model('regions', 'Terminal')
    for region_slug, by_name in NOTES.items():
        for terminal_name, note in by_name.items():
            Terminal.objects.filter(
                airport__regions__slug=region_slug,
                name=terminal_name,
                note='',
            ).update(note=note)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('regions', '0049_fix_meta_title_transfer_first'),
    ]

    operations = [
        migrations.RunPython(backfill_notes, noop),
    ]
