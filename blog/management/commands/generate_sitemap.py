from django.core.management.base import BaseCommand
from django.conf import settings
from datetime import datetime
import pytz
import os

BASE_URL = "https://easygoshuttle.com.au"


def _write_urlset(urls, path, today):
    content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n\n'
    for url in urls:
        lastmod = url.get("lastmod", today)
        content += '  <url>\n'
        content += f'    <loc>{url["loc"]}</loc>\n'
        content += f'    <lastmod>{lastmod}</lastmod>\n'
        content += f'    <changefreq>{url["changefreq"]}</changefreq>\n'
        content += f'    <priority>{url["priority"]}</priority>\n'
        content += '  </url>\n\n'
    content += '</urlset>'
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def _write_index(sitemaps, path):
    content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    content += '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n\n'
    for sm in sitemaps:
        content += '  <sitemap>\n'
        content += f'    <loc>{sm["loc"]}</loc>\n'
        content += f'    <lastmod>{sm["lastmod"]}</lastmod>\n'
        content += '  </sitemap>\n\n'
    content += '</sitemapindex>'
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


class Command(BaseCommand):
    help = "Generate sitemap index + per-region sub-sitemaps"

    def handle(self, *args, **options):
        sydney_tz = pytz.timezone("Australia/Sydney")
        today = datetime.now(sydney_tz).strftime("%Y-%m-%dT00:00:00+11:00")
        base_dir = settings.BASE_DIR
        index_entries = []

        # ── 1. sitemap-static.xml ────────────────────────────────────────
        static_urls = [
            {"loc": f"{BASE_URL}/",                          "changefreq": "daily",   "priority": "1.0000"},
            {"loc": f"{BASE_URL}/sydney_airport_transfer/",  "changefreq": "weekly",  "priority": "0.9000"},
            {"loc": f"{BASE_URL}/sydney-cruise-transfer/",   "changefreq": "weekly",  "priority": "0.9000"},
            {"loc": f"{BASE_URL}/sydney_airport_shuttle/",   "changefreq": "weekly",  "priority": "0.9000"},
            {"loc": f"{BASE_URL}/maxi-taxi/",                "changefreq": "weekly",  "priority": "0.9000"},
            {"loc": f"{BASE_URL}/inquiry/",                  "changefreq": "weekly",  "priority": "0.8000"},
            {"loc": f"{BASE_URL}/cruise_inquiry/",           "changefreq": "weekly",  "priority": "0.7000"},
            {"loc": f"{BASE_URL}/about_us/",                 "changefreq": "monthly", "priority": "0.7000"},
            {"loc": f"{BASE_URL}/easygo_review/",            "changefreq": "weekly",  "priority": "0.7000"},
            {"loc": f"{BASE_URL}/articles/blog/",            "changefreq": "daily",   "priority": "0.7000"},
            {"loc": f"{BASE_URL}/information/",              "changefreq": "monthly", "priority": "0.6000"},
            {"loc": f"{BASE_URL}/meeting_point/",            "changefreq": "monthly", "priority": "0.6000"},
            {"loc": f"{BASE_URL}/arrival_guide/",            "changefreq": "monthly", "priority": "0.6000"},
            {"loc": f"{BASE_URL}/more_suburbs/",             "changefreq": "weekly",  "priority": "0.6000"},
            {"loc": f"{BASE_URL}/more_suburbs_maxi_taxi/",   "changefreq": "weekly",  "priority": "0.6000"},
            {"loc": f"{BASE_URL}/payment_options/",          "changefreq": "monthly", "priority": "0.5000"},
            {"loc": f"{BASE_URL}/payonline/",                "changefreq": "monthly", "priority": "0.5000"},
            {"loc": f"{BASE_URL}/payment_options1/",         "changefreq": "monthly", "priority": "0.5000"},
            {"loc": f"{BASE_URL}/terms/",                    "changefreq": "yearly",  "priority": "0.3000"},
            {"loc": f"{BASE_URL}/privacy/",                  "changefreq": "yearly",  "priority": "0.3000"},
        ]
        _write_urlset(static_urls, os.path.join(base_dir, "sitemap-static.xml"), today)
        index_entries.append({"loc": f"{BASE_URL}/sitemap-static.xml", "lastmod": today})
        self.stdout.write(f"  sitemap-static.xml  — {len(static_urls)} URLs")

        # ── 2. sitemap-sydney.xml ────────────────────────────────────────
        sydney_urls = []
        try:
            from regions.models import RegionSuburb
            sydney_suburbs = RegionSuburb.objects.filter(
                is_active=True, region__slug='sydney'
            ).order_by('slug')
            for suburb in sydney_suburbs:
                sydney_urls.append({
                    "loc": f"{BASE_URL}/sydney/airport-shuttle/{suburb.slug}/",
                    "changefreq": "weekly",
                    "priority": "0.8000",
                })
                sydney_urls.append({
                    "loc": f"{BASE_URL}/sydney/airport-transfer/{suburb.slug}/",
                    "changefreq": "weekly",
                    "priority": "0.8000",
                })
                sydney_urls.append({
                    "loc": f"{BASE_URL}/maxi-taxi/{suburb.slug}/",
                    "changefreq": "weekly",
                    "priority": "0.8000",
                })
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Sydney suburbs error: {e}"))
        _write_urlset(sydney_urls, os.path.join(base_dir, "sitemap-sydney.xml"), today)
        index_entries.append({"loc": f"{BASE_URL}/sitemap-sydney.xml", "lastmod": today})
        self.stdout.write(f"  sitemap-sydney.xml  — {len(sydney_urls)} URLs")

        # ── 3. sitemap-{region}.xml per active region ────────────────────
        from regions.models import Region, RegionSuburb
        regions = Region.objects.filter(
            is_active=True, is_coming_soon=False
        ).exclude(slug='sydney').order_by('slug')

        for region in regions:
            try:
                region_urls = []

                # 지역 홈
                region_urls.append({
                    "loc": f"{BASE_URL}/{region.slug}/",
                    "changefreq": "weekly",
                    "priority": "0.9000",
                })
                # pillar 페이지
                for pillar in ('airport-shuttle', 'airport-transfer', 'cruise-transfer', 'maxi-taxi'):
                    region_urls.append({
                        "loc": f"{BASE_URL}/{region.slug}/{pillar}/",
                        "changefreq": "weekly",
                        "priority": "0.8000",
                    })
                # 서브 페이지
                for subpage in ('meeting-point', 'arrival-guide'):
                    region_urls.append({
                        "loc": f"{BASE_URL}/{region.slug}/{subpage}/",
                        "changefreq": "monthly",
                        "priority": "0.6000",
                    })
                # suburb 페이지 (shuttle + transfer)
                suburbs = RegionSuburb.objects.filter(
                    region=region, is_active=True
                ).order_by('slug')
                for suburb in suburbs:
                    region_urls.append({
                        "loc": f"{BASE_URL}/{region.slug}/airport-shuttle/{suburb.slug}/",
                        "changefreq": "weekly",
                        "priority": "0.8000",
                    })
                    region_urls.append({
                        "loc": f"{BASE_URL}/{region.slug}/airport-transfer/{suburb.slug}/",
                        "changefreq": "weekly",
                        "priority": "0.8000",
                    })

                filename = f"sitemap-{region.slug}.xml"
                _write_urlset(region_urls, os.path.join(base_dir, filename), today)
                index_entries.append({"loc": f"{BASE_URL}/{filename}", "lastmod": today})
                self.stdout.write(f"  {filename}  — {len(region_urls)} URLs ({suburbs.count()} suburbs × 2 + pages)")

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  {region.slug} sitemap error: {e}"))

        # ── 4. sitemap-blog.xml ──────────────────────────────────────────
        blog_urls = []
        blog_lastmod = today
        try:
            from articles.models import Post
            posts = Post.objects.filter(status='published').only('slug', 'published_at', 'updated_at').order_by('-updated_at')
            for post in posts:
                lastmod_dt = post.updated_at or post.published_at
                lastmod = lastmod_dt.astimezone(sydney_tz).strftime("%Y-%m-%dT%H:%M:%S+11:00") if lastmod_dt else today
                blog_urls.append({
                    "loc": f"{BASE_URL}/articles/blog/{post.slug}/",
                    "changefreq": "weekly",
                    "priority": "0.6000",
                    "lastmod": lastmod,
                })
            if blog_urls:
                blog_lastmod = blog_urls[0]["lastmod"]
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Blog sitemap error: {e}"))
        _write_urlset(blog_urls, os.path.join(base_dir, "sitemap-blog.xml"), today)
        index_entries.append({"loc": f"{BASE_URL}/sitemap-blog.xml", "lastmod": blog_lastmod})
        self.stdout.write(f"  sitemap-blog.xml    — {len(blog_urls)} URLs")

        # ── 5. sitemap.xml (index) ───────────────────────────────────────
        _write_index(index_entries, os.path.join(base_dir, "sitemap.xml"))
        self.stdout.write(self.style.SUCCESS(
            f"\nsitemap.xml (index) generated — {len(index_entries)} sub-sitemaps"
        ))
