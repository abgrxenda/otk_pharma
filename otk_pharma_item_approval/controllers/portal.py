# otk_pharma_item_approval/controllers/portal.py

import base64
from odoo import http, _
from odoo.http import request
from odoo.exceptions import AccessError, MissingError
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.sale.controllers.portal import CustomerPortal as SaleCustomerPortal


class ItemApprovalPortal(SaleCustomerPortal):

    # ── Override /my/orders to include pending_approval + pending_prescription ─

    def _prepare_orders_domain(self, partner):
        """
        Extend native domain to include pending_approval and pending_prescription
        orders in /my/orders.
        """
        return [
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['sale', 'pending_approval', 'pending_prescription']),
        ]

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        SaleOrder = request.env['sale.order']
        if 'pending_approval_count' in counters:
            values['pending_approval_count'] = SaleOrder.search_count([
                ('partner_id', 'child_of', [partner.commercial_partner_id.id]),
                ('state', '=', 'pending_approval'),
            ]) if SaleOrder.has_access('read') else 0
        if 'pending_prescription_count' in counters:
            values['pending_prescription_count'] = SaleOrder.search_count([
                ('partner_id', 'child_of', [partner.commercial_partner_id.id]),
                ('state', '=', 'pending_prescription'),
            ]) if SaleOrder.has_access('read') else 0
        return values

    # ── Prescription Upload Page ──────────────────────────────────────────────

    @http.route(
        '/pharmacy/order/<int:order_id>/prescription',
        type='http',
        auth='user',
        website=True,
        methods=['GET', 'POST'],
    )
    def order_prescription_page(self, order_id, **kwargs):
        """
        GET  — renders the prescription upload form for the given order.
        POST — validates uploaded files and saves them.
        """
        # ── Fetch and validate the order ──────────────────────────────────────
        try:
            order = request.env['sale.order'].sudo().browse(order_id)
            if not order.exists():
                return request.redirect('/my/orders')

            # Ensure the order belongs to the logged-in user's partner
            if order.partner_id != request.env.user.partner_id:
                return request.redirect('/my/orders')

        except Exception:
            return request.redirect('/my/orders')

        # ── Only show this page for orders in pending_prescription state ──────
        if order.state != 'pending_prescription':
            return request.redirect('/my/orders/%d' % order_id)

        # Get prescription upload lines for this order
        prescription_lines = order.sudo().x_prescription_line_ids.filtered(
            lambda r: r.product_id.x_requires_prescription
        )

        if not prescription_lines:
            return request.redirect('/my/orders/%d' % order_id)

        # ── POST: process uploaded files ──────────────────────────────────────
        if request.httprequest.method == 'POST':
            error = None
            success = None
            files_uploaded = 0

            for line in prescription_lines:
                field_name = 'prescription_%s' % line.id
                file_data = request.httprequest.files.get(field_name)

                if file_data and file_data.filename and file_data.read():
                    file_data.seek(0)
                    file_content = file_data.read()
                    line.sudo().write({
                        'prescription_file': base64.b64encode(file_content),
                        'prescription_filename': file_data.filename,
                    })
                    files_uploaded += 1

            if files_uploaded > 0:
                # Check if all prescriptions are now uploaded
                # Odoo auto-recomputes the field when accessed
                if order.sudo().x_all_prescriptions_uploaded:
                    success = _(
                        'All prescriptions uploaded successfully! '
                        'Proceeding to the next step...'
                    )
                    # Move to next step: approval or confirmation
                    return request.redirect(
                        '/pharmacy/order/%d/after-prescription' % order_id
                    )
                else:
                    success = _(
                        '%d prescription(s) uploaded. Please upload all required '
                        'prescriptions to proceed.'
                    ) % files_uploaded
            else:
                error = _('Please select at least one file to upload.')

            return request.render(
                'otk_pharma_item_approval.portal_order_prescription',
                self._prescription_page_values(
                    order, prescription_lines,
                    error=error, success=success,
                ),
            )

        # ── GET: render the form ──────────────────────────────────────────────
        return request.render(
            'otk_pharma_item_approval.portal_order_prescription',
            self._prescription_page_values(order, prescription_lines),
        )

    @http.route(
        '/pharmacy/order/<int:order_id>/after-prescription',
        type='http',
        auth='user',
        website=True,
    )
    def order_after_prescription(self, order_id, **kwargs):
        """
        Redirect after all prescriptions are uploaded.
        If order also needs approval → redirect to auth code page.
        Otherwise → confirm the order.
        """
        try:
            order = request.env['sale.order'].sudo().browse(order_id)
            if not order.exists():
                return request.redirect('/my/orders')
            if order.partner_id != request.env.user.partner_id:
                return request.redirect('/my/orders')
        except Exception:
            return request.redirect('/my/orders')

        if order.x_has_controlled_items:
            # Order needs approval — if not yet in pending_approval, trigger it
            if order.state == 'pending_prescription':
                order.with_context(skip_prescription_check=True).action_confirm()
            return request.redirect('/pharmacy/order/%d/approve' % order_id)
        else:
            # No approval needed — confirm the order
            order.with_context(skip_prescription_check=True).action_confirm()
            return request.redirect('/my/orders/%d' % order_id)

    @http.route(
        ['/my/prescription-uploads', '/my/prescription-uploads/page/<int:page>'],
        type='http',
        auth='user',
        website=True,
    )
    def portal_prescription_uploads(self, page=1, **kwargs):
        partner = request.env.user.partner_id
        domain = [
            ('partner_id', 'child_of', [partner.commercial_partner_id.id]),
            ('state', '=', 'pending_prescription'),
        ]
        orders = request.env['sale.order'].sudo().search(
            domain, order='date_order desc'
        )
        values = {
            'orders': orders,
            'page_name': 'prescription_uploads',
            'default_url': '/my/prescription-uploads',
        }
        return request.render(
            'otk_pharma_item_approval.portal_prescription_uploads',
            values,
        )

    # ── Auth Code Entry Page ──────────────────────────────────────────────────

    @http.route(
        '/pharmacy/order/<int:order_id>/approve',
        type='http',
        auth='user',
        website=True,
        methods=['GET', 'POST'],
    )
    def order_approval_page(self, order_id, **kwargs):
        """
        GET  — renders the auth code entry form for the given order.
        POST — validates the submitted code and either confirms the order
               or returns the form with an error message.
        """
        # ── Fetch and validate the order ──────────────────────────────────────
        try:
            order = request.env['sale.order'].sudo().browse(order_id)
            if not order.exists():
                return request.redirect('/my/orders')

            # Ensure the order belongs to the logged-in user's partner
            if order.partner_id != request.env.user.partner_id:
                return request.redirect('/my/orders')

        except Exception:
            return request.redirect('/my/orders')

        # ── Only show this page for orders in pending_approval state ──────────
        if order.state != 'pending_approval':
            return request.redirect('/my/orders/%d' % order_id)

        approval = order.x_approval_id

        if not approval:
            return request.redirect('/my/orders/%d' % order_id)

        # ── POST: process submitted auth code ─────────────────────────────────
        if request.httprequest.method == 'POST':
            entered_code = kwargs.get('auth_code', '').strip()

            if not entered_code:
                return request.render(
                    'otk_pharma_item_approval.portal_order_approve',
                    self._approval_page_values(order, approval, error=_(
                        'Please enter the authorisation code.'
                    ))
                )

            # Delegate verification to the model
            success = approval.sudo().verify_auth_code(entered_code)

            if success:
                return request.redirect('/my/orders/%d?approved=1' % order_id)
            else:
                if approval.state == 'expired':
                    error_msg = _(
                        'This authorisation code has expired. '
                        'Please contact the pharmacy to request a new one.'
                    )
                elif approval.state == 'rejected':
                    error_msg = _(
                        'This order has been rejected. '
                        'Please contact the pharmacy for further assistance.'
                    )
                else:
                    error_msg = _(
                        'Invalid authorisation code. Please check the code '
                        'in your email and try again.'
                    )

                resent = kwargs.get('resent')
                return request.render(
                    'otk_pharma_item_approval.portal_order_approve',
                    self._approval_page_values(order, approval, resent=resent),
                )

        # ── GET: render the form ──────────────────────────────────────────────
        return request.render(
            'otk_pharma_item_approval.portal_order_approve',
            self._approval_page_values(order, approval),
        )

    @http.route(
        '/pharmacy/order/<int:order_id>/resend-code',
        type='http',
        auth='user',
        website=True,
        methods=['GET'],
    )
    def order_resend_code(self, order_id, **kwargs):
        """
        Resends a new auth code to the pharmacy for the given order.
        Only accessible by the order's own portal user.
        """
        try:
            order = request.env['sale.order'].sudo().browse(order_id)
            if not order.exists():
                return request.redirect('/my/orders')
            if order.partner_id != request.env.user.partner_id:
                return request.redirect('/my/orders')
        except Exception:
            return request.redirect('/my/orders')

        if order.state != 'pending_approval' or not order.x_approval_id:
            return request.redirect('/my/orders/%d' % order_id)

        try:
            order.x_approval_id.sudo().action_resend_code()
        except Exception:
            pass

        return request.redirect(
            '/pharmacy/order/%d/approve?resent=1' % order_id
        )

    @http.route(
        ['/my/pending-approvals', '/my/pending-approvals/page/<int:page>'],
        type='http',
        auth='user',
        website=True,
    )
    def portal_pending_approvals(self, page=1, **kwargs):
        partner = request.env.user.partner_id
        domain = [
            ('partner_id', 'child_of', [partner.commercial_partner_id.id]),
            ('state', '=', 'pending_approval'),
        ]
        orders = request.env['sale.order'].sudo().search(domain, order='date_order desc')
        values = {
            'orders': orders,
            'page_name': 'pending_approvals',
            'default_url': '/my/pending-approvals',
        }
        return request.render(
            'otk_pharma_item_approval.portal_pending_approvals',
            values,
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _approval_page_values(self, order, approval, error=None, resent=None):
        return {
            'order': order,
            'approval': approval,
            'error': error,
            'resent': resent,
            'page_name': 'order_approve',
        }

    def _prescription_page_values(self, order, prescription_lines,
                                   error=None, success=None):
        return {
            'order': order,
            'prescription_lines': prescription_lines,
            'error': error,
            'success': success,
            'has_approval_items': order.x_has_controlled_items,
            'page_name': 'order_prescription',
        }


class ItemApprovalShopOverride(SaleCustomerPortal):
    """Override /shop/confirmation to redirect for pending_prescription
    or pending_approval orders."""

    @http.route('/shop/confirmation', type='http', auth='user', website=True)
    def shop_confirmation(self, **post):
        # Check the most recent order for this partner
        SaleOrder = request.env['sale.order'].sudo()
        last_order = SaleOrder.search([
            ('partner_id', '=', request.env.user.partner_id.commercial_partner_id.id),
        ], order='id desc', limit=1)

        if last_order:
            if last_order.state == 'pending_prescription':
                return request.redirect(
                    '/pharmacy/order/%d/prescription' % last_order.id
                )
            if last_order.state == 'pending_approval':
                return request.redirect(
                    '/pharmacy/order/%d/approve' % last_order.id
                )

        # Fall through to Odoo's native handler
        try:
            return super().shop_confirmation(**post)
        except AttributeError:
            # Native method not found — try the original website_sale flow
            return request.redirect('/my/orders')
