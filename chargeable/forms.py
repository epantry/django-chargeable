from django import forms
from chargeable.choices import CHARGEABLE_REFUND_CHOICES


class ChargeableRefundForm(forms.ModelForm):
    amount = forms.IntegerField(min_value=0,)
    reason = forms.ChoiceField(choices=CHARGEABLE_REFUND_CHOICES)

    class Meta:
        from chargeable.models import Chargeable

        model = Chargeable
        fields = ('amount', 'reason')

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount > self.instance.charge_amount:
            raise forms.ValidationError('Cannot refund more than we charged')
        return amount
