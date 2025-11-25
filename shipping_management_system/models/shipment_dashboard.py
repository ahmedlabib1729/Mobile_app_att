from odoo import models, fields, api, _
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class ShipmentDashboard(models.Model):
    _name = 'shipment.dashboard'
    _description = 'Shipment Dashboard'
    _auto = False

    @api.model
    def get_dashboard_data(self, date_from=None, date_to=None, search_term=None):
        """جمع بيانات Dashboard مع الفلاتر"""

        _logger.info(f"=== Dashboard Request ===")
        _logger.info(f"Raw Date From: {date_from}")
        _logger.info(f"Raw Date To: {date_to}")
        _logger.info(f"Search Term: {search_term}")

        # معالجة التواريخ بطريقة أبسط
        if date_from:
            if isinstance(date_from, str):
                try:
                    # Remove timezone info if present
                    date_from = date_from.replace('T', ' ').replace('Z', '').split('.')[0]
                    # Try multiple date formats
                    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y-%m-%dT%H:%M:%S']:
                        try:
                            date_from = datetime.strptime(date_from, fmt)
                            break
                        except:
                            continue

                    # Set to start of day
                    date_from = date_from.replace(hour=0, minute=0, second=0, microsecond=0)
                except Exception as e:
                    _logger.error(f"Failed to parse date_from: {e}")
                    date_from = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            elif isinstance(date_from, datetime):
                date_from = date_from.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            date_from = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if date_to:
            if isinstance(date_to, str):
                try:
                    # Remove timezone info if present
                    date_to = date_to.replace('T', ' ').replace('Z', '').split('.')[0]
                    # Try multiple date formats
                    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y-%m-%dT%H:%M:%S']:
                        try:
                            date_to = datetime.strptime(date_to, fmt)
                            break
                        except:
                            continue

                    # Set to end of day
                    date_to = date_to.replace(hour=23, minute=59, second=59, microsecond=999999)
                except Exception as e:
                    _logger.error(f"Failed to parse date_to: {e}")
                    date_to = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
            elif isinstance(date_to, datetime):
                date_to = date_to.replace(hour=23, minute=59, second=59, microsecond=999999)
        else:
            date_to = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)

        _logger.info(f"Parsed Date From: {date_from}")
        _logger.info(f"Parsed Date To: {date_to}")

        # بناء domain الأساسي
        base_domain = [
            ('create_date', '>=', date_from),
            ('create_date', '<=', date_to)
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
            full_domain = ['&'] + base_domain + search_domain
        else:
            full_domain = base_domain

        _logger.info(f"Full Domain: {full_domain}")

        # استخدام sudo للتأكد من الصلاحيات
        ShipmentOrder = self.env['shipment.order'].sudo()

        # العدد الكلي
        total_in_filter = ShipmentOrder.search_count(full_domain)
        _logger.info(f"Total Orders in Filter: {total_in_filter}")

        # حساب الإحصائيات للفلتر المحدد
        states_stats = self._get_states_statistics(full_domain)
        kpi_stats = self._get_kpi_statistics(full_domain)
        financial_stats = self._get_financial_statistics(full_domain)

        # === الإضافة الجديدة: حساب Overdue بدون فلترات ===
        overdue_count = self._get_total_overdue_count()

        # جلب آخر 20 شحنة للجدول فقط
        table_data = self._get_table_records(full_domain)

        result = {
            'states': states_stats,
            'kpi': kpi_stats,
            'today': kpi_stats,  # للتوافق مع الكود الحالي
            'financial': financial_stats,
            'today_shipments': table_data,
            'recent_shipments': table_data,
            'total_count': total_in_filter,
            'overdue_count': overdue_count,  # إضافة العداد المنفصل
            'filter_info': {
                'date_from': date_from.isoformat() if date_from else None,
                'date_to': date_to.isoformat() if date_to else None,
                'search_term': search_term or 'All',
                'total_found': total_in_filter
            }
        }

        _logger.info(f"=== Dashboard Response ===")
        _logger.info(f"Total Count: {total_in_filter}")
        _logger.info(f"Overdue Count (no filters): {overdue_count}")
        _logger.info(f"States Count: {sum([s['count'] for s in states_stats])}")

        return result

    def _get_overdue_statistics(self, domain):
        """حساب الطلبات المتأخرة عن تاريخ التسليم المتوقع"""
        ShipmentOrder = self.env['shipment.order'].sudo()
        current_time = fields.Datetime.now()

        # الطلبات المتأخرة: تجاوزت expected_delivery وليست delivered/cancelled/returned
        overdue_domain = list(domain) + [
            ('expected_delivery', '!=', False),
            ('expected_delivery', '<', current_time),
            ('state', 'not in', ['delivered', 'cancelled', 'returned'])
        ]

        overdue_count = ShipmentOrder.search_count(overdue_domain)

        _logger.info(f"Overdue Orders: {overdue_count}")

        return {
            'overdue_count': overdue_count
        }

    def _get_total_overdue_count(self):
        """حساب كل الطلبات المتأخرة بدون أي فلترات"""
        ShipmentOrder = self.env['shipment.order'].sudo()
        current_time = fields.Datetime.now()

        # Domain للطلبات المتأخرة فقط - بدون فلتر تاريخ أو بحث
        overdue_domain = [
            ('expected_delivery', '!=', False),
            ('expected_delivery', '<', current_time),
            ('state', 'not in', ['delivered', 'cancelled', 'returned'])
        ]

        overdue_count = ShipmentOrder.search_count(overdue_domain)

        _logger.info(f"Total Overdue Orders (no filters): {overdue_count}")

        return overdue_count

    def _get_states_statistics(self, domain):
        """حساب إحصائيات الحالات للفلتر المحدد"""
        ShipmentOrder = self.env['shipment.order'].sudo()

        states_config = [
            ('draft', 'Draft', 'secondary', 'fa-edit'),
            ('confirmed', 'Confirmed', 'primary', 'fa-check-circle'),
            ('picked', 'Picked Up', 'warning', 'fa-box'),
            ('torood_hub', 'Torood Hub', 'info', 'fa-warehouse'),  # جديد
            ('in_transit', 'In Transit', 'info', 'fa-truck'),
            ('shipping_company_hub', 'Shipping Hub', 'primary', 'fa-building'),  # جديد
            ('out_for_delivery', 'Out for Delivery', 'warning', 'fa-shipping-fast'),
            ('delivered', 'Delivered', 'success', 'fa-check-square'),
            ('returned', 'Returned', 'danger', 'fa-undo'),
            ('cancelled', 'Cancelled', 'dark', 'fa-times-circle'),
        ]

        # العدد الكلي للفلتر
        total = ShipmentOrder.search_count(domain)

        result = []
        for state_code, state_name, color, icon in states_config:
            # حساب كل حالة مع الفلتر
            state_domain = list(domain) + [('state', '=', state_code)]
            count = ShipmentOrder.search_count(state_domain)

            percentage = (count / total * 100) if total > 0 else 0

            _logger.info(f"State {state_code}: {count}/{total} = {percentage:.1f}%")

            result.append({
                'state': state_code,
                'name': state_name,
                'count': count,
                'percentage': round(percentage, 1),
                'color': color,
                'icon': icon,
            })

        return result

    def _get_kpi_statistics(self, domain):
        """حساب KPIs للفلتر المحدد - محدث"""
        ShipmentOrder = self.env['shipment.order'].sudo()

        # إجمالي الطلبات
        total_orders = ShipmentOrder.search_count(domain)

        # المسلمة
        delivered_domain = list(domain) + [('state', '=', 'delivered')]
        delivered = ShipmentOrder.search_count(delivered_domain)

        # في الطريق (كل المراحل بين picked و delivered)
        in_transit_domain = list(domain) + [
            ('state', 'in', ['torood_hub', 'in_transit', 'shipping_company_hub', 'out_for_delivery'])
        ]
        in_transit = ShipmentOrder.search_count(in_transit_domain)

        # المؤكدة
        confirmed_domain = list(domain) + [('state', '=', 'confirmed')]
        confirmed = ShipmentOrder.search_count(confirmed_domain)

        # المستلمة
        picked_domain = list(domain) + [('state', '=', 'picked')]
        picked = ShipmentOrder.search_count(picked_domain)

        # في Torood Hub
        torood_hub_domain = list(domain) + [('state', '=', 'torood_hub')]
        torood_hub = ShipmentOrder.search_count(torood_hub_domain)

        # في Shipping Company Hub
        shipping_hub_domain = list(domain) + [('state', '=', 'shipping_company_hub')]
        shipping_hub = ShipmentOrder.search_count(shipping_hub_domain)

        # الملغاة
        cancelled_domain = list(domain) + [('state', '=', 'cancelled')]
        cancelled = ShipmentOrder.search_count(cancelled_domain)

        # المرتجعة
        returned_domain = list(domain) + [('state', '=', 'returned')]
        returned = ShipmentOrder.search_count(returned_domain)

        current_time = fields.Datetime.now()
        overdue_domain = list(domain) + [
            ('expected_delivery', '!=', False),
            ('expected_delivery', '<', current_time),
            ('state', 'not in', ['delivered', 'cancelled', 'returned'])
        ]
        overdue = ShipmentOrder.search_count(overdue_domain)

        _logger.info(f"KPI Stats - Total: {total_orders}, Delivered: {delivered}, In Transit: {in_transit}")

        return {
            'created': total_orders,
            'delivered': delivered,
            'in_transit': in_transit,
            'confirmed': confirmed,
            'picked': picked,
            'torood_hub': torood_hub,  # جديد
            'shipping_hub': shipping_hub,  # جديد
            'cancelled': cancelled,
            'returned': returned,
            'overdue': overdue,
            'pickup': 0,
            'expected_delivery': 0,
        }

    def _get_financial_statistics(self, domain):
        """حساب الإحصائيات المالية للفلتر المحدد"""
        ShipmentOrder = self.env['shipment.order'].sudo()

        # استبعاد الملغاة من الحسابات المالية
        financial_domain = list(domain) + [('state', '!=', 'cancelled')]

        orders = ShipmentOrder.search(financial_domain)

        total_revenue = 0.0
        total_shipping_cost = 0.0
        total_cod = 0.0

        for order in orders:
            total_revenue += float(order.final_customer_price or 0)
            total_shipping_cost += float(order.shipping_cost or 0)
            if order.payment_method == 'cod':
                total_cod += float(order.cod_amount or 0)

        total_profit = total_revenue - total_shipping_cost
        avg_value = total_revenue / len(orders) if orders else 0

        _logger.info(f"Financial - Orders: {len(orders)}, Revenue: {total_revenue:.2f}")

        return {
            'total_revenue': round(total_revenue, 2),
            'total_shipping_cost': round(total_shipping_cost, 2),
            'total_profit': round(total_profit, 2),
            'total_cod': round(total_cod, 2),
            'avg_order_value': round(avg_value, 2),
            'order_count': len(orders),
        }

    def _get_table_records(self, domain):
        """جلب آخر 20 سجل للجدول فقط"""
        ShipmentOrder = self.env['shipment.order'].sudo()

        # آخر 20 شحنة من الفلتر
        orders = ShipmentOrder.search(domain, order='create_date desc', limit=20)

        result = []
        for order in orders:
            state_dict = dict(order._fields['state'].selection)
            state_name = state_dict.get(order.state, order.state or 'Draft')

            result.append({
                'id': order.id,
                'order_number': order.order_number or 'N/A',
                'sender': order.sender_id.name if order.sender_id else 'N/A',
                'recipient': order.recipient_id.name if order.recipient_id else 'N/A',
                'recipient_city': order.recipient_city or 'N/A',
                'shipping_company': order.shipping_company_id.name if order.shipping_company_id else 'N/A',
                'state': order.state or 'draft',
                'state_name': state_name,
                'tracking': order.tracking_number or '',
                'amount': float(order.final_customer_price or 0),
                'create_date': order.create_date.isoformat() if order.create_date else '',
                'weight': float(order.total_weight or 0),
            })

        _logger.info(f"Table: Showing {len(orders)} of {ShipmentOrder.search_count(domain)} total orders")

        return result