from odoo import models, fields, api, _
from datetime import datetime, timedelta
import json


class ShipmentDashboard(models.Model):
    _name = 'shipment.dashboard'
    _description = 'Shipment Dashboard'
    _auto = False

    @api.model
    def get_dashboard_data(self, date_from=None, date_to=None, search_term=None):
        """جمع بيانات Dashboard مع فلاتر"""

        # معالجة التواريخ
        if date_from and isinstance(date_from, str):
            try:
                date_from = fields.Datetime.from_string(date_from).date()
            except:
                date_from = fields.Date.today()
        elif not date_from:
            date_from = fields.Date.today()

        if date_to and isinstance(date_to, str):
            try:
                date_to = fields.Datetime.from_string(date_to).date()
            except:
                date_to = fields.Date.today()
        elif not date_to:
            date_to = fields.Date.today()

        # بناء domain
        base_domain = [
            ('create_date', '>=', datetime.combine(date_from, datetime.min.time())),
            ('create_date', '<=', datetime.combine(date_to, datetime.max.time()))
        ]

        # إضافة search term
        if search_term and search_term.strip():
            search_domain = [
                '|', '|', '|',
                ('order_number', 'ilike', search_term),
                ('tracking_number', 'ilike', search_term),
                ('sender_id.name', 'ilike', search_term),
                ('recipient_id.name', 'ilike', search_term)
            ]
            base_domain = ['&'] + base_domain + search_domain

        # جمع البيانات
        states_data = self._get_states_statistics_filtered(base_domain)
        period_stats = self._get_period_statistics(base_domain)
        financial = self._get_financial_statistics_filtered(base_domain)
        shipments = self._get_period_shipments(base_domain)

        return {
            'states': states_data,
            'today': period_stats,
            'financial': financial,
            'today_shipments': shipments,
            'recent_shipments': shipments,
        }

    def _get_states_statistics_filtered(self, base_domain):
        """إحصائيات الحالات"""
        ShipmentOrder = self.env['shipment.order']

        states = [
            ('draft', 'Draft', 'secondary', 'fa-edit'),
            ('confirmed', 'Confirmed', 'primary', 'fa-check-circle'),
            ('picked', 'Picked Up', 'warning', 'fa-box'),
            ('in_transit', 'In Transit', 'info', 'fa-truck'),
            ('out_for_delivery', 'Out for Delivery', 'warning', 'fa-shipping-fast'),
            ('delivered', 'Delivered', 'success', 'fa-check-square'),
            ('returned', 'Returned', 'danger', 'fa-undo'),
            ('cancelled', 'Cancelled', 'dark', 'fa-times-circle'),
        ]

        result = []
        total = ShipmentOrder.search_count(base_domain)

        for state_code, state_name, color, icon in states:
            count = ShipmentOrder.search_count(base_domain + [('state', '=', state_code)])
            percentage = (count / total * 100) if total > 0 else 0
            result.append({
                'state': state_code,
                'name': state_name,
                'count': count,
                'percentage': round(percentage, 1),
                'color': color,
                'icon': icon,
            })

        return result

    def _get_period_statistics(self, base_domain):
        """إحصائيات الفترة"""
        ShipmentOrder = self.env['shipment.order']

        period_created = ShipmentOrder.search_count(base_domain)
        period_delivered = ShipmentOrder.search_count(base_domain + [('state', '=', 'delivered')])

        return {
            'created': period_created,
            'delivered': period_delivered,
            'pickup': 0,
            'expected_delivery': 0,
        }

    def _get_period_shipments(self, base_domain):
        """شحنات الفترة"""
        ShipmentOrder = self.env['shipment.order']

        orders = ShipmentOrder.search(base_domain, order='create_date desc', limit=20)

        result = []
        for order in orders:
            result.append({
                'id': order.id,
                'order_number': order.order_number or 'N/A',
                'sender': order.sender_id.name if order.sender_id else 'N/A',
                'recipient': order.recipient_id.name if order.recipient_id else 'N/A',
                'state': order.state or 'draft',
                'state_name': dict(order._fields['state'].selection).get(order.state,
                                                                         order.state) if order.state else 'Draft',
                'tracking': order.tracking_number or '',
                'amount': order.final_customer_price or 0,
                'create_date': order.create_date.isoformat() if order.create_date else '',
            })

        return result

    def _get_financial_statistics_filtered(self, base_domain):
        """الإحصائيات المالية"""
        ShipmentOrder = self.env['shipment.order']

        orders = ShipmentOrder.search(base_domain + [('state', '!=', 'cancelled')])

        total_revenue = sum(orders.mapped('final_customer_price')) if orders else 0
        total_shipping_cost = sum(orders.mapped('shipping_cost')) if orders else 0
        total_profit = total_revenue - total_shipping_cost

        return {
            'total_revenue': total_revenue,
            'total_shipping_cost': total_shipping_cost,
            'total_profit': total_profit,
            'total_cod': 0,
            'avg_order_value': (total_revenue / len(orders)) if orders else 0,
        }