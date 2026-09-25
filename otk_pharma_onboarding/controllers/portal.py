# otk_pharma_onboarding/controllers/portal.py

from odoo import http, _
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
import logging

_logger = logging.getLogger(__name__)


class OtkPharmaOnboardingController(http.Controller):

    # ── Step 1: Registration Form ─────────────────────────────
    @http.route('/pharmacy/register', type='http', auth='public',
                website=True, sitemap=False)
    def pharmacy_register(self, **kwargs):
        """
        Public registration form.
        Anyone can access this page without logging in.
        """
        # If user is already logged in as a portal user, redirect to portal
        if request.env.user.has_group('base.group_portal'):
            return request.redirect('/my/home')

        # Get pricelists to show nothing on this page
        # (pricelist is set by admin, not chosen by applicant)
        return request.render(
            'otk_pharma_onboarding.portal_pharmacy_register',
            {'error': {}, 'form_data': {}}
        )

    @http.route('/pharmacy/register/submit', type='http', auth='public',
                website=True, sitemap=False, methods=['POST'])
    def pharmacy_register_submit(self, **kwargs):
        """
        Handles the registration form POST submission.
        Validates required fields and creates the application record.
        """
        error = {}
        required_fields = [
            'name', 'contact_name', 'email',
            'phone', 'pharmacy_license_number'
        ]

        # Validate required fields
        for field in required_fields:
            if not kwargs.get(field, '').strip():
                error[field] = True

        # Basic email format check
        email = kwargs.get('email', '').strip()
        if email and '@' not in email:
            error['email'] = True

        # Check if email already has a pending/approved application
        if not error.get('email'):
            existing = request.env[
                'otk.pharma.onboarding.application'
            ].sudo().search([
                ('email', '=', email),
                ('state', 'in', ['draft', 'submitted', 'approved'])
            ], limit=1)
            if existing:
                error['email_exists'] = True

        # If errors, re-render form with error indicators
        if error:
            return request.render(
                'otk_pharma_onboarding.portal_pharmacy_register',
                {'error': error, 'form_data': kwargs}
            )

        # Create the application record
        # Create the application record
        application = request.env[
            'otk.pharma.onboarding.application'
        ].sudo().create({
            'name': kwargs.get('name', '').strip(),
            'contact_name': kwargs.get('contact_name', '').strip(),
            'email': email,
            'phone': kwargs.get('phone', '').strip(),
            'street': kwargs.get('street', '').strip(),
            'city': kwargs.get('city', '').strip(),
            'province': kwargs.get('province', '').strip(),
            'postal_code': kwargs.get('postal_code', '').strip(),
            'pharmacy_license_number': kwargs.get(
                'pharmacy_license_number', ''
            ).strip(),
            'state': 'draft',
        })

        # Handle optional pharmacy license file upload
        import base64
        license_file = request.httprequest.files.get('pharmacy_license_doc')
        if license_file and license_file.filename:
            file_data = license_file.read()
            application.sudo().write({
                'pharmacy_license_doc': base64.b64encode(file_data),
                'pharmacy_license_doc_filename': license_file.filename,
            })

        # Store application ID in session to use in contract step
        request.session['otk_pharma_application_id'] = application.id

        # Redirect to contract signing page
        return request.redirect('/pharmacy/contract')

    # ── Step 2: Contract Signing ──────────────────────────────
    @http.route('/pharmacy/contract', type='http', auth='public',
                website=True, sitemap=False)
    def pharmacy_contract(self, **kwargs):
        """
        Displays the contract with e-signature widget.
        Requires a valid application session.
        """
        application_id = request.session.get('otk_pharma_application_id')
        if not application_id:
            # No session - send back to registration
            return request.redirect('/pharmacy/register')

        application = request.env[
            'otk.pharma.onboarding.application'
        ].sudo().browse(application_id)

        if not application.exists():
            request.session.pop('otk_pharma_application_id', None)
            return request.redirect('/pharmacy/register')

        # Already signed - go to pending page
        if application.contract_signed:
            return request.redirect('/pharmacy/pending')

        return request.render(
            'otk_pharma_onboarding.portal_pharmacy_contract',
            {'application': application, 'error': {}}
        )

    @http.route('/pharmacy/contract/submit', type='http', auth='public',
                website=True, sitemap=False, methods=['POST'])
    def pharmacy_contract_submit(self, **kwargs):
        """
        Handles contract signature submission.
        Saves signature, marks contract as signed,
        and moves application to 'submitted' state.
        """
        application_id = request.session.get('otk_pharma_application_id')
        if not application_id:
            return request.redirect('/pharmacy/register')

        application = request.env[
            'otk.pharma.onboarding.application'
        ].sudo().browse(application_id)

        if not application.exists():
            return request.redirect('/pharmacy/register')

        signature = kwargs.get('signature', '').strip()

        if not signature:
            return request.render(
                'otk_pharma_onboarding.portal_pharmacy_contract',
                {
                    'application': application,
                    'error': {'signature': True}
                }
            )

        # Save signature and mark as signed
        # Signature comes as base64 data URI: "data:image/png;base64,XXX"
        # Strip the prefix if present
        if ',' in signature:
            signature = signature.split(',')[1]

        from odoo.fields import Datetime
        signed_date = Datetime.now()

        application.sudo().write({
            'contract_signature': signature,
            'contract_signed': True,
            'contract_signed_date': signed_date,
            'state': 'submitted',
        })

        # Notify admin that a new application has been submitted
        try:
            company = request.env.company
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            admin_group = request.env.ref('base.group_system')
            admin_user = request.env['res.users'].sudo().search([
                ('groups_id', 'in', admin_group.id),
                ('active', '=', True),
            ], limit=1)
            admin_email = admin_user.partner_id.email or company.email or ''
            admin_url = '%s/odoo/pharmacy-onboarding/%d' % (base_url, application.id)
            body_html = """
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: #1a3c5e; padding: 30px; text-align: center;">
                    <h1 style="color: #ffffff; margin: 0;">New B2B Application Submitted</h1>
                </div>
                <div style="padding: 30px;">
                    <p>A new pharmacy has completed registration and signed the contract.</p>
                    <table style="width:100%%; border-collapse: collapse; margin: 20px 0;">
                        <tr><td style="padding:8px; font-weight:bold; width:40%%;">Pharmacy Name</td>
                            <td style="padding:8px;">%s</td></tr>
                        <tr style="background:#f0f4f8;">
                            <td style="padding:8px; font-weight:bold;">Contact Person</td>
                            <td style="padding:8px;">%s</td></tr>
                        <tr><td style="padding:8px; font-weight:bold;">Email</td>
                            <td style="padding:8px;">%s</td></tr>
                        <tr style="background:#f0f4f8;">
                            <td style="padding:8px; font-weight:bold;">Phone</td>
                            <td style="padding:8px;">%s</td></tr>
                        <tr><td style="padding:8px; font-weight:bold;">City</td>
                            <td style="padding:8px;">%s</td></tr>
                        <tr style="background:#f0f4f8;">
                            <td style="padding:8px; font-weight:bold;">Signed</td>
                            <td style="padding:8px;">%s</td></tr>
                    </table>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="%s"
                           style="background: #1a3c5e; color: #ffffff; padding: 12px 30px;
                                  text-decoration: none; border-radius: 4px; font-size: 16px;">
                            Review Application
                        </a>
                    </div>
                </div>
            </div>
            """ % (
                application.name or '',
                application.contact_name or '',
                application.email or '',
                application.phone or '',
                application.city or '',
                signed_date.strftime('%Y-%m-%d %H:%M UTC'),
                admin_url,
            )
            request.env['mail.mail'].sudo().create({
                'subject': 'New B2B Application: %s' % (application.name or ''),
                'email_from': company.email or '',
                'email_to': admin_email,
                'body_html': body_html,
                'auto_delete': True,
            }).send()
        except Exception as e:
            _logger.warning('Admin notification email failed: %s', e)

        # Generate contract PDF and save it on the application
        try:
            report = request.env.ref(
                'otk_pharma_onboarding.action_report_contract_pdf'
            ).sudo()
            pdf_content, _ = report._render_qweb_pdf(
                'otk_pharma_onboarding.report_contract_pdf',
                [application.id]
            )
            import base64
            application.sudo().write({
                'contract_pdf': base64.b64encode(pdf_content),
                'contract_pdf_filename': f"contract_{application.id}.pdf",
            })
        except Exception as e:
            _logger.warning("Contract PDF generation failed: %s", str(e))
            # Non-blocking - application still submitted even if PDF fails

        # Clear session - no longer needed
        request.session.pop('otk_pharma_application_id', None)

        # Redirect to pending confirmation page
        return request.redirect('/pharmacy/pending')

    # ── Step 3: Pending Confirmation ──────────────────────────
    @http.route('/pharmacy/pending', type='http', auth='public',
                website=True, sitemap=False)
    def pharmacy_pending(self, **kwargs):
        """
        Thank you / pending review page shown after contract signing.
        No session required - anyone who lands here sees the message.
        """
        return request.render(
            'otk_pharma_onboarding.portal_pharmacy_pending', {}
        )

class OtkPharmaCheckout(http.Controller):

    @http.route('/shop/confirm_on_credit', type='http', auth='user',
                website=True, methods=['POST', 'GET'])
    def confirm_on_credit(self, **kwargs):
        order = request.website.sale_get_order()
        if not order:
            return request.redirect('/shop')

        partner = request.env.user.partner_id.commercial_partner_id

        if not partner.credit_limit:
            return request.redirect('/shop/payment')

        # Re-check credit limit server-side (never trust the button alone)
        unpaid = request.env['account.move'].sudo().search([
            ('partner_id', 'child_of', partner.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
        ])
        unpaid_total = sum(unpaid.mapped('amount_residual'))
        total_exposure = order.amount_total + unpaid_total

        if total_exposure > partner.credit_limit:
            return request.redirect('/shop/payment?credit_blocked=1')

        # Inject delivery fee if set on partner
        delivery_fee = partner.x_delivery_fee
        if delivery_fee and delivery_fee > 0:
            try:
                fee_product = request.env.ref(
                    'otk_pharma_onboarding.product_delivery_fee',
                    raise_if_not_found=True,
                ).sudo().product_variant_id

                existing = order.order_line.filtered(
                    lambda l: l.product_id == fee_product
                )
                if not existing:
                    request.env['sale.order.line'].sudo().create({
                        'order_id': order.id,
                        'product_id': fee_product.id,
                        'name': 'Delivery Fee',
                        'product_uom_qty': 1,
                        'price_unit': delivery_fee,
                        'tax_id': False,
                    })
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(
                    'Could not inject delivery fee: %s', e
                )

        order.sudo().action_confirm()

        if order.state == 'pending_approval':
            return request.redirect(
                '/pharmacy/order/%d/approve' % order.id
            )

        return request.redirect('/shop/confirmation')