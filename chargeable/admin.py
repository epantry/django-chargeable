from django.conf.urls import patterns, url
from django.contrib import admin, messages
from django.shortcuts import render
from chargeable.forms import ChargeableRefundForm


class ChargeableAdminRefundMixin(object):

    def do_refund(self, request, id, **kwargs):
        obj = self.get_object(request, id)
        template_name = 'admin/chargeable/refund_form.html'

        if request.method == 'POST':
            form = ChargeableRefundForm(request.POST, instance=obj)
            if form.is_valid():
                if form.instance.refund(amount=form.cleaned_data['amount'], reason=form.cleaned_data['reason']):
                    self.message_user(request, 'Refund succeeded. Closing window...', messages.SUCCESS)
                    return render(request, template_name, context={'refunded': 1, 'is_popup': 1})
                else:
                    self.message_user(request, obj.refund_error_msg, messages.ERROR)
                    return render(request, template_name, context={'form': form, 'is_popup': 1})

            return render(request, template_name, context={'form': form, 'is_popup': 1})

        if request.method == 'GET':
            form = ChargeableRefundForm(instance=obj, initial={'amount': obj.charge_amount})
            return render(request, template_name, context={'form': form, 'is_popup': 1})


class ChargeableAdmin(admin.ModelAdmin, ChargeableAdminRefundMixin):

    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.model_name

        urls = patterns('',
                        (url(r'^(\d+)/refund/$',
                             self.admin_site.admin_view(self.do_refund),
                             name='%s_%s_refund' % info)
                         ),
                        )
        return urls + super(ChargeableAdmin, self).get_urls()