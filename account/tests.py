from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from unittest import mock

from .models import DeviceToken, Notification

User = get_user_model()


class DeviceTokenModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='tester@example.com', password='pass1234')

    def test_register_token(self):
        tok = DeviceToken.objects.create(user=self.user, token='token123', platform='android')
        self.assertEqual(self.user.device_tokens.count(), 1)
        self.assertEqual(str(tok), f"{self.user.email} - android")


from rest_framework.test import APIClient

class FcmSignalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='signal@example.com', password='pass1234')
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        # ensure at least one token exists
        DeviceToken.objects.create(user=self.user, token='tok1')

    # ``create=True`` ensures patch works even if messaging is None because
    # the package hasn't been installed in the test environment.
    @mock.patch('account.fcm.init_firebase', create=True)
    @mock.patch('account.fcm.messaging.send_multicast', create=True)
    def test_notification_trigger_push(self, mocked_multicast, mocked_init):
        # creating a notification should fire the post_save signal which
        # in turn attempts to send via firebase-admin.  we patch the
        # call so we don't perform real network requests.
        Notification.objects.create(
            recipient=self.user,
            sender=self.user,
            notification_type='join_request',
            message='you have a new request',
        )
        # signal spawns a thread; give it a moment to call send_multicast
        mocked_multicast.assert_called()
        # also exercise the device-token registration endpoint
        response = self.client.post('/api/account/device-tokens/', {'token': 'abc123', 'platform': 'web'})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.user.device_tokens.count(), 2)
