from django import forms
from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.contrib.admin.utils import model_ngettext, unquote
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.core.exceptions import PermissionDenied
from django.db import router, transaction
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

from .models import CustomUser
from .ownership import owned_asset_counts, transfer_and_delete_users

User = get_user_model()


class TransferOwnershipForm(forms.Form):
    transfer_to = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label='Transfer ownership to',
        help_text=(
            'Database connections, backups, storage destinations, and scheduled jobs '
            'will be moved to this user before the account is deleted.'
        ),
        empty_label=None,
    )

    def __init__(self, *args, exclude_pks=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = User.objects.filter(is_active=True).order_by('username')
        if exclude_pks:
            qs = qs.exclude(pk__in=exclude_pks)
        self.fields['transfer_to'].queryset = qs


def delete_selected_with_transfer(modeladmin, request, queryset):
    """Bulk-delete users after transferring owned data to another account."""
    opts = modeladmin.opts
    app_label = opts.app_label

    if not modeladmin.has_delete_permission(request):
        raise PermissionDenied

    deletable = queryset
    exclude_pks = list(deletable.values_list('pk', flat=True))
    has_target = User.objects.filter(is_active=True).exclude(pk__in=exclude_pks).exists()
    form = TransferOwnershipForm(request.POST or None, exclude_pks=exclude_pks)

    if request.POST.get('post'):
        if not has_target:
            modeladmin.message_user(
                request,
                'Cannot delete: no other active user exists to receive ownership.',
                messages.ERROR,
            )
            return None
        if form.is_valid():
            n = deletable.count()
            transfer_to = form.cleaned_data['transfer_to']
            transfer_and_delete_users(deletable, transfer_to)
            modeladmin.message_user(
                request,
                f'Successfully deleted {n} {model_ngettext(opts, n)}. '
                f'Owned data transferred to “{transfer_to}”.',
                messages.SUCCESS,
            )
            return None

    deleted_objects, model_count, perms_needed, protected = modeladmin.get_deleted_objects(
        list(deletable), request
    )

    asset_counts_total = {
        'database_connections': 0,
        'storage_destinations': 0,
        'scheduled_jobs': 0,
    }
    for user in deletable:
        counts = owned_asset_counts(user)
        for key in asset_counts_total:
            asset_counts_total[key] += counts[key]

    context = {
        **modeladmin.admin_site.each_context(request),
        'title': 'Are you sure?',
        'objects_name': model_ngettext(opts, deletable.count()),
        'deletable_objects': [deleted_objects],
        'model_count': dict(model_count).items(),
        'queryset': deletable,
        'perms_lacking': perms_needed,
        'protected': protected,
        'opts': opts,
        'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
        'media': modeladmin.media,
        'transfer_form': form,
        'has_transfer_target': has_target,
        'asset_counts_total': asset_counts_total,
    }

    request.current_app = modeladmin.admin_site.name
    return TemplateResponse(
        request,
        modeladmin.delete_selected_confirmation_template
        or [
            f'admin/{app_label}/{opts.model_name}/delete_selected_confirmation.html',
            f'admin/{app_label}/delete_selected_confirmation.html',
            'admin/delete_selected_confirmation.html',
        ],
        context,
    )


delete_selected_with_transfer.allowed_permissions = ('delete',)
delete_selected_with_transfer.short_description = 'Delete selected users (transfer data)'


@admin.register(CustomUser)
class CustomUserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        ('App roles', {'fields': ('is_viewer', 'is_editor', 'is_admin')}),
        ('Contact', {'fields': ('phone_number', 'country_code')}),
    )
    list_display = (
        *DjangoUserAdmin.list_display,
        'is_viewer',
        'is_editor',
        'is_admin',
        'phone_number',
        'country_code',
    )
    actions = [delete_selected_with_transfer]
    delete_confirmation_template = 'admin/accounts/customuser/delete_confirmation.html'
    delete_selected_confirmation_template = (
        'admin/accounts/customuser/delete_selected_confirmation.html'
    )

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def get_deleted_objects(self, objs, request):
        """Only list user accounts; owned assets are transferred, not wiped."""
        _deleted, _model_count, perms_needed, protected = super().get_deleted_objects(
            objs, request
        )
        simplified = [str(obj) for obj in objs]
        model_count = {str(CustomUser._meta.verbose_name_plural): len(objs)}
        return simplified, model_count, perms_needed, protected

    @method_decorator(csrf_protect)
    def delete_view(self, request, object_id, extra_context=None):
        if request.method in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
            return self._transfer_delete_view(request, object_id, extra_context)
        with transaction.atomic(using=router.db_for_write(self.model)):
            return self._transfer_delete_view(request, object_id, extra_context)

    def _transfer_delete_view(self, request, object_id, extra_context=None):
        obj = self.get_object(request, unquote(object_id))
        if not self.has_delete_permission(request, obj):
            raise PermissionDenied
        if obj is None:
            return self._get_obj_does_not_exist_redirect(
                request, self.opts, object_id
            )

        exclude_pks = [obj.pk]
        has_target = User.objects.filter(is_active=True).exclude(pk__in=exclude_pks).exists()
        form = TransferOwnershipForm(request.POST or None, exclude_pks=exclude_pks)

        deleted_objects, model_count, perms_needed, protected = self.get_deleted_objects(
            [obj], request
        )

        if request.method == 'POST' and not protected:
            if perms_needed:
                raise PermissionDenied
            if not has_target:
                self.message_user(
                    request,
                    'Cannot delete: no other active user exists to receive ownership.',
                    messages.ERROR,
                )
                return HttpResponseRedirect(
                    reverse(f'admin:{self.opts.app_label}_{self.opts.model_name}_changelist')
                )
            if form.is_valid():
                transfer_to = form.cleaned_data['transfer_to']
                obj_display = str(obj)
                obj_id = obj.pk
                self.log_deletions(request, [obj])
                transfer_and_delete_users([obj], transfer_to)
                self.message_user(
                    request,
                    f'User “{obj_display}” deleted. Owned data transferred to “{transfer_to}”.',
                    messages.SUCCESS,
                )
                return self.response_delete(request, obj_display, obj_id)

        context = {
            **self.admin_site.each_context(request),
            'title': 'Delete',
            'subtitle': None,
            'object_name': str(self.opts.verbose_name),
            'object': obj,
            'deleted_objects': deleted_objects,
            'model_count': dict(model_count).items(),
            'perms_lacking': perms_needed,
            'protected': protected,
            'opts': self.opts,
            'app_label': self.opts.app_label,
            'preserved_filters': self.get_preserved_filters(request),
            'transfer_form': form,
            'asset_counts': owned_asset_counts(obj),
            'has_transfer_target': has_target,
            **(extra_context or {}),
        }
        return self.render_delete_form(request, context)

    def delete_model(self, request, obj):
        form = TransferOwnershipForm(request.POST, exclude_pks=[obj.pk])
        if not form.is_valid():
            raise PermissionDenied('Select a user to receive ownership before deleting.')
        transfer_and_delete_users([obj], form.cleaned_data['transfer_to'])
