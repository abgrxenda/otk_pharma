# otk_pharma_item_approval/models/sale_order.py

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # ── Custom States ─────────────────────────────────────────────────────────
    state = fields.Selection(
        selection_add=[
            ('pending_prescription', 'Pending Prescription'),
            ('pending_approval', 'Pending Approval'),
        ],
        ondelete={
            'pending_prescription': 'set default',
            'pending_approval': 'set default',
        },
    )

    # ── Link to Approval Record ───────────────────────────────────────────────
    x_approval_id = fields.Many2one(
        'otk.pharma.item.approval',
        string='Approval Request',
        readonly=True,
        copy=False,
    )

    x_controlled_item_names = fields.Char(
        string='Controlled Items',
        related='x_approval_id.controlled_item_names',
        readonly=True,
        store=False,
    )

    # ── Computed: does this order have any controlled items? ──────────────────
    x_has_controlled_items = fields.Boolean(
        string='Has Controlled Items',
        compute='_compute_has_controlled_items',
        store=True,
    )

    # ── Computed: does this order have any prescription-required items? ───────
    x_has_prescription_items = fields.Boolean(
        string='Has Prescription Items',
        compute='_compute_has_prescription_items',
        store=True,
    )

    # ── Prescription Upload Lines ─────────────────────────────────────────────
    x_prescription_line_ids = fields.One2many(
        'sale.order.prescription.upload',
        'order_id',
        string='Prescription Uploads',
    )

    x_prescription_uploaded_count = fields.Integer(
        string='Prescriptions Uploaded',
        compute='_compute_prescription_counts',
    )

    x_prescription_required_count = fields.Integer(
        string='Prescriptions Required',
        compute='_compute_prescription_counts',
    )

    x_all_prescriptions_uploaded = fields.Boolean(
        string='All Prescriptions Uploaded',
        compute='_compute_prescription_counts',
    )

    @api.depends('order_line.product_id.x_requires_approval')
    def _compute_has_controlled_items(self):
        for order in self:
            order.x_has_controlled_items = any(
                line.product_id.x_requires_approval
                for line in order.order_line
            )

    @api.depends('order_line.product_id.x_requires_prescription')
    def _compute_has_prescription_items(self):
        for order in self:
            order.x_has_prescription_items = any(
                line.product_id.x_requires_prescription
                for line in order.order_line
            )

    @api.depends('x_prescription_line_ids', 'x_prescription_line_ids.state',
                 'order_line.product_id.x_requires_prescription')
    def _compute_prescription_counts(self):
        for order in self:
            # Count distinct products requiring prescription on this order
            required_products = order.order_line.filtered(
                lambda l: l.product_id.x_requires_prescription
            ).mapped('product_id')
            order.x_prescription_required_count = len(required_products)

            # Count uploaded prescriptions for this order
            order.x_prescription_uploaded_count = len(
                order.x_prescription_line_ids.filtered(
                    lambda r: r.state == 'uploaded'
                )
            )

            order.x_all_prescriptions_uploaded = (
                order.x_prescription_uploaded_count >= order.x_prescription_required_count
                and order.x_prescription_required_count > 0
            )

    # ── Override action_confirm ───────────────────────────────────────────────

    def action_confirm(self):
        """
        Intercept order confirmation with two gates:
        1. Prescription upload gate - if any product requires a prescription
           and not all are uploaded, hold for prescription.
        2. Approval gate - if any product requires approval (controlled item),
           hold for auth code approval.
        Both gates can apply to the same order.
        """
        # If called from verify_auth_code(), bypass the check entirely
        if self.env.context.get('skip_approval_check'):
            return super().action_confirm()

        # If called after prescription upload, bypass prescription check
        if self.env.context.get('skip_prescription_check'):
            return self._confirm_after_prescription()

        for order in self:
            # Gate 1: Prescription check
            if order.x_has_prescription_items and not order.x_all_prescriptions_uploaded:
                order._hold_for_prescription()
                return True

            # Gate 2: Approval check
            if order.x_has_controlled_items:
                order._hold_for_approval()
                return True

        # No gates - confirm normally
        return super().action_confirm()

    def _hold_for_prescription(self):
        """
        Sets the order to pending_prescription state and creates
        prescription upload records for each product requiring one.
        """
        self.ensure_one()

        # Don't recreate upload records if they already exist
        existing_products = self.x_prescription_line_ids.mapped('product_id')

        # Find products needing prescription that don't have upload records yet
        prescription_lines = self.order_line.filtered(
            lambda l: l.product_id.x_requires_prescription
        )
        for line in prescription_lines:
            product = line.product_id
            if product not in existing_products:
                self.env['sale.order.prescription.upload'].create({
                    'order_id': self.id,
                    'product_id': product.id,
                    'state': 'pending',
                })

        self.write({'state': 'pending_prescription'})

    def _hold_for_approval(self):
        """
        Sets the order to pending_approval state and creates
        a otk.pharma.item.approval record. Immediately auto-approves
        and sends the auth code to the pharmacy.
        """
        self.ensure_one()

        # Prevent creating a duplicate approval if one already exists
        if self.x_approval_id and self.x_approval_id.state == 'pending':
            raise UserError(_(
                'This order already has a pending approval request.'
            ))

        # Create the approval record
        approval = self.env['otk.pharma.item.approval'].create({
            'order_id': self.id,
            'partner_id': self.partner_id.id,
            'state': 'pending',
        })

        # Set order state to pending_approval and link the approval record
        self.write({
            'state': 'pending_approval',
            'x_approval_id': approval.id,
        })

        # Auto-approve immediately - generates and emails the auth code
        approval.action_approve()

    def _confirm_after_prescription(self):
        """
        Called after all prescriptions have been uploaded.
        Now check if approval is also needed, or confirm directly.
        """
        for order in self:
            if order.x_has_controlled_items:
                order._hold_for_approval()
                return True
            # No approval needed - set back to draft then confirm
            order.state = 'draft'
        return super().action_confirm()

    # ── Approval Action Buttons (called from order form) ─────────────────────

    def action_approve_order(self):
        """
        Button on the sale.order form that delegates to the approval record.
        """
        self.ensure_one()
        if not self.x_approval_id:
            raise UserError(_('No approval request found for this order.'))
        self.x_approval_id.action_approve()

    def action_reject_order(self):
        """
        Button on the sale.order form that delegates to the approval record.
        """
        self.ensure_one()
        if not self.x_approval_id:
            raise UserError(_('No approval request found for this order.'))
        self.x_approval_id.action_reject()
