# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import provider.validators
import provider.utils
import provider.oauth2.models
from django.conf import settings
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AccessToken',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('token', models.CharField(default=provider.utils.long_token, max_length=255, db_index=True)),
                ('expires', models.DateTimeField()),
                ('scope', provider.oauth2.models.ScopeField(default=0, choices=[(2, b'read'), (4, b'write'), (6, b'read+write')])),
                ('type', models.IntegerField(default=0)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Client',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, blank=True)),
                ('url', models.URLField(help_text="Your application's URL.")),
                ('redirect_uri', models.TextField(help_text="Your application's callback URL", max_length=1028, validators=[provider.validators.validate_uris])),
                ('webhook_uri', models.CharField(blank=True, max_length=1028, null=True, help_text="Your application's webhook URL", validators=[django.core.validators.RegexValidator(regex='^\\S*//\\S*$')])),
                ('logo', models.ImageField(help_text='40x40 pixel logo of your application', null=True, upload_to=provider.oauth2.models.client_logo_image_path, blank=True)),
                ('status', models.PositiveSmallIntegerField(default=1, choices=[(1, 'TEST'), (2, 'LIVE'), (3, 'DISABLED')])),
                ('last_updated_date', models.DateTimeField(auto_now=True)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('client_id', models.CharField(default=provider.utils.short_token, max_length=255)),
                ('client_secret', models.CharField(default=provider.utils.long_token, max_length=255)),
                ('client_type', models.IntegerField(default=0, choices=[(0, b'Confidential (Web applications)'), (1, b'Public (Native and JS applications)')])),
                ('scope', provider.oauth2.models.ScopeField(default=0, choices=[(2, b'read'), (4, b'write'), (6, b'read+write')])),
                ('user', models.ForeignKey(related_name='oauth2_client', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Grant',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(default=provider.utils.long_token, max_length=255)),
                ('expires', models.DateTimeField(default=provider.utils.get_code_expiry)),
                ('redirect_uri', models.CharField(max_length=255, blank=True)),
                ('scope', provider.oauth2.models.ScopeField(default=0, choices=[(2, b'read'), (4, b'write'), (6, b'read+write')])),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('client', models.ForeignKey(to='oauth2.Client')),
                ('user', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='RefreshToken',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('token', models.CharField(default=provider.utils.long_token, max_length=255)),
                ('expired', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('access_token', models.OneToOneField(related_name='refresh_token', to='oauth2.AccessToken')),
                ('client', models.ForeignKey(to='oauth2.Client')),
                ('user', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
        ),
        migrations.AddField(
            model_name='accesstoken',
            name='client',
            field=models.ForeignKey(to='oauth2.Client'),
        ),
        migrations.AddField(
            model_name='accesstoken',
            name='user',
            field=models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True),
        ),
    ]
