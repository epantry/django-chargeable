NOT_PAID = 0
PAID = 10
FAILED = 20
REFUNDED = 30
VALIDATION_FAILED = 40

CHARGEABLE_STATUS_CHOICES = (
    (NOT_PAID, 'Not paid'),
    (PAID, 'Paid'),
    (FAILED, 'Failed'),
    (REFUNDED, 'Refunded'),
    (VALIDATION_FAILED, 'Validation Failed')
)