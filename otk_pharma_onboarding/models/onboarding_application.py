# otk_pharma_onboarding/models/onboarding_application.py

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import html_escape
import logging

_logger = logging.getLogger(__name__)

class OtkPharmaOnboardingApplication(models.Model):
    _name = 'otk.pharma.onboarding.application'
    _description = 'Pharmacy Onboarding Application'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # ── Basic Info ────────────────────────────────────────────
    name = fields.Char(
        string='Pharmacy Name',
        required=True,
        tracking=True
    )
    contact_name = fields.Char(
        string='Contact Person',
        required=True
    )
    email = fields.Char(
        string='Email',
        required=True,
        tracking=True
    )
    phone = fields.Char(
        string='Phone',
        required=True
    )
    street = fields.Char(string='Street')
    city = fields.Char(string='City')
    province = fields.Char(string='Province')
    postal_code = fields.Char(string='Postal Code')

    # ── License & Documents ───────────────────────────────────
    pharmacy_license_number = fields.Char(
        string='Pharmacy License Number',
        required=True
    )
    pharmacy_license_doc = fields.Binary(
        string='Pharmacy License Document'
    )
    pharmacy_license_doc_filename = fields.Char(
        string='License Filename'
    )

    # ── Contract & Signature ──────────────────────────────────
    contract_signed = fields.Boolean(
        string='Contract Signed',
        default=False,
        tracking=True
    )
    contract_signed_date = fields.Datetime(
        string='Contract Signed Date',
        readonly=True
    )
    contract_signature = fields.Binary(
        string='Digital Signature'
    )
    contract_pdf = fields.Binary(
        string='Signed Contract PDF',
        readonly=True
    )
    contract_pdf_filename = fields.Char(
        string='Contract PDF Filename'
    )

    # ── Commercial Settings (set by admin on activation) ──────
    delivery_fee = fields.Monetary(
        string='Delivery Fee',
        currency_field='currency_id',
        default=0.0,
        help='Flat delivery fee added to every order for this partner'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Discount Tier',
        help='Pricelist assigned to this partner (Gold, Silver, Bronze, etc.)'
    )

    # ── Status ────────────────────────────────────────────────
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted — Pending Review'),
        ('approved', 'Approved — Active'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)

    rejection_reason = fields.Text(
        string='Rejection Reason',
        help='Reason sent to the applicant in the rejection email'
    )

    # ── Link to created partner ───────────────────────────────
    partner_id = fields.Many2one(
        'res.partner',
        string='Created Partner',
        readonly=True,
        help='Set automatically when the application is approved and activated'
    )

    # ── Computed display name ─────────────────────────────────
    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, f"{rec.name} ({rec.email})"))
        return result

    # ── Actions ───────────────────────────────────────────────
    def action_approve(self):
        """
        Called by the Activate Account button in the backend.
        Creates a res.partner and portal user, then marks
        the application as approved.
        """
        self.ensure_one()

        if self.state != 'submitted':
            raise UserError(_('Only submitted applications can be approved.'))

        if not self.contract_signed:
            raise UserError(_('Cannot activate an account without a signed contract.'))

        # Create the partner
        partner = self.env['res.partner'].create({
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'street': self.street,
            'city': self.city,
            'state_id': False,
            'zip': self.postal_code,
            'is_company': True,
            'customer_rank': 1,
            'x_onboarding_state': 'active',
            'x_contract_signed': True,
            'x_contract_signed_date': self.contract_signed_date,
            'x_contract_pdf': self.contract_pdf,
            'x_contract_pdf_filename': self.contract_pdf_filename,
            'x_pharmacy_license': self.pharmacy_license_doc,
            'x_pharmacy_license_filename': self.pharmacy_license_doc_filename,
            'x_delivery_fee': self.delivery_fee,
        })

        # Set pricelist separately — property field must be set after create
        if self.pricelist_id:
            partner.sudo().write({
                'property_product_pricelist': self.pricelist_id.id
            })

        # Grant portal access — Odoo 18 compatible
        user = self.env['res.users'].sudo().search([
            ('partner_id', '=', partner.id)
        ], limit=1)
        if not user:
            user = self.env['res.users'].sudo().create({
                'name': partner.name,
                'login': self.email,
                'email': self.email,
                'partner_id': partner.id,
                'groups_id': [(6, 0, [
                    self.env.ref('base.group_portal').id
                ])],
            })

        # Send Odoo's native "set your password" email — this is the correct
        # first-login flow when no password was set during registration
        try:
            user.sudo().action_reset_password()
        except Exception as e:
            _logger.warning('Password reset email failed: %s', e)


        # Create contact person as child of the partner
        self.env['res.partner'].create({
            'name': self.contact_name,
            'email': self.email,
            'phone': self.phone,
            'parent_id': partner.id,
            'type': 'contact',
        })

        # Link partner and update state
        self.write({
            'state': 'approved',
            'partner_id': partner.id,
        })

        # Link back from partner to this application
        partner.sudo().write({
            'x_onboarding_application_id': self.id,
        })

        # Send welcome email in Python to avoid Odoo 18 Jinja rendering issues
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        company = self.env.company
        body_html = """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #1a3c5e; padding: 30px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0;">Account Activated</h1>
            </div>
            <div style="padding: 30px;">
                <p style="font-size: 16px;">Dear <strong>%s</strong>,</p>
                <p>We are pleased to inform you that your B2B pharmacy account for
                <strong>%s</strong> has been reviewed and activated.</p>
                <p>You will receive a separate email shortly with a link to set your
                password and access the portal for the first time.</p>
                <p>Your registered email address is: <strong>%s</strong></p>
            </div>
            <div style="background: #f0f4f8; padding: 20px; text-align: center;
                        font-size: 12px; color: #666;">
                <p>If you have any questions, please contact us by replying to this email.</p>
                <p>%s &mdash; %s, %s</p>
            </div>
        </div>
        """ % (
            self.contact_name or self.name,
            self.name,
            self.email,
            company.name,
            company.street or '',
            company.city or '',
        )

        mail = self.env['mail.mail'].sudo().create({
            'subject': 'Your B2B Pharmacy Account Has Been Activated — Check Your Email to Set Password',
            'email_from': company.email or '',
            'email_to': self.email,
            'body_html': body_html,
            'auto_delete': True,
        })
        mail.send()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': partner.id,
            'view_mode': 'form',
        }

    def action_reject(self):
        """
        Opens a wizard to enter rejection reason,
        then sends rejection email.
        """
        self.ensure_one()
        if self.state not in ('draft', 'submitted'):
            raise UserError(_('This application cannot be rejected in its current state.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Application'),
            'res_model': 'otk.pharma.onboarding.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_application_id': self.id},
        }

    def action_reset_to_draft(self):
        self.ensure_one()
        self.write({'state': 'draft'})


class OtkPharmaOnboardingRejectWizard(models.TransientModel):
    """
    Small popup wizard that captures the rejection reason
    before sending the rejection email.
    """
    _name = 'otk.pharma.onboarding.reject.wizard'
    _description = 'Reject Onboarding Application'

    application_id = fields.Many2one(
        'otk.pharma.onboarding.application',
        string='Application',
        required=True
    )
    rejection_reason = fields.Text(
        string='Rejection Reason',
        required=True,
        help='This text will be included in the rejection email sent to the applicant'
    )

    def action_confirm_reject(self):
        self.ensure_one()
        self.application_id.write({
            'state': 'rejected',
            'rejection_reason': self.rejection_reason,
        })

        # Send rejection email
        application = self.application_id
        company = self.env.company
        body_html = """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #c0392b; padding: 30px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0;">Application Update</h1>
            </div>
            <div style="padding: 30px;">
                <p style="font-size: 16px;">Dear <strong>%s</strong>,</p>
                <p>Thank you for your interest in becoming a B2B partner with
                <strong>%s</strong>.</p>
                <p>After reviewing your application for <strong>%s</strong>,
                we are unable to approve your account at this time.</p>
                <div style="background: #fff3f3; border-left: 4px solid #c0392b;
                            padding: 15px; margin: 20px 0;">
                    <strong>Reason:</strong><br/>
                    %s
                </div>
                <p>If you have any questions or would like to discuss this further,
                please contact us by replying to this email.</p>
            </div>
            <div style="background: #f0f4f8; padding: 20px; text-align: center;
                        font-size: 12px; color: #666;">
                <p>%s &mdash; %s, %s</p>
            </div>
        </div>
        """ % (
            html_escape(application.contact_name or application.name),
            html_escape(company.name),
            html_escape(application.name),
            html_escape(self.rejection_reason or 'Please contact us for further details.'),
            html_escape(company.name),
            html_escape(company.street or ''),
            html_escape(company.city or ''),
        )

        mail = self.env['mail.mail'].sudo().create({
            'subject': 'Update on Your B2B Pharmacy Application',
            'email_from': company.email or '',
            'email_to': application.email,
            'body_html': body_html,
            'auto_delete': True,
        })
        mail.send()

        return {'type': 'ir.actions.act_window_close'}