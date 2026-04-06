import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from notifications.tests import NotificationTests
t = NotificationTests('test_list_notifications_isolated')
t.setUpClass()
t.setUp()
try:
    response = t.client.get('/api/notifications/')
    print(response.status_code)
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    t.tearDownClass()
