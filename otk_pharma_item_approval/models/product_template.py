# otk_pharma_item_approval/models/product_template.py

from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    x_requires_approval = fields.Boolean(
        string='Requires Approval',
        default=False,
        help='Mark this product as a controlled compound. Any order containing '
             'this item will be held and require admin approval before confirming.',
        tracking=True,
    )

    x_approval_note = fields.Char(
        string='Approval Note',
        help='Internal note shown to the admin when reviewing an approval request '
             'for an order containing this product.',
    )

    x_requires_prescription = fields.Boolean(
        string='Requires Prescription',
        default=False,
        help='Mark this product as requiring a prescription. The pharmacy must '
             'upload a valid prescription before the order can proceed.',
        tracking=True,
    )


class ProductProduct(models.Model):
    _inherit = 'product.product'

    x_requires_approval = fields.Boolean(
        string='Requires Approval',
        related='product_tmpl_id.x_requires_approval',
        readonly=False,
    )

    x_requires_prescription = fields.Boolean(
        string='Requires Prescription',
        related='product_tmpl_id.x_requires_prescription',
        readonly=False,
    )