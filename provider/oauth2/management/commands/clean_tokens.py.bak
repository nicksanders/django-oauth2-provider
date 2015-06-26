# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.management.base import BaseCommand
from django.utils.timezone import now

from ...models import AccessToken, Grant, RefreshToken


class Command(BaseCommand):
    help = 'Cleans up expires oauth2 rows'

    def handle(self, *args, **options):
        self._do_clean('refresh tokens', RefreshToken.objects.filter(expired=True))
        self._do_clean('grants', Grant.objects.filter(expires__lt=now()))
        self._do_clean('access tokens', AccessToken.objects.filter(expires__lt=now()))

    def _do_clean(self, name, queryset):
        self.stdout.write("Finding expired {}...".format(name), ending='')
        count = queryset.count()
        self.stdout.write("Removing {:d} expired {}...".format(count, name), ending='')
        queryset.delete()
        self.stdout.write("Removed")
