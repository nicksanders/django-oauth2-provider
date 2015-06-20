# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import skipIf

from django.conf import settings


try:
    from django.contrib.auth.tests.utils import skipIfCustomUser
except ImportError:
    def skipIfCustomUser(wrapped):
        return skipIf(settings.AUTH_USER_MODEL != 'auth.User', 'Custom user model in use')(wrapped)
