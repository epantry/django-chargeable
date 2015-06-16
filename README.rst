django-chargeable is a simple wrapper for models that supposed to charged.

Install:

``pip install git+https://github.com:Anton-Shutik/django-chargeable``

Add to INSTALLED_APPS

``INSTALLED_APPS = (
...,
'chargeable',
...
)``

Just inherit from Chargeable model and implement several functions to make it working:

  @property
  def payer(self):
    # Return any objects that has stripe_token set up

   def get_charge_amount(self):
    # return amount to be charged in cents

  def _validate_for_charge(self, **kwargs):
    # place any validation logic here, raise ValidationError to prevent charge

  def post_charge(self, **kwargs): (optional)
    # This function called after charge happend and model saved.

  def charge_succeeded(self, charge_amount, **kwargs): (optional)
    # This function called after charge succeeded, but before model saved

  def charge_failed(self, exc, **kwargs): (optional)
    # This function called after charge failed, but before model saved

