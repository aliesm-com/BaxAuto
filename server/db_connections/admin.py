from django import forms
from django.contrib import admin

from .models import DatabaseConnection, DatabaseConnectionShare

_SECRET_FIELDS = (
    'password',
    'ssh_password',
    'ssh_private_key',
    'ssh_private_key_passphrase',
)


class DatabaseConnectionAdminForm(forms.ModelForm):
    class Meta:
        model = DatabaseConnection
        fields = '__all__'
        widgets = {
            'password': forms.PasswordInput(render_value=False),
            'ssh_password': forms.PasswordInput(render_value=False),
            'ssh_private_key_passphrase': forms.PasswordInput(render_value=False),
            'ssh_private_key': forms.Textarea(attrs={'rows': 4}),
        }

    def save(self, commit=True):
        preserve = {
            name: (
                self.cleaned_data.get(name) == '' and self.instance.pk is not None
            )
            for name in _SECRET_FIELDS
        }
        instance = super().save(commit=False)
        if any(preserve.values()):
            existing = DatabaseConnection.objects.get(pk=self.instance.pk)
            for name, keep in preserve.items():
                if keep:
                    setattr(instance, name, getattr(existing, name))
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class DatabaseConnectionShareInline(admin.TabularInline):
    model = DatabaseConnectionShare
    extra = 0
    raw_id_fields = ('user',)


@admin.register(DatabaseConnection)
class DatabaseConnectionAdmin(admin.ModelAdmin):
    form = DatabaseConnectionAdminForm
    list_display = ('name', 'engine', 'user', 'host', 'port', 'ssh_enabled', 'updated_at')
    list_filter = ('engine', 'ssh_enabled')
    search_fields = ('name', 'host', 'ssh_host', 'user__username', 'database_name')
    raw_id_fields = ('user',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = (DatabaseConnectionShareInline,)
    fieldsets = (
        (None, {
            'fields': (
                'user',
                'name',
                'engine',
                'host',
                'port',
                'database_name',
                'username',
                'password',
                'virtual_host',
                'connection_uri',
                'use_tls',
                'extra_options',
            ),
        }),
        ('SSH tunnel', {
            'classes': ('collapse',),
            'fields': (
                'ssh_enabled',
                'ssh_host',
                'ssh_port',
                'ssh_username',
                'ssh_password',
                'ssh_private_key',
                'ssh_private_key_passphrase',
                'ssh_host_key_fingerprint',
            ),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )
