"""픽업 2시간 전 드라이버 텔레그램 알림 / 확인 버튼 / 미확인 경고 / 연결 webhook."""
import datetime
import json
from datetime import timedelta
from unittest.mock import patch

import pytz
from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from blog.driver_reminder import ReminderRun
from blog.models import Driver, Post
from utils.telegram_driver import TelegramDriverError

SYD = pytz.timezone('Australia/Sydney')
BOT = dict(TELEGRAM_DRIVER_BOT_TOKEN='tok', TELEGRAM_DRIVER_BOT_USERNAME='EasyGoDriverBot',
           TELEGRAM_DRIVER_WEBHOOK_SECRET='s3cret')


def at(day, hhmm):
    h, m = map(int, hhmm.split(':'))
    return SYD.localize(datetime.datetime.combine(day, datetime.time(h, m)))


DAY = datetime.date(2026, 11, 20)


def make_driver(name='Alex', chat_id='111', **kw):
    return Driver.objects.create(driver_name=name, driver_contact='0400111222',
                                 telegram_chat_id=chat_id, **kw)


def make_post(driver, day=DAY, time='14:30', **kw):
    defaults = dict(name='Customer', email='c@example.com', no_of_passenger='2',
                    pickup_date=day, pickup_time=time, driver=driver,
                    direction='Pickup from Intl Airport', start_point='Sydney Airport T1',
                    end_point='Chatswood', flight_number='QF1', no_of_baggage='3')
    defaults.update(kw)
    return Post.objects.create(**defaults)


@override_settings(**BOT)
@patch('utils.telegram.send_telegram_sync')
@patch('utils.telegram_driver.send_message')
class ReminderRunTests(TestCase):

    def run_at(self, now):
        return ReminderRun(now_fn=lambda: now).run()

    def test_sends_two_hours_before_and_marks(self, send, staff):
        driver = make_driver()
        post = make_post(driver)

        self.run_at(at(DAY, '12:25'))
        send.assert_not_called()

        self.run_at(at(DAY, '12:31'))
        send.assert_called_once()
        chat_id, text, buttons = send.call_args[0]
        self.assertEqual(chat_id, '111')
        self.assertIn('#%d · Today 02:30 PM' % post.pk, text)
        self.assertIn('Sydney Airport T1 → Chatswood', text)
        self.assertNotIn('Customer', text)  # 고객 이름은 넣지 않는다
        self.assertEqual(buttons[0][0]['callback_data'], f'ack:{post.pk}')

        post.refresh_from_db()
        self.assertEqual(post.driver_reminder_sent_to_id, driver.pk)
        self.assertIsNotNone(post.driver_reminder_sent_at)

        self.run_at(at(DAY, '12:46'))
        send.assert_called_once()  # 중복 발송 없음

    def test_not_sent_after_pickup(self, send, staff):
        make_post(make_driver())
        self.run_at(at(DAY, '14:31'))
        send.assert_not_called()

    def test_cancelled_and_owner_skipped(self, send, staff):
        make_post(make_driver(), cancelled=True)
        make_post(make_driver(name='Sam', chat_id='999'))
        self.run_at(at(DAY, '13:00'))
        send.assert_not_called()

    def test_after_midnight_pickup_sent_previous_evening(self, send, staff):
        make_post(make_driver(), day=DAY + timedelta(days=1), time='00:30')
        self.run_at(at(DAY, '22:45'))
        send.assert_called_once()
        self.assertIn('Tomorrow 12:30 AM', send.call_args[0][1])

    def test_unlinked_driver_alerts_staff_once(self, send, staff):
        post = make_post(make_driver(chat_id=None))
        self.run_at(at(DAY, '12:31'))
        self.run_at(at(DAY, '12:46'))
        send.assert_not_called()
        staff.assert_called_once()
        self.assertIn('미연결', staff.call_args[0][0])
        post.refresh_from_db()
        self.assertIsNone(post.driver_reminder_sent_at)

    def test_reassignment_resends_and_resets_ack(self, send, staff):
        post = make_post(make_driver())
        self.run_at(at(DAY, '12:31'))
        Post.objects.filter(pk=post.pk).update(driver_ack_at=at(DAY, '12:35'))

        other = make_driver(name='Bo', chat_id='222')
        Post.objects.filter(pk=post.pk).update(driver=other)
        self.run_at(at(DAY, '12:46'))

        self.assertEqual(send.call_count, 2)
        self.assertEqual(send.call_args[0][0], '222')
        post.refresh_from_db()
        self.assertEqual(post.driver_reminder_sent_to_id, other.pk)
        self.assertIsNone(post.driver_ack_at)

    def test_permanent_error_marks_handled(self, send, staff):
        send.side_effect = TelegramDriverError('blocked', status_code=403)
        post = make_post(make_driver())
        self.run_at(at(DAY, '12:31'))
        self.run_at(at(DAY, '12:46'))
        self.assertEqual(send.call_count, 1)
        post.refresh_from_db()
        self.assertIsNotNone(post.driver_reminder_sent_to_id)

    def test_transient_error_retries(self, send, staff):
        send.side_effect = [TelegramDriverError('timeout'), None]
        post = make_post(make_driver())
        self.run_at(at(DAY, '12:31'))
        self.run_at(at(DAY, '12:46'))
        self.assertEqual(send.call_count, 2)
        post.refresh_from_db()
        self.assertIsNotNone(post.driver_reminder_sent_at)

    def test_unacked_alert_one_hour_before(self, send, staff):
        post = make_post(make_driver())
        with patch('django.utils.timezone.now', return_value=at(DAY, '12:31')):
            self.run_at(at(DAY, '12:31'))
        staff.reset_mock()

        self.run_at(at(DAY, '13:16'))
        staff.assert_not_called()

        self.run_at(at(DAY, '13:31'))
        staff.assert_called_once()
        self.assertIn('미확인', staff.call_args[0][0])

        self.run_at(at(DAY, '13:46'))
        staff.assert_called_once()  # 경고는 한 번만
        post.refresh_from_db()
        self.assertIsNotNone(post.driver_ack_alert_sent_at)

    def test_acked_no_alert(self, send, staff):
        post = make_post(make_driver())
        self.run_at(at(DAY, '12:31'))
        Post.objects.filter(pk=post.pk).update(driver_ack_at=at(DAY, '12:40'))
        staff.reset_mock()
        self.run_at(at(DAY, '13:31'))
        staff.assert_not_called()

    def test_late_send_gets_grace_before_alert(self, send, staff):
        make_post(make_driver())
        with patch('django.utils.timezone.now', return_value=at(DAY, '14:00')):
            self.run_at(at(DAY, '14:00'))
        staff.reset_mock()
        self.run_at(at(DAY, '14:15'))
        staff.assert_not_called()
        self.run_at(at(DAY, '14:21'))
        staff.assert_called_once()


@override_settings(**BOT)
@patch('blog.tasks.send_telegram_task.delay')
@patch('utils.telegram_driver.edit_message')
@patch('utils.telegram_driver.answer_callback')
@patch('utils.telegram_driver.send_message')
class WebhookTests(TestCase):
    url = '/webhook/telegram/driver/'

    def post(self, update, secret='s3cret'):
        return Client().post(self.url, data=json.dumps(update), content_type='application/json',
                             HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN=secret, secure=True)

    def test_rejects_bad_secret(self, *mocks):
        self.assertEqual(self.post({}, secret='nope').status_code, 403)

    @override_settings(TELEGRAM_DRIVER_WEBHOOK_SECRET='')
    def test_rejects_when_secret_unset(self, *mocks):
        self.assertEqual(self.post({}, secret='').status_code, 403)

    def test_start_links_driver_and_burns_token(self, send, answer, edit, staff):
        driver = make_driver(chat_id=None, telegram_link_token='tkn123')
        r = self.post({'message': {'chat': {'id': 555, 'type': 'private'}, 'text': '/start tkn123'}})
        self.assertEqual(r.status_code, 200)
        driver.refresh_from_db()
        self.assertEqual(driver.telegram_chat_id, '555')
        self.assertIsNone(driver.telegram_link_token)
        self.assertIn('Connected', send.call_args[0][1])

    def test_start_bad_token_does_not_link(self, send, answer, edit, staff):
        make_driver(chat_id=None, telegram_link_token='tkn123')
        self.post({'message': {'chat': {'id': 555, 'type': 'private'}, 'text': '/start wrong'}})
        self.assertFalse(Driver.objects.filter(telegram_chat_id='555').exists())

    def cb(self, post, chat_id):
        return {'callback_query': {'id': 'cq1', 'data': f'ack:{post.pk}', 'message': {
            'message_id': 9, 'chat': {'id': int(chat_id)}, 'text': 'EasyGo job in 2 hours'}}}

    def test_ack_records_and_edits_message(self, send, answer, edit, staff):
        post = make_post(make_driver(chat_id='111'))
        self.post(self.cb(post, '111'))
        post.refresh_from_db()
        self.assertIsNotNone(post.driver_ack_at)
        self.assertIn('Confirmed', edit.call_args[0][2])
        staff.assert_not_called()

    def test_ack_from_other_chat_rejected(self, send, answer, edit, staff):
        post = make_post(make_driver(chat_id='111'))
        self.post(self.cb(post, '222'))
        post.refresh_from_db()
        self.assertIsNone(post.driver_ack_at)
        self.assertIn('no longer assigned', answer.call_args[0][1])

    def test_late_ack_notifies_staff(self, send, answer, edit, staff):
        post = make_post(make_driver(chat_id='111'))
        Post.objects.filter(pk=post.pk).update(driver_ack_alert_sent_at=at(DAY, '13:31'))
        self.post(self.cb(post, '111'))
        staff.assert_called_once()


@patch('blog.bird_proxy.create_bird_mapping', return_value=True)
@patch('blog.bird_proxy.close_bird_mapping', return_value=True)
class DashboardConnectTests(TestCase):

    def login_driver(self, **kw):
        user = User.objects.create_user(username='d1', password='Pass1234!x')
        driver = make_driver(user=user, must_change_password=False, **kw)
        c = Client()
        c.force_login(user)
        return c, driver

    @override_settings(**BOT)
    def test_unlinked_driver_sees_connect_link(self, *m):
        c, driver = self.login_driver(chat_id=None)
        r = c.get(reverse('blog:driver_dashboard'), secure=True)
        driver.refresh_from_db()
        self.assertTrue(driver.telegram_link_token)
        self.assertEqual(r.context['telegram_link_url'],
                         f'https://t.me/EasyGoDriverBot?start={driver.telegram_link_token}')
        self.assertContains(r, 'Connect Telegram')

    @override_settings(**BOT)
    def test_linked_driver_no_link(self, *m):
        c, _ = self.login_driver(chat_id='111')
        r = c.get(reverse('blog:driver_dashboard'), secure=True)
        self.assertIsNone(r.context['telegram_link_url'])

    @override_settings(TELEGRAM_DRIVER_BOT_TOKEN='')
    def test_hidden_when_bot_not_configured(self, *m):
        c, _ = self.login_driver(chat_id=None)
        r = c.get(reverse('blog:driver_dashboard'), secure=True)
        self.assertIsNone(r.context['telegram_link_url'])


@override_settings(**BOT)
@patch('utils.telegram.send_telegram_sync')
@patch('utils.telegram_driver.send_message')
class JobOfferNotificationTests(TestCase):
    """candidate_drivers 에 추가되면 드라이버 봇으로 '대시보드에 잡이 올라왔다' 알림."""

    def setUp(self):
        self.post = make_post(None, day=datetime.date.today() + timedelta(days=3),
                              suburb='Chatswood', driver_price='85.00')

    def add(self, *drivers):
        with self.captureOnCommitCallbacks(execute=True):
            self.post.candidate_drivers.add(*drivers)

    def test_new_candidate_gets_offer_with_dashboard_button(self, send, staff):
        driver = make_driver()
        self.add(driver)
        send.assert_called_once()
        chat_id, text, buttons = send.call_args[0]
        self.assertEqual(chat_id, '111')
        self.assertIn('New job available', text)
        self.assertIn(f'#{self.post.pk}', text)
        self.assertIn('Chatswood', text)
        self.assertIn('$85.00', text)
        self.assertNotIn('Customer', text)
        self.assertEqual(buttons[0][0]['url'][-len(reverse('blog:driver_dashboard')):],
                         reverse('blog:driver_dashboard'))
        staff.assert_not_called()

    def test_existing_candidates_not_renotified_on_set(self, send, staff):
        a, b = make_driver('Alex', '111'), make_driver('Ben', '222')
        self.add(a)
        send.reset_mock()
        with self.captureOnCommitCallbacks(execute=True):
            self.post.candidate_drivers.set([a, b])
        send.assert_called_once()
        self.assertEqual(send.call_args[0][0], '222')

    def test_reverse_add_notifies(self, send, staff):
        driver = make_driver()
        with self.captureOnCommitCallbacks(execute=True):
            driver.candidate_posts.add(self.post)
        send.assert_called_once()

    def test_skips_unconnected_owner_assigned_and_cancelled(self, send, staff):
        self.add(make_driver('Zed', None), make_driver('Sam', '999'))
        send.assert_not_called()

        Post.objects.filter(pk=self.post.pk).update(cancelled=True)
        self.post.refresh_from_db()
        self.add(make_driver('Cara', '333'))
        send.assert_not_called()

        other = make_post(make_driver('Dan', '444'), day=self.post.pickup_date)
        with self.captureOnCommitCallbacks(execute=True):
            other.candidate_drivers.add(make_driver('Eve', '555'))
        send.assert_not_called()

    def test_send_failure_alerts_staff(self, send, staff):
        send.side_effect = TelegramDriverError('blocked', status_code=403)
        self.add(make_driver())
        staff.assert_called_once()
        self.assertIn('잡 오퍼', staff.call_args[0][0])

    @override_settings(TELEGRAM_DRIVER_BOT_TOKEN='')
    def test_noop_when_bot_not_configured(self, send, staff):
        self.add(make_driver())
        send.assert_not_called()
