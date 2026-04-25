from django.core.management.base import BaseCommand
from django.conf import settings
from datetime import datetime
import pytz
import os


class Command(BaseCommand):
    help = "Generate Sydney time sitemap.xml"

    def handle(self, *args, **options):
        sydney_tz = pytz.timezone("Australia/Sydney")
        today_sydney = datetime.now(sydney_tz).strftime("%Y-%m-%dT00:00:00+11:00")

        # 정적 URL 목록
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
            {"loc": "https://easygoshuttle.com.au/blog/", "changefreq": "daily", "priority": "0.7000"},
            {"loc": "https://easygoshuttle.com.au/information/", "changefreq": "monthly", "priority": "0.6000"},
            {"loc": "https://easygoshuttle.com.au/meeting_point/", "changefreq": "monthly", "priority": "0.6000"},
            {"loc": "https://easygoshuttle.com.au/arrival_guide/", "changefreq": "monthly", "priority": "0.6000"},
            {"loc": "https://easygoshuttle.com.au/more_suburbs/", "changefreq": "weekly", "priority": "0.6000"},
            {"loc": "https://easygoshuttle.com.au/more_suburbs_maxi_taxi/", "changefreq": "weekly", "priority": "0.6000"},
            {"loc": "https://easygoshuttle.com.au/more_suburbs1/", "changefreq": "weekly", "priority": "0.6000"},
            {"loc": "https://easygoshuttle.com.au/payment_options/", "changefreq": "monthly", "priority": "0.5000"},
            {"loc": "https://easygoshuttle.com.au/payonline/", "changefreq": "monthly", "priority": "0.5000"},
            {"loc": "https://easygoshuttle.com.au/payment_options1/", "changefreq": "monthly", "priority": "0.5000"},
            {"loc": "https://easygoshuttle.com.au/terms/", "changefreq": "yearly", "priority": "0.3000"},
            {"loc": "https://easygoshuttle.com.au/privacy/", "changefreq": "yearly", "priority": "0.3000"},
        ]

        # 지역 페이지 동적 추가 (sydney 제외)
        try:
            from regions.models import Region, RegionSuburb
            regions = Region.objects.filter(is_active=True).exclude(slug='sydney')
            for region in regions:
                urls.append({
                    "loc": f"https://easygoshuttle.com.au/{region.slug}/",
                    "changefreq": "weekly",
                    "priority": "0.9000",
                })
            self.stdout.write(f"  Added {regions.count()} region pages to sitemap.")

            suburbs = RegionSuburb.objects.filter(
                is_active=True
            ).exclude(region__slug='sydney').select_related('region')
            for suburb in suburbs:
                urls.append({
                    "loc": f"https://easygoshuttle.com.au/{suburb.region.slug}/airport-shuttle/{suburb.slug}/",
                    "changefreq": "weekly",
                    "priority": "0.8000",
                })
            self.stdout.write(f"  Added {suburbs.count()} suburb pages to sitemap.")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Could not load region/suburb pages: {e}"))

        # 블로그 글 동적 추가
        try:
            from articles.models import Post
            posts = Post.objects.filter(status='published').only('slug', 'published_at', 'updated_at')
            for post in posts:
                # 수정일이 있으면 수정일, 없으면 발행일 사용
                lastmod_dt = post.updated_at or post.published_at
                if lastmod_dt:
                    lastmod = lastmod_dt.astimezone(sydney_tz).strftime("%Y-%m-%dT%H:%M:%S+11:00")
                else:
                    lastmod = today_sydney
                urls.append({
                    "loc": f"https://easygoshuttle.com.au/blog/{post.slug}/",
                    "changefreq": "weekly",
                    "priority": "0.6000",
                    "lastmod": lastmod,
                })
            self.stdout.write(f"  Added {posts.count()} blog posts to sitemap.")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Could not load blog posts: {e}"))

        # 사이트맵 생성
        sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n\n'
        sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n\n'

        for url in urls:
            lastmod = url.get("lastmod", today_sydney)
            sitemap += f'  <url>\n'
            sitemap += f'       <loc>{url["loc"]}</loc>\n'
            sitemap += f'       <lastmod>{lastmod}</lastmod>\n'
            sitemap += f'       <changefreq>{url["changefreq"]}</changefreq>\n'
            sitemap += f'       <priority>{url["priority"]}</priority>\n'
            sitemap += f'  </url>\n\n'

        sitemap += '</urlset>'

        output_path = os.path.join(settings.BASE_DIR, "sitemap.xml")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(sitemap)

        self.stdout.write(self.style.SUCCESS(f"sitemap.xml generated. Date: {today_sydney}"))