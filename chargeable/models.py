import sys
import stripe
import logging

from datetime import datetime
from django.conf import settings
from django.core.cache import cache
from django.db import models
from stripe.error import StripeError
from chargeable import app_settings
from chargeable.exceptions import ValidationError
from chargeable.managers import ChargeableManager
from chargeable.choices import *


logger = logging.getLogger('chargeable')


class Chargeable(models.Model):
    charge_id = models.CharField(max_length=32, blank=True, null=True)
    charge_status = models.IntegerField(choices=CHARGEABLE_STATUS_CHOICES, default=0)
    charge_amount = models.IntegerField(null=True, blank=True)
    charge_date = models.DateTimeField(null=True, blank=True)

    charge_error_msg = None

    objects = ChargeableManager()

    class Meta:
        abstract = True

    @property
    def payer(self):
        raise NotImplementedError

    @property
    def is_charged(self):
        return self.charge_status == PAID

    @property
    def _charge_lock_key(self):
        return 'charge_lock_%s_%s' % (self.__class__.__name__, self.id)

    def charge(self, **kwargs):
        stripe.api_key = settings.STRIPE_API_KEY
        if self.is_valid_for_charge(**kwargs) and self._lock_for_charge():
            try:
                amount = self.get_charge_amount()
                logger.info('Charging %s: %s' % (self.payer.id, amount))
                if amount >= app_settings.CHARGEABLE_STRIPE_MINIMUM_CHARGE_AMOUNT:
                    charge = stripe.resource.Charge.create(amount=amount,
                                                           customer=self.payer.stripe_token,
                                                           currency='usd',
                                                           description=self.get_charge_description()
                    )
                    logger.info('Charged %s: %s' % (self.payer.id, amount))
                    self.charge_id = charge.id
                    amount = charge.amount
                self.charge_amount = amount
                self.charge_status = PAID
                self.charge_date = datetime.now()
                self.charge_succeeded(amount, **kwargs)
            except StripeError as e:
                self.charge_status = FAILED
                exc_type, exc_value, _ = sys.exc_info()
                self.charge_error_msg = exc_value.message
                logger.warning('Charge failed %s %s:%s - %s' % (amount, self.payer.id, exc_type, exc_value))
                self.charge_failed(e, **kwargs)
            finally:
                self.save()
                self._unlock_for_charge()
                self.post_charge(**kwargs)
        return self.is_charged

    def is_valid_for_charge(self, **kwargs):
        try:
            self._validate_for_charge(**kwargs)

            if not self.id:
                self.charge_error_msg = 'Chargeable object %s must be saved before it can be charged' % self.__class__.__name__
                raise ValidationError(self.charge_error_msg)
            if self.get_charge_amount() > app_settings.CHARGEABLE_STRIPE_MAXIMUM_CHARGE_AMOUNT:
                self.charge_error_msg = 'Cannot charge more than $%s' % (app_settings.CHARGEABLE_STRIPE_MAXIMUM_CHARGE_AMOUNT / 100.0)
                raise ValidationError('%s %s: %s' % (self.__class__.__name__, self.id, self.charge_error_msg))
            if self.charge_id:
                self.charge_error_msg = '%s has already been charged' % self.__class__.__name__
                raise ValidationError('%s %s : charge_id is set' % (self.id, self.charge_error_msg))
            if self.charge_amount is not None:
                self.charge_error_msg = '%s has already been charged' % self.__class__.__name__
                raise ValidationError('%s %s: charge_amount is set (but charge_id is NOT set...weird)' % (self.id, self.charge_error_msg))
            if self.is_charged:
                self.charge_error_msg = '%s has already been charged' % self.__class__.__name__
                raise ValidationError('%s %s has already been charged' % (self.id, self.charge_error_msg))
            if self.payer is None:
                self.charge_error_msg = '%s does not belong to active customer' % self.__class__.__name__
                raise ValidationError('%s %s' % (self.id, self.charge_error_msg))
            if not self.payer.stripe_token:
                self.charge_error_msg = '%s does not belong to active customer' % self.__class__.__name__
                raise ValidationError('%s %s' % (self.id, self.charge_error_msg))
        except ValidationError as e:
            logger.info("Validation failed for %s %s, payer %s: %s" % (self.__class__.__name__, self.id, self.payer.id, e.message))
            self.charge_status = VALIDATION_FAILED
            self.save()
            self.validation_failed(e.message)
            return False
        return True

    def _validate_for_charge(self, **kwargs):
        raise ValidationError('_validate_for_charge method should be implemented on %s.' % self.__class__.__name__)

    def get_charge_amount(self):
        """Must return amount to charge, in cents."""
        raise NotImplementedError

    def charged_display(self):
        """Dollars to cents for use anywhere a human needs to see it"""
        return round(self.charge_amount / 100.0, 2) if self.charge_amount else 0.0

    def get_charge_description(self):
        return 'Chargeable %s id:%s' % (self.__class__.__name__, self.id)

    def post_charge(self, **kwargs):
        pass

    def charge_succeeded(self, charge_amount, **kwargs):
        pass

    def charge_failed(self, exc, **kwargs):
        pass

    def validation_failed(self, message):
        pass

    def _lock_for_charge(self):
        return cache.add(self._charge_lock_key, 1, app_settings.CHARGEABLE_CHARGE_LOCK_TIME)

    def _unlock_for_charge(self):
        cache.delete(self._charge_lock_key)