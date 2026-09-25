# otk_pharma_onboarding/models/res_partner.py

from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ── Onboarding State ──────────────────────────────────────
    x_onboarding_state = fields.Selection([
        ('pending', 'Pending Review'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
    ],
        string='Account Status',
        default='pending',
        tracking=True,
        help='B2B pharmacy account status'
    )

    # ── Contract ──────────────────────────────────────────────
    x_contract_signed = fields.Boolean(
        string='Contract Signed',
        default=False
    )
    x_contract_signed_date = fields.Datetime(
        string='Contract Signed Date',
        readonly=True
    )
    x_contract_pdf = fields.Binary(
        string='Signed Contract PDF'
    )
    x_contract_pdf_filename = fields.Char(
        string='Contract PDF Filename'
    )

    # ── Pharmacy License ──────────────────────────────────────
    x_pharmacy_license = fields.Binary(
        string='Pharmacy License Document'
    )
    x_pharmacy_license_filename = fields.Char(
        string='License Filename'
    )

    # ── Commercial Settings ───────────────────────────────────
    x_delivery_fee = fields.Monetary(
        string='Delivery Fee',
        currency_field='currency_id',
        default=0.0,
        help='Flat delivery fee added automatically to every order for this partner'
    )

    # ── Onboarding Application link ───────────────────────────
    x_onboarding_application_id = fields.Many2one(
        'otk.pharma.onboarding.application',
        string='Onboarding Application',
        readonly=True
    )

    # ── Helper to check if partner is an active B2B pharmacy ──
    x_is_b2b_pharmacy = fields.Boolean(
        string='Is B2B Pharmacy Partner',
        compute='_compute_is_b2b_pharmacy',
        store=True
    )

    @api.depends('x_onboarding_state')
    def _compute_is_b2b_pharmacy(self):
        for rec in self:
            rec.x_is_b2b_pharmacy = rec.x_onboarding_state == 'active'