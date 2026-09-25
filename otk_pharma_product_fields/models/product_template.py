from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # ═══════════════════════════════════════════════════════════
    # NOTE: x_requires_approval and x_requires_prescription are
    # already defined in otk_pharma_item_approval module.
    # Do NOT duplicate them here.
    # ═══════════════════════════════════════════════════════════

    # Drug Identification Number
    x_din = fields.Char(
        string='DIN',
        help='Drug Identification Number assigned by regulatory authority.',
    )

    # Generic Name (active ingredient name)
    x_generic_name = fields.Char(
        string='Generic Name',
        help='Generic/chemical name of the drug product.',
    )

    # Brand Name
    x_brand_name = fields.Char(
        string='Brand Name',
        help='Brand/trade name of the drug product.',
    )

    # Manufacturer Code
    x_manufacturer_code = fields.Char(
        string='Manufacturer Code',
        help='Internal or manufacturer-specific product code.',
    )

    # Schedule Category (regulatory classification)
    x_schedule_category = fields.Char(
        string='Schedule Category',
        help='Regulatory schedule classification (e.g., Schedule H, Schedule G).',
    )

    # MLP - Max Listed Price (monetary field)
    x_mlp = fields.Monetary(
        string='MLP (Max Listed Price)',
        currency_field='currency_id',
        help='Maximum Listed Price — the highest price at which this product can be sold.',
    )

    # LCAP - Lowest Alternative Price (monetary field)
    x_lcap = fields.Monetary(
        string='LCAP (Lowest Alt Price)',
        currency_field='currency_id',
        help='Lowest Alternative Price — price of the cheapest alternative product.',
    )

    # Tier (product tier/classification)
    x_tier = fields.Char(
        string='Tier',
        help='Product tier classification.',
    )


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # Related fields for product variants (pointing to product.template)
    x_din = fields.Char(
        string='DIN',
        related='product_tmpl_id.x_din',
        readonly=False,
    )

    x_generic_name = fields.Char(
        string='Generic Name',
        related='product_tmpl_id.x_generic_name',
        readonly=False,
    )

    x_brand_name = fields.Char(
        string='Brand Name',
        related='product_tmpl_id.x_brand_name',
        readonly=False,
    )

    x_manufacturer_code = fields.Char(
        string='Manufacturer Code',
        related='product_tmpl_id.x_manufacturer_code',
        readonly=False,
    )

    x_schedule_category = fields.Char(
        string='Schedule Category',
        related='product_tmpl_id.x_schedule_category',
        readonly=False,
    )

    x_mlp = fields.Monetary(
        string='MLP (Max Listed Price)',
        related='product_tmpl_id.x_mlp',
        currency_field='currency_id',
        readonly=False,
    )

    x_lcap = fields.Monetary(
        string='LCAP (Lowest Alt Price)',
        related='product_tmpl_id.x_lcap',
        currency_field='currency_id',
        readonly=False,
    )

    x_tier = fields.Char(
        string='Tier',
        related='product_tmpl_id.x_tier',
        readonly=False,
    )
