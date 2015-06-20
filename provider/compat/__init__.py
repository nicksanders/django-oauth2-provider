# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import skipIf

from django.conf import settings


try:
    from django.contrib.auth.tests.utils import skipIfCustomUser
except ImportError:
    def skipIfCustomUser(wrapped):
        return skipIf(settings.AUTH_USER_MODEL != 'auth.User', 'Custom user model in use')(wrapped)


if django.VERSION < (1, 7, 0):
    from django.db.models import get_model
else:
    from django.apps import apps
    get_model = apps.get_model


user_model_label = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')

try:
    from django.contrib.auth import get_user_model
except ImportError:
    def get_user_model():
        return get_model(*user_model_label.rsplit('.', 1))
