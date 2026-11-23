from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from blog.models import Inquiry, Post


class AdminSearchByIdTests(TestCase):
    """Admin search box: a plain number also finds the Inquiry / Post with that ID."""

    def setUp(self):
        self.admin = User.objects.create_superuser('boss', 'boss@example.com', 'pw-123456')
        self.client.force_login(self.admin)

    def _search(self, model, term):
        url = reverse(f'admin:blog_{model}_changelist')
        r = self.client.get(url, {'q': term}, secure=True)
        self.assertEqual(r.status_code, 200)
        return [o.pk for o in r.context['cl'].result_list]

    def test_inquiry_found_by_id(self):
        a = Inquiry.objects.create(name='Alice', email='alice@example.com')
        Inquiry.objects.create(name='Bob', email='bob@example.com')
        self.assertEqual(self._search('inquiry', str(a.pk)), [a.pk])
        self.assertEqual(self._search('inquiry', f'#{a.pk}'), [a.pk])

    def test_inquiry_name_search_still_works(self):
        a = Inquiry.objects.create(name='Alice', email='alice@example.com')
        Inquiry.objects.create(name='Bob', email='bob@example.com')
        self.assertEqual(self._search('inquiry', 'alice'), [a.pk])

    def test_post_found_by_id(self):
        p = Post.objects.create(name='Carol', email='carol@example.com', price='99')
        Post.objects.create(name='Dave', email='dave@example.com', price='120')
        self.assertIn(p.pk, self._search('post', str(p.pk)))
