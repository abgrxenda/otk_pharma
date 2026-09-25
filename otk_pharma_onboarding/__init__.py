# otk_pharma_onboarding/__init__.py

from . import models
from . import controllers

def create_delivery_fee_product(env):
    """Create the B2B Delivery Fee service product if it doesn't exist."""
    existing = env.ref(
        'otk_pharma_onboarding.product_delivery_fee',
        raise_if_not_found=False,
    )
    if existing:
        return

    product = env['product.template'].create({
        'name': 'B2B Delivery Fee',
        'type': 'service',
        'invoice_policy': 'order',
        'sale_ok': True,
        'purchase_ok': False,
        'list_price': 0.0,
        'description_sale': 'Delivery fee applied to B2B pharmacy orders.',
    })

    # Register XML ID so we can ref it later
    env['ir.model.data'].create({
        'name': 'product_delivery_fee',
        'module': 'otk_pharma_onboarding',
        'model': 'product.template',
        'res_id': product.id,
        'noupdate': True,
    })