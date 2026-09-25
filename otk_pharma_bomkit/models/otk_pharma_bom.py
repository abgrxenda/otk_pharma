from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OtkPharmaBom(models.Model):
    _name = 'otk.pharma.bom'
    _description = 'Pharmacy Bill of Materials / Kit Definition'
    _order = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Kit Name',
        required=True,
        tracking=True,
    )
    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Kit Product',
        required=True,
        domain=[('sale_ok', '=', True)],
        tracking=True,
        help='The product that represents this kit. When sold, it will be '
             'exploded into its component items based on the BOM type.',
    )
    product_id = fields.Many2one(
        'product.product',
        string='Kit Product Variant',
        domain="[('product_tmpl_id', '=', product_tmpl_id)]",
        tracking=True,
        help='Specific variant of the kit product. Leave empty to apply to all variants.',
    )
    bom_type = fields.Selection([
        ('kit_only', 'Kit Only (Show Components)'),
        ('explode', 'Explode to Components'),
    ], string='BOM Type', default='kit_only', required=True,
       tracking=True,
       help='Kit Only: order line shows the kit product, components visible in a tab.\n'
            'Explode: order line is replaced by individual component lines.')
    bom_line_ids = fields.One2many(
        'otk.pharma.bom.line',
        'bom_id',
        string='Components',
        copy=True,
        tracking=True,
    )
    component_count = fields.Integer(
        string='Number of Components',
        compute='_compute_component_count',
    )
    is_configured = fields.Boolean(
        string='Fully Configured',
        compute='_compute_is_configured',
        help='True when the BOM has at least one component line.',
    )
    kit_calculated_price = fields.Float(
        string='Calculated Kit Price',
        compute='_compute_kit_calculated_price',
        digits='Product Price',
        help='Auto-calculated from component list prices (qty × unit price sum).',
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )

    _sql_constraints = [
        ('product_uniq', 'unique(product_id)',
         'A BOM/Kit definition already exists for this product variant. '
         'To define kits for specific variants, select the variant in the "Kit Product Variant" field.'),
    ]

    # ── Create / Write Override: Update kit product sale price ────────────────

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._update_kit_product_price()
        return records

    def write(self, vals):
        result = super().write(vals)
        # Always recalculate and update price on every save
        self._update_kit_product_price()
        return result

    # ── Computed Fields ───────────────────────────────────────────────────────

    @api.depends('bom_line_ids')
    def _compute_component_count(self):
        for bom in self:
            bom.component_count = len(bom.bom_line_ids)

    @api.depends('bom_line_ids', 'bom_line_ids.product_id')
    def _compute_is_configured(self):
        for bom in self:
            bom.is_configured = bool(bom.bom_line_ids)

    @api.depends('bom_line_ids', 'bom_line_ids.product_id', 'bom_line_ids.product_qty', 'bom_line_ids.is_fixed_quantity')
    def _compute_kit_calculated_price(self):
        """Sum of (component list_price × qty) for all BOM lines.
        For fixed quantity components, qty is not multiplied by any kit quantity.
        For scalable components, qty is multiplied by a base kit quantity of 1.
        """
        for bom in self:
            total = 0.0
            for line in bom.bom_line_ids:
                # For BOM form view, we calculate based on 1 unit of kit
                # Fixed quantity components: use their qty as-is
                # Scalable quantity components: multiply by 1 (base unit)
                total += line.product_id.lst_price * line.product_qty
            bom.kit_calculated_price = total

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_view_components(self):
        self.ensure_one()
        if not self.bom_line_ids:
            return {'type': 'ir.actions.act_window_close'}
        product_ids = self.bom_line_ids.mapped('product_id').ids
        return {
            'name': _('Kit Components'),
            'type': 'ir.actions.act_window',
            'res_model': 'product.product',
            'view_mode': 'list,form',
            'domain': [('id', 'in', product_ids)],
            'context': {'create': False},
        }

    # ── Internal Methods ──────────────────────────────────────────────────────

    def _update_kit_product_price(self):
        """
        Update the kit product's sale price based on component list prices.
        Called on create, write, and when component prices change.
        """
        for bom in self:
            if not bom.bom_line_ids:
                continue

            # Determine which product variant to update
            target_product = bom.product_id or (
                bom.product_tmpl_id.product_variant_ids[:1] if bom.product_tmpl_id.product_variant_ids
                else False
            )
            if not target_product:
                continue

            # Calculate total from components
            total = sum(
                line.product_id.lst_price * line.product_qty
                for line in bom.bom_line_ids
            )

            # Update the product's list_price
            if target_product.list_price != total:
                target_product.list_price = total
