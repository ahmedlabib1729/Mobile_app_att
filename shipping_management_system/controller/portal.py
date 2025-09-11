# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from collections import OrderedDict
from odoo.osv.expression import OR, AND
from odoo.exceptions import AccessError, MissingError
import datetime

class ShipmentPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        user = request.env.user

        if 'shipment_count' in counters:
            shipment_count = request.env['shipment.order'].search_count([
                ('sender_id', '=', user.partner_id.id)
            ]) if request.env['shipment.order'].check_access_rights('read', raise_exception=False) else 0
            values['shipment_count'] = shipment_count

        return values

    def _prepare_portal_layout_values(self):
        """Include shipment count in portal layout"""
        values = super()._prepare_portal_layout_values()
        user = request.env.user

        values['shipment_count'] = request.env['shipment.order'].search_count([
            ('sender_id', '=', user.partner_id.id)
        ])

        return values

    @http.route(['/my/shipments', '/my/shipments/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_shipments(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        user = request.env.user
        ShipmentOrder = request.env['shipment.order']

        domain = [('sender_id', '=', user.partner_id.id)]

        # Archive groups
        archive_groups = self._get_archive_groups('shipment.order', domain) if values.get('my_details') else []

        # Filters
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'draft': {'label': _('Draft'), 'domain': [('state', '=', 'draft')]},
            'confirmed': {'label': _('Confirmed'), 'domain': [('state', '=', 'confirmed')]},
            'in_transit': {'label': _('In Transit'),
                           'domain': [('state', 'in', ['picked', 'in_transit', 'out_for_delivery'])]},
            'delivered': {'label': _('Delivered'), 'domain': [('state', '=', 'delivered')]},
            'cancelled': {'label': _('Cancelled'), 'domain': [('state', '=', 'cancelled')]},
        }

        # Sort by
        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'order_number': {'label': _('Order Number'), 'order': 'order_number'},
            'state': {'label': _('Status'), 'order': 'state'},
        }

        # Default sort and filter
        if not sortby:
            sortby = 'date'
        if not filterby:
            filterby = 'all'

        sort_order = searchbar_sortings[sortby]['order']
        filter_domain = searchbar_filters[filterby]['domain']

        if filter_domain:
            domain = AND([domain, filter_domain])

        # Date filter
        if date_begin and date_end:
            domain = AND([domain, [('create_date', '>', date_begin), ('create_date', '<=', date_end)]])

        # Count for pager
        shipment_count = ShipmentOrder.search_count(domain)

        # Pager
        pager = portal_pager(
            url="/my/shipments",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby},
            total=shipment_count,
            page=page,
            step=self._items_per_page
        )

        # Fetch records
        shipments = ShipmentOrder.search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'date': date_begin,
            'shipments': shipments,
            'page_name': 'shipment',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/shipments',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
        })

        return request.render("shipping_management_system.portal_my_shipments", values)

    def portal_my_invoices(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        user = request.env.user
        AccountMove = request.env['account.move']

        # حل مشكلة overdue_invoice_count
        values['overdue_invoice_count'] = 0
        values['bills'] = False  # أضف هذا أيضاً

        # Domain للفواتير الخاصة بالعميل
        domain = [
            ('move_type', '=', 'out_invoice'),
            ('partner_id', '=', user.partner_id.id),
            ('state', '!=', 'cancel')
        ]

        # Filters
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'draft': {'label': _('Draft'), 'domain': [('state', '=', 'draft')]},
            'posted': {'label': _('Confirmed'), 'domain': [('state', '=', 'posted')]},
            'paid': {'label': _('Paid'), 'domain': [('payment_state', '=', 'paid')]},
            'unpaid': {'label': _('Unpaid'), 'domain': [('payment_state', 'in', ['not_paid', 'partial'])]},
        }

        # Sort by
        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'invoice_date desc'},
            'due_date': {'label': _('Due Date'), 'order': 'invoice_date_due'},
            'amount': {'label': _('Amount'), 'order': 'amount_total desc'},
            'state': {'label': _('Status'), 'order': 'state'},
        }

        # Default sort and filter
        if not sortby:
            sortby = 'date'
        if not filterby:
            filterby = 'all'

        sort_order = searchbar_sortings[sortby]['order']
        filter_domain = searchbar_filters[filterby]['domain']

        if filter_domain:
            domain = domain + filter_domain

        # Date filter
        if date_begin and date_end:
            domain += [('invoice_date', '>', date_begin), ('invoice_date', '<=', date_end)]

        # Get invoices
        invoice_count = AccountMove.search_count(domain)

        # Pager
        pager = portal_pager(
            url="/my/invoices",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby},
            total=invoice_count,
            page=page,
            step=self._items_per_page
        )

        # Fetch records
        invoices = AccountMove.search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])

        # Calculate statistics بشكل آمن
        all_invoices = AccountMove.search([
            ('move_type', '=', 'out_invoice'),
            ('partner_id', '=', user.partner_id.id),
            ('state', '!=', 'cancel')
        ])

        # استخدم default values آمنة
        total_amount = sum(all_invoices.mapped('amount_total')) if all_invoices else 0
        paid_amount = sum(
            all_invoices.filtered(lambda i: i.payment_state == 'paid').mapped('amount_total')) if all_invoices else 0
        unpaid_invoices = all_invoices.filtered(
            lambda i: i.payment_state in ['not_paid', 'partial']) if all_invoices else []
        unpaid_amount = sum(unpaid_invoices.mapped('amount_residual')) if unpaid_invoices else 0

        # حساب الفواتير المتأخرة
        from datetime import date
        today = date.today()
        overdue_invoices = []
        if unpaid_invoices:
            for inv in unpaid_invoices:
                if inv.invoice_date_due and inv.invoice_date_due < today:
                    overdue_invoices.append(inv)

        values.update({
            'date': date_begin,
            'invoices': invoices,
            'page_name': 'invoice',
            'pager': pager,
            'default_url': '/my/invoices',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
            'total_amount': total_amount,
            'paid_amount': paid_amount,
            'unpaid_amount': unpaid_amount,
            'invoice_count': len(all_invoices) if all_invoices else 0,
            'paid_count': len(all_invoices.filtered(lambda i: i.payment_state == 'paid')) if all_invoices else 0,
            'unpaid_count': len(unpaid_invoices) if unpaid_invoices else 0,
            'overdue_count': len(overdue_invoices),
            'overdue_invoice_count': len(overdue_invoices),  # مهم جداً
        })

        return request.render("shipping_management_system.portal_my_invoices", values)

    @http.route(['/my/invoice/<int:invoice_id>'], type='http', auth="user", website=True)
    def portal_my_invoice_detail(self, invoice_id=None, access_token=None, **kw):
        try:
            invoice_sudo = self._document_check_access('account.move', invoice_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = {
            'page_name': 'invoice',
            'invoice': invoice_sudo,
            'user': request.env.user
        }

        return request.render("shipping_management_system.portal_my_invoice_detail", values)

    @http.route(['/my/shipment/<int:shipment_id>'], type='http', auth="user", website=True)
    def portal_my_shipment_detail(self, shipment_id=None, access_token=None, **kw):
        try:
            shipment_sudo = self._document_check_access('shipment.order', shipment_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = self._shipment_get_page_view_values(shipment_sudo, access_token, **kw)
        return request.render("shipping_management_system.portal_my_shipment_detail", values)

    def _shipment_get_page_view_values(self, shipment, access_token, **kwargs):
        values = {
            'page_name': 'shipment',
            'shipment': shipment,
            'user': request.env.user
        }
        return self._get_page_view_values(shipment, access_token, values, 'my_shipments_history', False, **kwargs)

class ToroodWebsite(http.Controller):



    @http.route(['/shipment', '/shipment/request'], type='http', auth='public', website=True)
    def shipment_form(self, **kwargs):
        """عرض صفحة طلب الشحن"""
        # الكود الموجود مسبقاً
        categories = request.env['product.category'].sudo().search([])
        brands = request.env['product.brand'].sudo().search([('active', '=', True)])

        values = {
            'categories': categories,
            'brands': brands,
            'error': {},
            'success': kwargs.get('success', False)
        }

        values.update(kwargs)
        return request.render('shipping_management_system.shipment_request_form', values)