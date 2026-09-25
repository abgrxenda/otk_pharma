from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_kit_line = fields.Boolean(
        string='Is Kit Product',
        default=False,
        help='This line is a kit product that has component items.',
    )
    is_kit_component = fields.Boolean(
        string='Is Kit Component',
        default=False,
        help='This line is a component of a kit product.',
    )
    kit_parent_id = fields.Many2one(
        'sale.order.line',
        string='Kit Parent',
        ondelete='cascade',
        help='The parent kit line this component belongs to.',
    )
    bom_id = fields.Many2one(
        'otk.pharma.bom',
        string='BOM',
        readonly=True,
        help='BOM definition for this kit or component line.',
    )
    kit_component_line_ids = fields.One2many(
        'sale.order.line',
        'kit_parent_id',
        string='Kit Components',
    )
    kit_component_count = fields.Integer(
        string='Kit Component Count',
        compute='_compute_kit_component_count',
    )
    kit_price_breakdown = fields.Text(
        string='Kit Price Breakdown',
        compute='_compute_kit_price_breakdown',
        help='Auto-calculated from component prices based on the partner pricelist.',
    )

    @api.depends('kit_component_line_ids')
    def _compute_kit_component_count(self):
        for line in self:
            line.kit_component_count = len(line.kit_component_line_ids)

    # ── Kit Price Computation ────────────────────────────────────────────────

    def _compute_kit_price_breakdown(self):
        for line in self:
            if line.is_kit_line and line.bom_id and line.product_uom_qty > 0:
                breakdown = line._get_kit_price_from_components()
                line.kit_price_breakdown = breakdown['breakdown_text']
            else:
                line.kit_price_breakdown = False

    def _get_kit_price_from_components(self):
        """
        Calculate kit price by summing component prices from the partner's pricelist.
        For fixed quantity components (is_fixed_quantity=True), the quantity is NOT multiplied by kit qty.
        For scalable components, the quantity IS multiplied by kit qty.
        Returns dict with: total_price, breakdown_text, component_prices
        """
        self.ensure_one()
        if not self.bom_id or not self.product_uom_qty:
            return {'total_price': 0.0, 'breakdown_text': '', 'component_prices': {}}

        order = self.order_id
        partner = order.partner_id
        currency = order.currency_id
        pricelist = partner.property_product_pricelist
        total = 0.0
        lines = []

        # Collect all component products and their quantities
        products = self.bom_id.bom_line_ids.mapped('product_id')
        qty_map = {}  # product_id -> total qty needed

        for bom_line in self.bom_id.bom_line_ids:
            if bom_line.is_fixed_quantity:
                # Fixed quantity: use as-is, NOT multiplied by kit quantity
                qty = bom_line.product_qty
            else:
                # Scalable quantity: multiply by kit quantity
                qty = bom_line.product_qty * self.product_uom_qty
            qty_map[bom_line.product_id.id] = qty

        # Get component prices - use list prices directly.
        # Pricelist-based component pricing is complex and error-prone across Odoo versions.
        # The kit price is based on component lst_price * qty.
        price_results = {p.id: p.lst_price for p in products}

        for bom_line in self.bom_id.bom_line_ids:
            qty = qty_map[bom_line.product_id.id]
            unit_price = price_results.get(bom_line.product_id.id, bom_line.product_id.lst_price)
            line_total = unit_price * qty
            total += line_total

            qty_label = ' (fixed)' if bom_line.is_fixed_quantity else ''
            lines.append(
                '  • %s × %s %s @ %s = %s%s' % (
                    bom_line.product_qty,
                    bom_line.product_id.display_name,
                    bom_line.product_uom_id.name,
                    currency.round(unit_price),
                    currency.round(line_total),
                    qty_label,
                )
            )

        breakdown_text = 'Kit Components:\n' + '\n'.join(lines) if lines else ''
        breakdown_text += '\nKit Total: %s' % currency.round(total)

        return {
            'total_price': total,
            'breakdown_text': breakdown_text,
            'component_prices': price_results,
        }

    @api.depends('product_id', 'product_uom', 'product_uom_qty',
             'bom_id', 'bom_id.bom_line_ids', 'bom_id.bom_line_ids.product_id',
             'bom_id.bom_line_ids.product_qty', 'bom_id.bom_line_ids.is_fixed_quantity',
             'order_id.partner_id', 'order_id.pricelist_id')
    def _compute_price_unit(self):
        """
        Kit line pricing flow:
        1. Sum components (fixed qty respected) → component_total
        2. Derive unit base price = component_total / kit_qty
        3. Detect pricelist factor by comparing pricelist price vs lst_price
            on the kit product - this gives us the multiplier (e.g. 1.1 for +10%)
        4. Apply that factor to our component-based unit price
        5. Fall back to component unit price if no pricelist or lst_price is zero

        Non-kit lines: untouched by super().
        """
        # Sync virtual-state flags before super() runs
        for line in self:
            if line.product_id.otk_pharma_bom_id:
                if not line.is_kit_line:
                    line.is_kit_line = True
                if not line.bom_id:
                    line.bom_id = line.product_id.otk_pharma_bom_id

        # Standard Odoo pricing for non-kit lines
        super()._compute_price_unit()

        # Override kit lines
        for line in self:
            effective_bom = line.bom_id or line.product_id.otk_pharma_bom_id
            if not effective_bom:
                continue

            qty = line.product_uom_qty or 1.0
            currency = line.order_id.currency_id
            pricelist = line.order_id.pricelist_id
            product = line.product_id

            # ── Step 1 & 2: Component sum → base unit price ───────────────────────
            breakdown = line._get_kit_price_from_components()
            component_total = breakdown['total_price']       # e.g. 1305.0
            base_unit_price = component_total / qty          # e.g. 65.25

            # ── Step 3: Derive pricelist factor from kit product ──────────────────
            # We ask the pricelist what it would charge for the kit product at this
            # qty, then compare to lst_price to extract the factor (e.g. 1.1).
            # This works for all rule types: % discount, fixed, formula.
            # For fixed-price rules the factor would replace our base entirely,
            # which is the correct behaviour - a fixed pricelist rule means the
            # client negotiated a flat kit price regardless of components.
            pricelist_factor = 1.0
            if pricelist and product.lst_price:
                try:
                    pricelist_unit_price = pricelist._get_product_price(
                        product,
                        qty,
                        currency=currency,
                        date=line.order_id.date_order or fields.Date.today(),
                        uom=line.product_uom,
                    )
                    # Factor = what pricelist charges / what lst_price says
                    # e.g. lst_price=65.25, pricelist says 71.775 → factor=1.1
                    pricelist_factor = pricelist_unit_price / product.lst_price
                except Exception:
                    pricelist_factor = 1.0

            # ── Step 4: Apply factor to our component-based unit price ────────────
            final_unit_price = currency.round(base_unit_price * pricelist_factor)

            # ── Step 5: Write ─────────────────────────────────────────────────────
            line.price_unit = final_unit_price
            line.technical_price_unit = final_unit_price

    @api.onchange('product_id')
    def _onchange_product_id_detect_kit(self):
        """Detect kit products immediately when added to order and set bom_id + is_kit_line."""
        for line in self:
            if line.product_id and line.product_id.otk_pharma_bom_id:
                line.is_kit_line = True
                line.bom_id = line.product_id.otk_pharma_bom_id
            elif not line.product_id:
                line.is_kit_line = False
                line.bom_id = False
