from django.db import models
from chargeable.choices import *


class ChargeableManager(models.Manager):

    def paid(self, **kwargs):
        return self.filter(charge_status=PAID, **kwargs)

    def failed(self, **kwargs):
        return self.filter(charge_status=FAILED, **kwargs)

    def refunded(self, **kwargs):
        return self.filter(charge_status=REFUNDED, **kwargs)