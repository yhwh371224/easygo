import os
import string
import random
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Generate random passwords for predefined email prefixes and save to secure/password.txt'

    def handle(self, *args, **kwargs):
        
        # 이메일 접두사 리스트
        names = [
            "info@",
            "sungkam3@",
            "junghee@",
            "commbank",
            "nab",
            "westpac",
            "coinspot",
            "paypal",
            "stripe",
            "ozlotto",
            "github",
            "mysql",
            "vultr",
            "crazy",
            "cloudfare",
        ]

        if len(names) != 15:
            self.stdout.write(self.style.ERROR("⚠️  이름 리스트가 정확히 15개인지 확인하세요."))
            return

        # 패스워드 생성 함수
        def generate_password(length=16):
            chars = string.ascii_letters + string.digits + string.punctuation
            return ''.join(random.choice(chars) for _ in range(length))

        # secure 폴더 설정
        project_root = settings.BASE_DIR if hasattr(settings, 'BASE_DIR') else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        secure_folder = os.path.join(project_root, 'secure')
        os.makedirs(secure_folder, exist_ok=True)
        file_path = os.path.join(secure_folder, 'password.txt')

        # 패스워드 생성 및 저장
        with open(file_path, 'w') as f:
            for name in names:
                password = generate_password()
                f.write(f"{name.ljust(15)} :  {password}\n")

        self.stdout.write(self.style.SUCCESS(f'✅  15개의 패스워드가 {file_path}에 저장되었습니다.'))
