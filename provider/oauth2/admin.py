import operator
from django.contrib import admin
from django import forms
from .models import AccessToken, Grant, Client, RefreshToken
from .. import scope

class ScopeMixin(object):
    """
    Form mixin to clean scope fields.
    """
    def clean_scope(self):
        """
        The scope is assembled by combining all the set flags into a single
        integer value which we can later check again for set bits.

        If *no* scope is set, we return 0

        """
        default = 0

        flags = map(int, self.cleaned_data.get('scope', []))

        return reduce(operator.or_, flags, default)

class ModelAdminForm(ScopeMixin, forms.ModelForm):
    pass

class AccessTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'client', 'token', 'expires',)
    raw_id_fields = ('user',)
    form = ModelAdminForm


class GrantAdmin(admin.ModelAdmin):
    list_display = ('user', 'client', 'code', 'expires',)
    raw_id_fields = ('user',)
    form = ModelAdminForm


class ClientAdmin(admin.ModelAdmin):
    list_display = ('url', 'user', 'redirect_uri', 'client_id', 'client_type')
    raw_id_fields = ('user',)
    form = ModelAdminForm

admin.site.register(AccessToken, AccessTokenAdmin)
admin.site.register(Grant, GrantAdmin)
admin.site.register(Client, ClientAdmin)
admin.site.register(RefreshToken)
