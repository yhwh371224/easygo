from django.core.management.base import BaseCommand
from django.conf import settings
from google_auth_oauthlib.flow import InstalledAppFlow
import json

SCOPES = [
    'https://www.googleapis.com/auth/business.manage'
]


class Command(BaseCommand):
    help = 'Authenticate Google My Business OAuth2 (run once)'

    def handle(self, *args, **options):
        flow = InstalledAppFlow.from_client_secrets_file(
            settings.GMB_OAUTH_CLIENT_FILE,
            scopes=SCOPES
        )

        creds = flow.run_local_server(port=0)

        # 토큰 저장
        with open(settings.GMB_TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())

        self.stdout.write(self.style.SUCCESS(
            f"✅ OAuth 인증 완료! 토큰 저장됨: {settings.GMB_TOKEN_FILE}"
        ))