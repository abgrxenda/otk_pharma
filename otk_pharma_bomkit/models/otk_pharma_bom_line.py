from odoo import models, fields, api


class OtkPharmaBomLine(models.Model):
    _name = 'otk.pharma.bom.line'
    _description = 'Pharmacy BOM Component Line'
    _order = 'sequence, id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    bom_id = fields.Many2one(
        'otk.pharma.bom',
        string='BOM',
        required=True,
        ondelete='cascade',
    )
    product_id = fields.Many2one(
        'product.product',
        string='Component',
        required=True,
        domain=[('type', 'in', ('product', 'consu'))],
        tracking=True,
    )
    product_qty = fields.Float(
        string='Quantity',
        required=True,
        default=1.0,
        digits='Product Unit of Measure',
        tracking=True,
    )
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        required=True,
        compute='_compute_product_uom_id',
        store=True,
        readonly=False,
        precompute=True,
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )
    is_fixed_quantity = fields.Boolean(
        string='Fixed Quantity',
        default=False,
        tracking=True,
        help='When checked, this component quantity will NOT be multiplied by the kit order quantity. '
             'Use this for container items, serving items, or one-time components that remain constant '
             'regardless of how many kits are ordered.',
    )
    company_id = fields.Many2one(
        related='bom_id.product_tmpl_id.company_id',
        store=True,
        string='Company',
    )

    @api.depends('product_id')
    def _compute_product_uom_id(self):
        for line in self:
            if line.product_id:
                line.product_uom_id = line.product_id.uom_id
            else:
                line.product_uom_id = self.env.ref('uom.product_uom_unit', raise_if_not_found=False)
