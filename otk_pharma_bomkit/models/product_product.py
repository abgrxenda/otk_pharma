from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    otk_pharma_bom_id = fields.Many2one(
        'otk.pharma.bom',
        string='Pharma BOM',
        compute='_compute_otk_pharma_bom_id',
        help='BOM/Kit definition for this product. If set, this product '
             'is a kit that will be exploded into components on order.',
    )
    is_kit_product = fields.Boolean(
        string='Is Kit Product',
        compute='_compute_is_kit_product',
        help='This product is used as a kit in a BOM definition.',
    )
    is_kit_component = fields.Boolean(
        string='Is Kit Component',
        compute='_compute_is_kit_component',
        help='This product is used as a component in one or more BOMs.',
    )

    def _compute_otk_pharma_bom_id(self):
        Bom = self.env['otk.pharma.bom']
        for product in self:
            # Priority: variant-specific BOM first, then template-level BOM
            bom = Bom.search([('product_id', '=', product.id)], limit=1)
            if not bom:
                bom = Bom.search([
                    ('product_tmpl_id', '=', product.product_tmpl_id.id),
                    ('product_id', '=', False),
                ], limit=1)
            product.otk_pharma_bom_id = bom

    @api.depends('otk_pharma_bom_id')
    def _compute_is_kit_product(self):
        for product in self:
            product.is_kit_product = bool(product.otk_pharma_bom_id)

    @api.depends('product_tmpl_id')
    def _compute_is_kit_component(self):
        BomLine = self.env['otk.pharma.bom.line']
        for product in self:
            product.is_kit_component = bool(
                BomLine.search([('product_id', '=', product.id)], limit=1)
            )

    def write(self, vals):
        """
        When a product's list_price changes and it is used as a BOM component,
        recalculate and update the kit product's sale price.
        """
        result = super().write(vals)

        # Only trigger if the product is a component and price may have changed
        if any(f in vals for f in ('lst_price', 'list_price')):
            boms = self.env['otk.pharma.bom'].search([
                ('bom_line_ids.product_id', 'in', self.ids),
            ])
            if boms:
                boms._update_kit_product_price()

        return result


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    otk_pharma_bom_id = fields.Many2one(
        'otk.pharma.bom',
        string='Pharma BOM',
        compute='_compute_otk_pharma_bom_id',
    )
    otk_pharma_bom_ids = fields.Many2many(
        'otk.pharma.bom',
        string='All BOMs',
        compute='_compute_otk_pharma_bom_ids',
        help='All BOM/Kit definitions for this template and its variants.',
    )
    is_kit_product = fields.Boolean(
        string='Is Kit Product',
        compute='_compute_is_kit_product',
        help='This template has a BOM definition (one of its variants is a kit).',
    )

    def _compute_otk_pharma_bom_id(self):
        Bom = self.env['otk.pharma.bom']
        for tmpl in self:
            # If template has variants with BOMs, pick the first one
            bom = Bom.search([
                '|',
                ('product_id.product_tmpl_id', '=', tmpl.id),
                ('product_tmpl_id', '=', tmpl.id),
            ], limit=1)
            tmpl.otk_pharma_bom_id = bom

    @api.depends('product_variant_ids')
    def _compute_otk_pharma_bom_ids(self):
        """
        Collect ALL BOMs for this template:
        - Template-level BOMs (product_tmpl_id set, product_id empty)
        - Variant-level BOMs (any variant of this template)
        """
        Bom = self.env['otk.pharma.bom']
        for tmpl in self:
            boms = Bom.search([
                '|',
                ('product_id.product_tmpl_id', '=', tmpl.id),
                ('product_tmpl_id', '=', tmpl.id),
            ])
            tmpl.otk_pharma_bom_ids = boms

    @api.depends('otk_pharma_bom_ids')
    def _compute_is_kit_product(self):
        for tmpl in self:
            tmpl.is_kit_product = bool(tmpl.otk_pharma_bom_ids)
