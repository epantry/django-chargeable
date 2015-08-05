from decimal import Decimal
from chargeable.models import Chargeable


class Payer(object):
    id = 1
    is_active = True
    stripe_token = 'valid_token'


class RealChargeable(Chargeable):
    id = 1
    payer = Payer()
    _charge_amount = 1000  # $10.00

    class Meta:
        abstract = True

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        pass

    def _validate_for_charge(self, **kwargs):
        pass

    def get_charge_amount(self):
        return self._charge_amount