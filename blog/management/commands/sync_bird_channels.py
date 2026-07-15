"""Wire Bird numbers up to this app.

Buying a number in Bird is not enough: until its channels are recorded here and
Bird is told to deliver their events to our webhooks, anyone who dials it
reaches nothing — silently. That gap is what left a driver ringing a number no
call ever arrived from. This command closes it in one step, so adding a number
later is `buy in Bird → run this → assign in the admin`.

Read-only by default; pass --apply to write.
"""
import logging

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.urls import reverse

from blog.models import VirtualNumber

logger = logging.getLogger('bird_proxy')

BIRD_API_BASE = 'https://api.bird.com'

SMS_PLATFORM = 'sms-messagebird'
VOICE_PLATFORM = 'voice-messagebird'

PLATFORM_EVENTS = {
    SMS_PLATFORM: ('sms.inbound', 'bird_sms_webhook_channel'),
    VOICE_PLATFORM: ('voice.inbound', 'bird_voice_webhook_channel'),
}


class Command(BaseCommand):
    help = 'Record Bird channel ids on VirtualNumber and register their webhooks.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Actually write. Without it, only prints what would change.',
        )

    # -------------------------------------------------- Bird API
    def _headers(self):
        return {
            'Authorization': f'AccessKey {settings.BIRD_API_KEY}',
            'Content-Type': 'application/json',
        }

    def _get(self, path):
        resp = requests.get(f'{BIRD_API_BASE}{path}', headers=self._headers(), timeout=20)
        resp.raise_for_status()
        return resp.json().get('results', [])

    def _webhook_url(self, route_name, channel_id):
        path = reverse(route_name, kwargs={'channel_id': channel_id})
        return f'{settings.BIRD_WEBHOOK_BASE_URL}{path}'

    # -------------------------------------------------- steps
    def _sync_numbers(self, channels, apply):
        """Record every workspace number's channel ids, the shared company
        number included.

        Skipping the shared number used to look tidy — it is configured through
        settings, after all — but any VirtualNumber row for it could then never
        be wired, so the admin labelled our most-used number '(not wired)' and
        resolve_virtual_number() logged a false warning on every lookup. A
        number is a number; settings only decide which one is the fallback.
        """
        by_number = {}
        for channel in channels:
            identifier = channel.get('identifier')
            platform = channel.get('platformId')
            if not identifier or platform not in PLATFORM_EVENTS:
                continue
            by_number.setdefault(identifier, {})[platform] = channel['id']

        for number, platforms in sorted(by_number.items()):
            sms_id = platforms.get(SMS_PLATFORM)
            voice_id = platforms.get(VOICE_PLATFORM)

            if not sms_id or not voice_id:
                self.stdout.write(self.style.WARNING(
                    f'  {number}  INCOMPLETE — sms={bool(sms_id)} voice={bool(voice_id)}; '
                    f'stays unwired and will not be advertised'
                ))

            virtual_number, created = (
                VirtualNumber.objects.get_or_create(number=number)
                if apply else (VirtualNumber.objects.filter(number=number).first(), False)
            )

            if virtual_number is None:
                self.stdout.write(f'  {number}  would create VirtualNumber + set channels')
                continue

            changed = (
                virtual_number.sms_channel_id != sms_id
                or virtual_number.voice_channel_id != voice_id
            )
            if not changed:
                self.stdout.write(f'  {number}  already recorded')
                continue

            if apply:
                virtual_number.sms_channel_id = sms_id
                virtual_number.voice_channel_id = voice_id
                virtual_number.save(update_fields=['sms_channel_id', 'voice_channel_id'])
                verb = 'created' if created else 'updated'
                self.stdout.write(self.style.SUCCESS(f'  {number}  {verb} channels'))
            else:
                self.stdout.write(f'  {number}  would set sms={sms_id} voice={voice_id}')

    def _sync_subscriptions(self, channels, existing, apply):
        """One subscription per channel, pointed at that channel's own URL."""
        wanted = []
        for channel in channels:
            platform = channel.get('platformId')
            if platform not in PLATFORM_EVENTS:
                continue
            event, route_name = PLATFORM_EVENTS[platform]
            wanted.append((
                channel['id'],
                channel.get('identifier'),
                event,
                self._webhook_url(route_name, channel['id']),
            ))

        by_channel = {}
        for sub in existing:
            for f in sub.get('eventFilters') or []:
                if f.get('key') == 'channelId':
                    by_channel[(f.get('value'), sub.get('event'))] = sub

        for channel_id, number, event, url in sorted(wanted, key=lambda x: (x[1] or '', x[2])):
            current = by_channel.get((channel_id, event))

            if current and current.get('url') == url:
                self.stdout.write(f'  {number:<16} {event:<14} already subscribed')
                continue

            if not apply:
                action = (
                    f'would move {current.get("url")} → {url}' if current
                    else f'would create → {url}'
                )
                self.stdout.write(f'  {number:<16} {event:<14} {action}')
                continue

            if current:
                self._replace(current, channel_id, event, url, number)
            else:
                self._create(channel_id, event, url, number)

    def _payload(self, channel_id, event, url):
        payload = {
            'service': 'channels',
            'event': event,
            'url': url,
            'eventFilters': [{'key': 'channelId', 'value': channel_id}],
        }
        if settings.BIRD_WEBHOOK_SIGNING_KEY:
            payload['signingKey'] = settings.BIRD_WEBHOOK_SIGNING_KEY
        return payload

    def _create(self, channel_id, event, url, number):
        resp = requests.post(
            f'{BIRD_API_BASE}/workspaces/{settings.BIRD_WORKSPACE_ID}/webhook-subscriptions',
            json=self._payload(channel_id, event, url),
            headers=self._headers(),
            timeout=20,
        )
        if not resp.ok:
            self.stdout.write(self.style.ERROR(
                f'  {number:<16} {event:<14} FAILED {resp.status_code} {resp.text[:200]}'
            ))
            return
        self.stdout.write(self.style.SUCCESS(f'  {number:<16} {event:<14} subscribed'))

    def _replace(self, current, channel_id, event, url, number):
        """Bird has no update, so re-create. Delete last: a subscription pointing
        at the wrong URL still delivers, none at all drops calls on the floor."""
        resp = requests.post(
            f'{BIRD_API_BASE}/workspaces/{settings.BIRD_WORKSPACE_ID}/webhook-subscriptions',
            json=self._payload(channel_id, event, url),
            headers=self._headers(),
            timeout=20,
        )
        if not resp.ok:
            self.stdout.write(self.style.ERROR(
                f'  {number:<16} {event:<14} FAILED to re-create, old one left in place: '
                f'{resp.status_code} {resp.text[:200]}'
            ))
            return

        old = requests.delete(
            f'{BIRD_API_BASE}/workspaces/{settings.BIRD_WORKSPACE_ID}'
            f'/webhook-subscriptions/{current["id"]}',
            headers=self._headers(),
            timeout=20,
        )
        state = 'moved' if old.ok else f'moved (old {current["id"]} left behind)'
        self.stdout.write(self.style.SUCCESS(f'  {number:<16} {event:<14} {state}'))

    # -------------------------------------------------- entry
    def handle(self, *args, **options):
        apply = options['apply']
        ws = settings.BIRD_WORKSPACE_ID

        if not apply:
            self.stdout.write(self.style.WARNING('DRY RUN — nothing will be written. Use --apply.\n'))

        if not settings.BIRD_WEBHOOK_SIGNING_KEY:
            self.stdout.write(self.style.WARNING(
                'BIRD_WEBHOOK_SIGNING_KEY is unset: subscriptions will be created '
                'unsigned and the endpoints stay open to anyone.\n'
            ))

        channels = self._get(f'/workspaces/{ws}/channels')
        existing = self._get(f'/workspaces/{ws}/webhook-subscriptions')

        self.stdout.write(f'Bird workspace {ws}')
        self.stdout.write(f'  {len(channels)} channels, {len(existing)} webhook subscriptions')
        self.stdout.write(f'  webhook base: {settings.BIRD_WEBHOOK_BASE_URL}\n')

        self.stdout.write('Numbers:')
        self._sync_numbers(channels, apply)

        self.stdout.write('\nWebhook subscriptions:')
        self._sync_subscriptions(channels, existing, apply)

        if not apply:
            self.stdout.write(self.style.WARNING('\nDRY RUN — re-run with --apply to write.'))
