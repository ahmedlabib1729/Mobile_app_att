# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta
import json


class ShipmentDashboard(models.Model):
    _name = 'shipment.dashboard'
    _description = 'Shipment Dashboard'
    _auto = False

    @api.model
    def get_dashboard_data(self):
        """جمع كل بيانات Dashboard"""

        # إحصائيات الحالات
        states_data = self._get_states_statistics()

        # إحصائيات اليوم
        today_stats = self._get_today_statistics()

        # إحصائيات الأداء
        performance = self._get_performance_statistics()

        # إحصائيات المحافظات
        governorates = self._get_top_governorates()

        # إحصائيات الشركات
        companies = self._get_shipping_companies_stats()

        # إحصائيات المالية
        financial = self._get_financial_statistics()

        # الشحنات الأخيرة
        recent_shipments = self._get_recent_shipments()

        return {
            'states': states_data,
            'today': today_stats,
            'performance': performance,
            'governorates': governorates,
            'companies': companies,
            'financial': financial,
            'recent_shipments': recent_shipments,
            'chart_data': self._get_chart_data(),
        }

    def _get_states_statistics(self):
        """إحصائيات حسب الحالة"""
        ShipmentOrder = self.env['shipment.order']

        states = [
            ('draft', 'Draft', 'info', 'fa-edit'),
            ('confirmed', 'Confirmed', 'primary', 'fa-check-circle'),
            ('picked', 'Picked Up', 'warning', 'fa-box'),
            ('in_transit', 'In Transit', 'info', 'fa-truck'),
            ('out_for_delivery', 'Out for Delivery', 'warning', 'fa-shipping-fast'),
            ('delivered', 'Delivered', 'success', 'fa-check-square'),
            ('returned', 'Returned', 'danger', 'fa-undo'),
            ('cancelled', 'Cancelled', 'secondary', 'fa-times-circle'),
        ]

        result = []
        total = ShipmentOrder.search_count([])

        for state_code, state_name, color, icon in states:
            count = ShipmentOrder.search_count([('state', '=', state_code)])
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

    def _get_today_statistics(self):
        """إحصائيات اليوم"""
        ShipmentOrder = self.env['shipment.order']
        today = fields.Date.today()

        # شحنات اليوم
        today_created = ShipmentOrder.search_count([
            ('create_date', '>=', datetime.combine(today, datetime.min.time())),
            ('create_date', '<=', datetime.combine(today, datetime.max.time())),
        ])

        # الاستلام اليوم
        today_pickup = ShipmentOrder.search_count([
            ('pickup_date', '>=', datetime.combine(today, datetime.min.time())),
            ('pickup_date', '<=', datetime.combine(today, datetime.max.time())),
        ])

        # التسليم المتوقع اليوم
        today_delivery = ShipmentOrder.search_count([
            ('expected_delivery', '>=', datetime.combine(today, datetime.min.time())),
            ('expected_delivery', '<=', datetime.combine(today, datetime.max.time())),
        ])

        # التسليم الفعلي اليوم
        today_delivered = ShipmentOrder.search_count([
            ('actual_delivery', '>=', datetime.combine(today, datetime.min.time())),
            ('actual_delivery', '<=', datetime.combine(today, datetime.max.time())),
        ])

        return {
            'created': today_created,
            'pickup': today_pickup,
            'expected_delivery': today_delivery,
            'delivered': today_delivered,
        }

    def _get_performance_statistics(self):
        """إحصائيات الأداء"""
        ShipmentOrder = self.env['shipment.order']

        # نسبة التسليم في الوقت
        total_delivered = ShipmentOrder.search_count([('state', '=', 'delivered')])
        on_time = ShipmentOrder.search_count([
            ('state', '=', 'delivered'),
            ('actual_delivery', '<=', 'expected_delivery')
        ])

        on_time_rate = (on_time / total_delivered * 100) if total_delivered > 0 else 0

        # متوسط وقت التسليم
        delivered_orders = ShipmentOrder.search([
            ('state', '=', 'delivered'),
            ('actual_delivery', '!=', False),
            ('pickup_date', '!=', False)
        ], limit=100)

        avg_delivery_days = 0
        if delivered_orders:
            total_days = sum([
                (order.actual_delivery.date() - order.pickup_date.date()).days
                for order in delivered_orders
            ])
            avg_delivery_days = total_days / len(delivered_orders)

        # نسبة الإرجاع
        total_completed = ShipmentOrder.search_count([
            ('state', 'in', ['delivered', 'returned'])
        ])
        returned = ShipmentOrder.search_count([('state', '=', 'returned')])
        return_rate = (returned / total_completed * 100) if total_completed > 0 else 0

        return {
            'on_time_rate': round(on_time_rate, 1),
            'avg_delivery_days': round(avg_delivery_days, 1),
            'return_rate': round(return_rate, 1),
        }

    def _get_top_governorates(self):
        """أكثر المحافظات شحناً"""
        query = """
            SELECT 
                rcs.name as governorate,
                COUNT(*) as count
            FROM shipment_order so
            JOIN res_country_state rcs ON so.recipient_governorate_id = rcs.id
            GROUP BY rcs.name
            ORDER BY count DESC
            LIMIT 5
        """
        self.env.cr.execute(query)
        return self.env.cr.dictfetchall()

    def _get_shipping_companies_stats(self):
        """إحصائيات شركات الشحن"""
        query = """
            SELECT 
                sc.name as company,
                COUNT(so.id) as total_orders,
                COUNT(CASE WHEN so.state = 'delivered' THEN 1 END) as delivered,
                COUNT(CASE WHEN so.state = 'returned' THEN 1 END) as returned,
                ROUND(
                    COUNT(CASE WHEN so.state = 'delivered' THEN 1 END)::numeric * 100 / 
                    NULLIF(COUNT(so.id), 0), 1
                ) as success_rate
            FROM shipping_company sc
            LEFT JOIN shipment_order so ON sc.id = so.shipping_company_id
            GROUP BY sc.id, sc.name
            ORDER BY total_orders DESC
            LIMIT 5
        """
        self.env.cr.execute(query)
        return self.env.cr.dictfetchall()

    def _get_financial_statistics(self):
        """الإحصائيات المالية"""
        ShipmentOrder = self.env['shipment.order']
        today = fields.Date.today()
        month_start = today.replace(day=1)

        # إجمالي الشهر
        month_orders = ShipmentOrder.search([
            ('create_date', '>=', month_start),
            ('state', 'not in', ['cancelled'])
        ])

        total_revenue = sum(month_orders.mapped('final_customer_price'))
        total_shipping_cost = sum(month_orders.mapped('shipping_cost'))
        total_profit = total_revenue - total_shipping_cost

        # COD
        cod_orders = ShipmentOrder.search([
            ('payment_method', '=', 'cod'),
            ('state', 'not in', ['cancelled', 'returned'])
        ])
        total_cod = sum(cod_orders.mapped('cod_amount'))

        return {
            'total_revenue': total_revenue,
            'total_shipping_cost': total_shipping_cost,
            'total_profit': total_profit,
            'total_cod': total_cod,
            'avg_order_value': total_revenue / len(month_orders) if month_orders else 0,
        }

    def _get_recent_shipments(self):
        """آخر الشحنات"""
        ShipmentOrder = self.env['shipment.order']

        recent = ShipmentOrder.search([], order='create_date desc', limit=10)

        return [{
            'id': order.id,
            'order_number': order.order_number,
            'sender': order.sender_id.name,
            'recipient': order.recipient_id.name,
            'state': order.state,
            'state_name': dict(order._fields['state'].selection).get(order.state),
            'tracking': order.tracking_number or '',
            'amount': order.final_customer_price,
        } for order in recent]

    def _get_chart_data(self):
        """بيانات الرسوم البيانية"""
        # شحنات آخر 7 أيام
        today = fields.Date.today()
        week_data = []

        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            count = self.env['shipment.order'].search_count([
                ('create_date', '>=', datetime.combine(date, datetime.min.time())),
                ('create_date', '<=', datetime.combine(date, datetime.max.time())),
            ])
            week_data.append({
                'date': date.strftime('%a'),
                'count': count
            })

        # توزيع طرق الدفع
        payment_methods = []
        for method, label in [('prepaid', 'Prepaid'), ('cod', 'COD'), ('credit', 'Credit')]:
            count = self.env['shipment.order'].search_count([
                ('payment_method', '=', method)
            ])
            if count > 0:
                payment_methods.append({
                    'method': label,
                    'count': count
                })

        return {
            'weekly': week_data,
            'payment_methods': payment_methods,
        }