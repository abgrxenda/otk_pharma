from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    kit_component_count = fields.Integer(
        string='Kit Components Count',
        compute='_compute_kit_component_count',
    )
    has_kit_products = fields.Boolean(
        compute='_compute_has_kit_products',
        string='Has Kit Products',
    )
    kit_component_data = fields.Json(
        string='Kit Component Data',
        compute='_compute_kit_component_data',
        help='JSON data for portal display of kit components with stock info.',
    )
    kit_component_summary = fields.Text(
        string='Kit Components',
        compute='_compute_kit_component_summary',
        help='Summary of kit components with stock levels.',
    )

    def _compute_kit_component_count(self):
        for order in self:
            kit_lines = order.order_line.filtered(lambda l: l.is_kit_line and l.bom_id)
            count = 0
            for kit_line in kit_lines:
                count += len(kit_line.bom_id.bom_line_ids)
            order.kit_component_count = count

    @api.depends('order_line.product_id.otk_pharma_bom_id')
    def _compute_has_kit_products(self):
        for order in self:
            order.has_kit_products = bool(
                order.order_line.filtered(lambda l: l.product_id.otk_pharma_bom_id)
            )

    @api.depends('order_line.is_kit_line', 'order_line.bom_id')
    def _compute_kit_component_data(self):
        """
        Compute kit component data for portal display.
        Reads directly from BOM definitions - no component sale order lines needed.
        Returns a list of dicts with component info and stock levels.
        """
        for order in self:
            kit_lines = order.order_line.filtered(lambda l: l.is_kit_line and l.bom_id)
            data = []
            for kit_line in kit_lines:
                bom = kit_line.bom_id
                kit_name = kit_line.product_id.display_name

                for bom_line in bom.bom_line_ids:
                    product = bom_line.product_id
                    # Handle fixed vs scalable quantity
                    if bom_line.is_fixed_quantity:
                        qty = bom_line.product_qty
                    else:
                        qty = bom_line.product_qty * kit_line.product_uom_qty
                    available = product.free_qty
                    needed = qty

                    if available <= 0:
                        status = 'out_of_stock'
                        status_label = 'Out of Stock'
                    elif available < needed:
                        status = 'low_stock'
                        status_label = 'Low Stock'
                    else:
                        status = 'in_stock'
                        status_label = 'In Stock'

                    data.append({
                        'kit_name': kit_name,
                        'product_name': product.display_name,
                        'ordered_qty': qty,
                        'uom': bom_line.product_uom_id.name if bom_line.product_uom_id else 'Units',
                        'stock_on_hand': product.qty_available,
                        'free_available': product.free_qty,
                        'forecasted': product.virtual_available,
                        'stock_status': status,
                        'stock_status_label': status_label,
                    })
            order.kit_component_data = data

    @api.depends('kit_component_data')
    def _compute_kit_component_summary(self):
        """
        Compute a human-readable summary of kit components for backend display.
        """
        for order in self:
            if not order.kit_component_data:
                order.kit_component_summary = False
                continue
            lines = []
            for comp in order.kit_component_data:
                status_icon = {
                    'in_stock': '🟢',
                    'low_stock': '🟡',
                    'out_of_stock': '🔴',
                }.get(comp['stock_status'], '⚪')
                lines.append(
                    f"{status_icon} {comp['product_name']}: "
                    f"Ordered {comp['ordered_qty']} {comp['uom']} | "
                    f"Available {comp['free_available']} | "
                    f"On Hand {comp['stock_on_hand']}"
                )
            order.kit_component_summary = '\n'.join(lines) if lines else False

    def action_confirm(self):
        """
        Override to handle kit explosion and component stock moves.
        """
        # Mark kit lines before confirming
        for order in self:
            kit_lines = order.order_line.filtered(lambda l: l.product_id.otk_pharma_bom_id)
            if kit_lines:
                order._explode_kit_lines(kit_lines)

        # Confirm the order (creates pickings and regular stock moves)
        result = super().action_confirm()

        # Create component stock moves AFTER picking exists
        for order in self:
            kit_lines = order.order_line.filtered(lambda l: l.is_kit_line and l.bom_id)
            if kit_lines:
                order._create_kit_component_moves(kit_lines)

        return result

    def _create_kit_component_moves(self, kit_lines):
        """
        Create stock moves for kit components and add them to the delivery picking.
        Called after order confirmation when picking already exists.
        """
        StockMove = self.env['stock.move']

        # Find the outgoing picking for this sale order
        picking = self.env['stock.picking'].search([
            ('sale_id', '=', self.id),
            ('picking_type_id.code', '=', 'outgoing'),
        ], limit=1)

        if not picking:
            return

        for kit_line in kit_lines:
            bom = kit_line.bom_id
            if not bom or not bom.bom_line_ids:
                continue

            for bom_line in bom.bom_line_ids:
                # Handle fixed vs scalable quantity
                if bom_line.is_fixed_quantity:
                    qty = bom_line.product_qty
                else:
                    qty = bom_line.product_qty * kit_line.product_uom_qty
                StockMove.create({
                    'name': bom_line.product_id.display_name,
                    'product_id': bom_line.product_id.id,
                    'product_uom_qty': qty,
                    'product_uom': bom_line.product_uom_id.id,
                    'sale_line_id': kit_line.id,
                    'picking_id': picking.id,
                    'picking_type_id': picking.picking_type_id.id,
                    'location_id': picking.location_id.id,
                    'location_dest_id': picking.location_dest_id.id,
                    'group_id': self.procurement_group_id.id,
                    'company_id': self.company_id.id,
                    'origin': self.name,
                })

    def _explode_kit_lines(self, kit_lines):
        """
        Mark kit lines - no component sale order lines are created.
        Stock moves for components are created separately via _create_kit_component_moves.
        """
        self.ensure_one()

        for kit_line in kit_lines:
            # Skip if already processed
            if kit_line.is_kit_line and kit_line.bom_id:
                continue

            bom = kit_line.product_id.otk_pharma_bom_id
            if not bom or not bom.bom_line_ids:
                continue

            # Mark the kit line
            kit_line.write({
                'is_kit_line': True,
                'bom_id': bom.id,
            })
