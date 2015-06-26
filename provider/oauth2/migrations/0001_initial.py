# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import provider.utils


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AccessToken',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('token', models.CharField(max_length=255, default=provider.utils.long_token, db_index=True)),
                ('expires', models.DateTimeField()),
                ('scope', models.IntegerField(default=2, choices=[(2, 'read'), (4, 'write'), (6, 'read+write')])),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Client',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('name', models.CharField(max_length=255, blank=True)),
                ('url', models.URLField(help_text="Your application's URL.")),
                ('redirect_uri', models.URLField(help_text="Your application's callback URL")),
                ('client_id', models.CharField(max_length=255, default=provider.utils.short_token)),
                ('client_secret', models.CharField(max_length=255, default=provider.utils.long_token)),
                ('client_type', models.IntegerField(choices=[(0, 'Confidential (Web applications)'), (1, 'Public (Native and JS applications)')])),
                ('user', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, related_name='oauth2_client', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Grant',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('code', models.CharField(max_length=255, default=provider.utils.long_token)),
                ('expires', models.DateTimeField(default=provider.utils.get_code_expiry)),
                ('redirect_uri', models.CharField(max_length=255, blank=True)),
                ('scope', models.IntegerField(default=0)),
                ('client', models.ForeignKey(to='oauth2.Client')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='RefreshToken',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('token', models.CharField(max_length=255, default=provider.utils.long_token)),
                ('expired', models.BooleanField(default=False)),
                ('access_token', models.OneToOneField(to='oauth2.AccessToken', related_name='refresh_token')),
                ('client', models.ForeignKey(to='oauth2.Client')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='accesstoken',
            name='client',
            field=models.ForeignKey(to='oauth2.Client'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='accesstoken',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
    ]
