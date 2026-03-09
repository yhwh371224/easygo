from django.core.management.base import BaseCommand
from django.conf import settings
from datetime import datetime
import pytz
import os

class Command(BaseCommand):
    help = "Generate Sydney time sitemap.xml"

    def handle(self, *args, **options):
        # Sydney 시간대 설정
        sydney_tz = pytz.timezone("Australia/Sydney")
        today_sydney = datetime.now(sydney_tz).strftime("%Y-%m-%dT00:00:00+11:00")

        # 사이트맵 URL 목록
        urls = [
            {"loc": "https://easygoshuttle.com.au/", "changefreq": "daily", "priority": "1.0000"},
            {"loc": "https://easygoshuttle.com.au/sydney-airport-transfer/", "changefreq": "weekly", "priority": "0.9000"},
            {"loc": "https://easygoshuttle.com.au/sydney-cruise-transfer/", "changefreq": "weekly", "priority": "0.9000"},
            {"loc": "https://easygoshuttle.com.au/sydney-airport-shuttle/", "changefreq": "weekly", "priority": "0.9000"},
            {"loc": "https://easygoshuttle.com.au/maxi-taxi/", "changefreq": "weekly", "priority": "0.9000"},
            {"loc": "https://easygoshuttle.com.au/booking/", "changefreq": "weekly", "priority": "0.8000"},
            {"loc": "https://easygoshuttle.com.au/inquiry/", "changefreq": "weekly", "priority": "0.8000"},
            {"loc": "https://easygoshuttle.com.au/cruise_inquiry/", "changefreq": "weekly", "priority": "0.7000"},
            {"loc": "https://easygoshuttle.com.au/about_us/", "changefreq": "monthly", "priority": "0.7000"},
            {"loc": "https://easygoshuttle.com.au/easygo_review/", "changefreq": "weekly", "priority": "0.7000"},
            {"loc": "https://easygoshuttle.com.au/information/", "changefreq": "monthly", "priority": "0.6000"},
            {"loc": "https://easygoshuttle.com.au/meeting_point/", "changefreq": "monthly", "priority": "0.6000"},
            {"loc": "https://easygoshuttle.com.au/arrival_guide/", "changefreq": "monthly", "priority": "0.6000"},
            {"loc": "https://easygoshuttle.com.au/layouts/more_suburbs/", "changefreq": "weekly", "priority": "0.6000"},
            {"loc": "https://easygoshuttle.com.au/layouts/more_suburbs_maxi_taxi/", "changefreq": "weekly", "priority": "0.6000"},
            {"loc": "https://easygoshuttle.com.au/layouts/more_suburbs1/", "changefreq": "weekly", "priority": "0.6000"},
            {"loc": "https://easygoshuttle.com.au/payment_options/", "changefreq": "monthly", "priority": "0.5000"},
            {"loc": "https://easygoshuttle.com.au/payonline/", "changefreq": "monthly", "priority": "0.5000"},
            {"loc": "https://easygoshuttle.com.au/payment_options1/", "changefreq": "monthly", "priority": "0.5000"},
            {"loc": "https://easygoshuttle.com.au/terms/", "changefreq": "yearly", "priority": "0.3000"},
            {"loc": "https://easygoshuttle.com.au/privacy/", "changefreq": "yearly", "priority": "0.3000"},
        ]

        # 사이트맵 생성
        sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n\n'
        sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n\n'

        for url in urls:
            sitemap += f'  <url>\n'
            sitemap += f'       <loc>{url["loc"]}</loc>\n'
            sitemap += f'       <lastmod>{today_sydney}</lastmod>\n'
            sitemap += f'       <changefreq>{url["changefreq"]}</changefreq>\n'
            sitemap += f'       <priority>{url["priority"]}</priority>\n'
            sitemap += f'  </url>\n\n'

        sitemap += '</urlset>'

        # 파일 저장 (프로젝트 루트 또는 원하는 경로)
        output_path = os.path.join(settings.BASE_DIR, "sitemap.xml")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(sitemap)

        self.stdout.write(self.style.SUCCESS(f"Sydney 시간 기준 sitemap.xml 파일이 생성되었습니다. 날짜: {today_sydney}"))