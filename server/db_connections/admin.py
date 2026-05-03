from django import forms
from django.contrib import admin

from .models import DatabaseConnection


class DatabaseConnectionAdminForm(forms.ModelForm):
    class Meta:
        model = DatabaseConnection
        fields = '__all__'
        widgets = {
            'password': forms.PasswordInput(render_value=False),
        }

    def save(self, commit=True):
        preserve_password = (
            self.cleaned_data.get('password') == '' and self.instance.pk is not None
        )
        instance = super().save(commit=False)
        if preserve_password:
            instance.password = DatabaseConnection.objects.get(pk=self.instance.pk).password
        if commit:
            instance.save()
            self.save_m2m()
        return instance


@admin.register(DatabaseConnection)
class DatabaseConnectionAdmin(admin.ModelAdmin):
    form = DatabaseConnectionAdminForm
    list_display = ('name', 'engine', 'user', 'host', 'port', 'updated_at')
    list_filter = ('engine',)
    search_fields = ('name', 'host', 'user__username', 'database_name')
    raw_id_fields = ('user',)
    readonly_fields = ('created_at', 'updated_at')
