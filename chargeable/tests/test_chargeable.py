from decimal import Decimal
import datetime
from chargeable.app_settings import CHARGEABLE_STRIPE_MAXIMUM_CHARGE_AMOUNT
from django.core.cache import cache
from django.test import TestCase
from mock import Mock, patch
from stripe import StripeError
from chargeable.choices import *
from chargeable.exceptions import ValidationError
from chargeable.models import Chargeable
from chargeable.tests.models import RealChargeable


class TestChargeValidation(TestCase):

    def setUp(self):
        self.chargeable = RealChargeable()
        self.chargeable.validation_failed = Mock()

    def test_validate_returns_true(self):
        self.chargeable.payer.stripe_token = 'valid_stripe_token'
        self.assertTrue(self.chargeable.is_valid_for_charge())

    def test_payers_without_stripe_tokens_are_not_valid(self):
        self.chargeable.payer.stripe_token = None
        self.assertFalse(self.chargeable.is_valid_for_charge())
        self.assertEqual(self.chargeable.charge_status, VALIDATION_FAILED)
        self.chargeable.validation_failed.assert_called_once_with('1 RealChargeable does not belong to active customer')

    def test_chargeable_with_charge_id_not_valid(self):
        self.chargeable.charge_id = '123'
        self.assertFalse(self.chargeable.is_valid_for_charge())
        self.assertEqual(self.chargeable.charge_status, VALIDATION_FAILED)
        self.chargeable.validation_failed.assert_called_once_with('1 RealChargeable has already been charged : charge_id is set')

    def test_chargeable_with_0_charge_amount_not_valid(self):
        self.chargeable.charge_amount = 0
        self.assertFalse(self.chargeable.is_valid_for_charge())
        self.assertEqual(self.chargeable.charge_status, VALIDATION_FAILED)
        self.chargeable.validation_failed.assert_called_once_with('1 RealChargeable has already been charged: charge_amount is set (but charge_id is NOT set...weird)')

    def test_chargeable_must_be_saved(self):
        c = RealChargeable()
        c.id = None
        c.validation_failed = Mock()
        self.assertFalse(c.is_valid_for_charge())
        c.validation_failed.assert_called_once_with('Chargeable object RealChargeable must be saved before it can be charged')

    def test_chargeable_with_a_charge_amount_not_valid(self):
        #even if the charge id is null
        self.chargeable.charge_amount = Decimal("10.00")
        self.assertFalse(self.chargeable.is_valid_for_charge())
        self.assertEqual(self.chargeable.charge_status, VALIDATION_FAILED)
        self.chargeable.validation_failed.assert_called_once_with('1 RealChargeable has already been charged: charge_amount is set (but charge_id is NOT set...weird)')


class TestRefundValidation(TestCase):

    def setUp(self):
        self.chargeable = RealChargeable()
        self.chargeable.charge_id = 'test_charge_id'
        self.chargeable.charge_status = PAID

    def test_validation_fails_on_wrong_status(self):
        statuses = [NOT_PAID, FAILED, REFUNDED, VALIDATION_FAILED]
        for status in statuses:
            self.chargeable.charge_status = status
            self.assertFalse(self.chargeable.is_valid_for_refund())
            expected = 'Cannot refund Chargeable with status "%s"' % self.chargeable.get_charge_status_display()
            self.assertEqual(self.chargeable.refund_error_msg, expected)

    def test_cant_refund_with_charge_amount_zero(self):
        self.chargeable.charge_amount = 0

        self.assertFalse(self.chargeable.is_valid_for_refund())
        expected = 'Cannot refund Chargeable with charged amount = 0'
        self.assertEqual(self.chargeable.refund_error_msg, expected)

    def test_cant_refund_with_amount_zero(self):
        self.assertFalse(self.chargeable.is_valid_for_refund(amount=0))
        expected = 'Cannot refund 0'
        self.assertEqual(self.chargeable.refund_error_msg, expected)

    def test_cant_refund_more_than_charged(self):
        self.chargeable.charge_amount = 500
        amount = self.chargeable.charge_amount + 1
        self.assertFalse(self.chargeable.is_valid_for_refund(amount=amount))
        expected = 'Cannot refund more than was charged'
        self.assertEqual(self.chargeable.refund_error_msg, expected)

    def test_cant_refund_with_charge_id_not_set(self):
        self.chargeable.charge_id = None
        self.assertFalse(self.chargeable.is_valid_for_refund())
        expected = 'Cannot refund Chargeable with charge_id not set'
        self.assertEqual(self.chargeable.refund_error_msg, expected)

    def test_validate_return_true(self):
        self.assertTrue(self.chargeable.is_valid_for_refund())

class TestAmount(TestCase):

    def setUp(self):
        self.chargeable = Chargeable()
        self.real_chargeable = RealChargeable()

    def test_get_charge_amount_raises_error(self):
        self.assertRaises(NotImplementedError, self.chargeable.get_charge_amount)

    def test_get_charge_amount_gives_integer(self):
        got = self.real_chargeable.get_charge_amount()

        self.assertIsInstance(got, int)


def mocked_charge(amount, customer, currency, description):
    return type('obj', (object,), {'id': 'asd', 'amount': amount})


class TestCharge(TestCase):

    def setUp(self):
        self.patcher = patch('stripe.Charge.create')
        self.mocked_stripe = self.patcher.start()
        self.mocked_stripe.side_effect = mocked_charge
        self.to_charge = 500

        self.chargeable = RealChargeable()

    def tearDown(self):
        self.patcher.stop()

    def test_charge_calls_validate_for_charge(self):
        self.chargeable._validate_for_charge = Mock()

        self.chargeable.charge()

        self.chargeable._validate_for_charge.assert_called_once_with()

    def test_validation_failed_called_when_validate_returned_false(self):
        self.chargeable._validate_for_charge = Mock(side_effect=ValidationError('test'))
        self.chargeable.validation_failed = Mock()

        self.chargeable.charge()

        self.chargeable.validation_failed.assert_called_once_with('test')
        self.assertFalse(self.chargeable.is_charged)

    def test_right_field_values_set_after_successful_charge(self):
        self.chargeable._validate_for_charge = Mock(return_value=True)

        self.chargeable.charge()

        self.assertEqual(self.chargeable.charge_amount, self.chargeable._charge_amount)
        self.assertEqual(self.chargeable.charge_status, PAID)
        self.assertIsNotNone(self.chargeable.charge_date)

    def test_charge_failed_give_failed_status(self):
        self.mocked_stripe.side_effect = StripeError

        self.chargeable.charge()

        self.assertEqual(self.chargeable.charge_status, FAILED)

    def test_charge_failed_called_on_stripe_error(self):
        self.mocked_stripe.side_effect = StripeError
        self.chargeable.charge_failed = Mock()

        self.chargeable.charge()

        self.assertEqual(self.chargeable.charge_failed.call_count, 1)

    def test_post_charge_and_save_called_after_charge_succeeded(self):
        self.chargeable.post_charge = Mock()
        self.chargeable.save = Mock()

        self.chargeable.charge()

        self.chargeable.post_charge.assert_called_once_with()
        self.chargeable.save.assert_called_once_with()

    def test_cannot_charge_more_than_max_amount(self):
        self.chargeable._charge_amount = CHARGEABLE_STRIPE_MAXIMUM_CHARGE_AMOUNT + 1
        self.assertFalse(self.chargeable.is_valid_for_charge())

    def test_chargeable_locked_on_charge(self):
        self.chargeable._lock = Mock(return_value=True)

        self.chargeable.charge()

        self.chargeable._lock.assert_called_once_with()

    def test_cannot_charge_when_locked(self):
        self.assertTrue(self.chargeable._lock())

        self.assertFalse(self.chargeable.charge())

        self.assertEqual(self.mocked_stripe.call_count, 0)

        self.chargeable._unlock()

    def test_chargeable_unlocked_after_charge(self):
        self.assertTrue(self.chargeable.charge())

        self.assertFalse(cache.has_key(self.chargeable._lock_key))