NOT_PAID = 0
PAID = 10
FAILED = 20
REFUNDED = 30
PARTIALLY_REFUNDED = 31
VALIDATION_FAILED = 40

CHARGEABLE_STATUS_CHOICES = (
    (NOT_PAID, 'Not paid'),
    (PAID, 'Paid'),
    (FAILED, 'Failed'),
    (REFUNDED, 'Refunded'),
    (PARTIALLY_REFUNDED, 'Partially refunded'),
    (VALIDATION_FAILED, 'Validation Failed')
)


CHARGEABLE_REFUND_CHOICES = (
    ('requested_by_customer', 'Requested by customer'),
    ('duplicate', 'Duplicate'),
    ('fraudulent', 'Fraudulent'),
)
