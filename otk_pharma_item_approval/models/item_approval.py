# otk_pharma_item_approval/models/item_approval.py

import random
import hashlib
from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class OtkPharmaItemApproval(models.Model):
    _name = 'otk.pharma.item.approval'
    _description = 'Pharmacy Item Approval Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # ── Core Links ────────────────────────────────────────────────────────────
    order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        required=True,
        ondelete='cascade',
        tracking=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Pharmacy',
        required=True,
        tracking=True,
    )

    # ── Status ────────────────────────────────────────────────────────────────
    state = fields.Selection([
        ('pending',  'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired',  'Expired'),
    ], string='Status', default='pending', tracking=True)

    # ── Approval Metadata ─────────────────────────────────────────────────────
    approved_by = fields.Many2one(
        'res.users',
        string='Approved By',
        readonly=True,
    )
    approval_date = fields.Datetime(
        string='Approval Date',
        readonly=True,
    )
    rejection_reason = fields.Text(
        string='Rejection Reason',
    )
    expiry_date = fields.Datetime(
        string='Auth Code Expiry',
        readonly=True,
    )

    # ── Auth Code (hashed) ────────────────────────────────────────────────────
    # We never store the plaintext code. Only the SHA-256 hash is stored.
    # The plaintext is generated, emailed, then discarded.
    auth_code_hash = fields.Char(
        string='Auth Code Hash',
        readonly=True,
        copy=False,
    )

    auth_code_plain = fields.Char(
        string='Auth Code (Temp)',
        readonly=True,
        copy=False,
        help='Temporary plaintext code — cleared immediately after email is sent.',
    )
    
    # ── Controlled Items Summary (for admin review) ───────────────────────────
    controlled_item_names = fields.Char(
        string='Controlled Items',
        compute='_compute_controlled_item_names',
        store=True,
    )

    @api.depends('order_id.order_line.product_id.x_requires_approval')
    def _compute_controlled_item_names(self):
        for rec in self:
            if not rec.order_id:
                rec.controlled_item_names = ''
                continue
            names = rec.order_id.order_line.filtered(
                lambda l: l.product_id.x_requires_approval
            ).mapped('product_id.name')
            rec.controlled_item_names = ', '.join(names) if names else ''

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_approve(self):
        """
        Called by the Approve button on the sale.order form or approval form.
        Generates a 6-digit one-time auth code, stores its hash,
        sets expiry to 24 hours, and emails the code to the pharmacy.
        """
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_('Only pending approvals can be approved.'))

        # Generate a 6-digit plaintext code
        plaintext_code = str(random.randint(100000, 999999))

        # Hash it — we never store the plaintext long term
        code_hash = hashlib.sha256(plaintext_code.encode()).hexdigest()

        self.write({
            'state': 'approved',
            'auth_code_hash': code_hash,
            'approved_by': self.env.uid,
            'approval_date': fields.Datetime.now(),
            'expiry_date': fields.Datetime.now() + timedelta(hours=24),
        })

        # Build and send the email entirely in Python
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        approve_url = '%s/pharmacy/order/%d/approve' % (base_url, self.order_id.id)
        company_email = self.order_id.company_id.email or self.env.user.email

        body_html = """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #1a3c5e;">Your Order Has Been Approved</h2>
            <p>Your order has been reviewed and approved. Use the authorisation
            code below to confirm your order.</p>

            <div style="text-align:center; margin: 30px 0;">
                <div style="display:inline-block; padding:20px 40px;
                            background:#f0f4f8; border:2px solid #1a3c5e;
                            border-radius:8px;">
                    <p style="margin:0 0 8px 0; color:#666; font-size:13px;">
                        AUTHORISATION CODE
                    </p>
                    <p style="margin:0; font-size:36px; font-weight:bold;
                              letter-spacing:8px; color:#1a3c5e;">
                        %s
                    </p>
                </div>
            </div>

            <p style="color:#e74c3c; font-size:13px;">
                &#9888; This code expires in 24 hours and can only be used once.
            </p>

            <table style="width:100%%; border-collapse:collapse; margin: 20px 0;">
                <tr style="background:#f0f4f8;">
                    <td style="padding:8px 12px; font-weight:bold;">Order</td>
                    <td style="padding:8px 12px;">%s</td>
                </tr>
                <tr>
                    <td style="padding:8px 12px; font-weight:bold;">Controlled Items</td>
                    <td style="padding:8px 12px;">%s</td>
                </tr>
                <tr style="background:#f0f4f8;">
                    <td style="padding:8px 12px; font-weight:bold;">Code Expires</td>
                    <td style="padding:8px 12px;">%s</td>
                </tr>
            </table>

            <a href="%s"
               style="display:inline-block; padding:10px 20px; background:#1a3c5e;
                      color:#ffffff; text-decoration:none; border-radius:4px;">
                Enter Code &amp; Confirm Order
            </a>
        </div>
        """ % (
            plaintext_code,
            self.order_id.name,
            self.controlled_item_names or '',
            str(self.expiry_date),
            approve_url,
        )

        mail_values = {
            'subject': 'Your Authorisation Code for Order %s' % self.order_id.name,
            'email_from': company_email,
            'email_to': self.partner_id.email,
            'body_html': body_html,
            'auto_delete': True,
        }

        mail = self.env['mail.mail'].sudo().create(mail_values)
        try:
            mail.send(auto_commit=False)
            self.message_post(
                body=_('Auth code sent to %s - %s') % (self.partner_id.email, plaintext_code)
            )
        except Exception as e:
            self.message_post(
                body=_('Failed to send auth code: %s') % str(e)
            )

        return True

    def action_resend_code(self):
        """
        Generates a new auth code and resends it to the pharmacy.
        Called from the backend Resend Code button or portal resend link.
        Replaces the existing hash with the new code's hash.
        """
        self.ensure_one()
        if self.state not in ('approved', 'expired'):
            raise UserError(_('Can only resend code for approved or expired approvals.'))

        # Generate a fresh 6-digit code
        plaintext_code = str(random.randint(100000, 999999))
        code_hash = hashlib.sha256(plaintext_code.encode()).hexdigest()

        self.write({
            'state': 'approved',  # reactivate if expired
            'auth_code_hash': code_hash,
            'expiry_date': fields.Datetime.now() + timedelta(hours=24),
        })

        # Build and send email with new code
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        approve_url = '%s/pharmacy/order/%d/approve' % (base_url, self.order_id.id)
        company_email = self.order_id.company_id.email or self.env.user.email

        body_html = """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #1a3c5e;">Your New Authorisation Code</h2>
            <p>A new authorisation code has been generated for your order.
            Your previous code is no longer valid.</p>

            <div style="text-align:center; margin: 30px 0;">
                <div style="display:inline-block; padding:20px 40px;
                            background:#f0f4f8; border:2px solid #1a3c5e;
                            border-radius:8px;">
                    <p style="margin:0 0 8px 0; color:#666; font-size:13px;">
                        AUTHORISATION CODE
                    </p>
                    <p style="margin:0; font-size:36px; font-weight:bold;
                              letter-spacing:8px; color:#1a3c5e;">
                        %s
                    </p>
                </div>
            </div>

            <p style="color:#e74c3c; font-size:13px;">
                &#9888; This code expires in 24 hours and can only be used once.
            </p>

            <table style="width:100%%; border-collapse:collapse; margin: 20px 0;">
                <tr style="background:#f0f4f8;">
                    <td style="padding:8px 12px; font-weight:bold;">Order</td>
                    <td style="padding:8px 12px;">%s</td>
                </tr>
                <tr>
                    <td style="padding:8px 12px; font-weight:bold;">Controlled Items</td>
                    <td style="padding:8px 12px;">%s</td>
                </tr>
                <tr style="background:#f0f4f8;">
                    <td style="padding:8px 12px; font-weight:bold;">Code Expires</td>
                    <td style="padding:8px 12px;">%s</td>
                </tr>
            </table>

            <a href="%s"
               style="display:inline-block; padding:10px 20px; background:#1a3c5e;
                      color:#ffffff; text-decoration:none; border-radius:4px;">
                Enter Code &amp; Confirm Order
            </a>
        </div>
        """ % (
            plaintext_code,
            self.order_id.name,
            self.controlled_item_names or '',
            str(self.expiry_date),
            approve_url,
        )

        mail_values = {
            'subject': 'New Authorisation Code for Order %s' % self.order_id.name,
            'email_from': company_email,
            'email_to': self.partner_id.email,
            'body_html': body_html,
            'auto_delete': True,
        }

        mail = self.env['mail.mail'].sudo().create(mail_values)
        try:
            mail.send(auto_commit=False)
            self.message_post(
                body=_('New auth code resent to %s - %s') % (self.partner_id.email, plaintext_code)
            )
        except Exception as e:
            self.message_post(
                body=_('Failed to resend auth code: %s') % str(e)
            )

        return True

    def action_reject(self):
        """
        Called by the Reject button on the sale.order form.
        Sets the approval to rejected and resets the order to draft.
        """
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_('Only pending approvals can be rejected.'))

        self.write({'state': 'rejected'})

        # Reset the order back to draft so the pharmacy can edit and resubmit
        self.order_id.write({'state': 'draft'})

        # Remove the pending_approval flag from the order
        self.order_id.write({'x_approval_id': False})

        # Send rejection notification email to pharmacy
        template = self.env.ref(
            'otk_pharma_item_approval.email_template_approval_rejected',
            raise_if_not_found=False,
        )
        if template:
            template.send_mail(self.id, force_send=True)

        return True

    def verify_auth_code(self, entered_code):
        """
        Called from the portal controller when the pharmacy submits the code.
        Returns True if the code matches and has not expired, False otherwise.
        """
        self.ensure_one()

        if self.state != 'approved':
            return False

        if self.expiry_date and fields.Datetime.now() > self.expiry_date:
            self.write({'state': 'expired'})
            return False

        entered_hash = hashlib.sha256(entered_code.strip().encode()).hexdigest()
        if entered_hash != self.auth_code_hash:
            return False

        # Code is valid — reset order to draft first so action_confirm() accepts it
        self.order_id.write({'state': 'draft'})

        # Now confirm the order — skip_approval_check prevents re-triggering our hook
        self.order_id.with_context(skip_approval_check=True).action_confirm()

        # Clear the hash so it cannot be reused
        self.write({'auth_code_hash': False})

        return True

    def action_expire_pending(self):
        """
        Called by the scheduled cron job (ir.cron).
        Finds all approved approvals whose expiry_date has passed
        and marks them as expired.
        """
        expired = self.search([
            ('state', '=', 'approved'),
            ('expiry_date', '<', fields.Datetime.now()),
        ])
        expired.write({'state': 'expired'})