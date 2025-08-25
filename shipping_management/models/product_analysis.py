# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class ProductAnalysis(models.Model):
    _name = 'product.analysis'
    _description = 'Product Shipping Analysis'
    _order = 'shipping_date desc'

    # ===== Product Information =====
    product_name = fields.Char(
        string='Product Name',
        required=True,
        index=True
    )

    category_id = fields.Many2one(
        'product.category',
        string='Main Category',
        required=True,
        index=True
    )

    subcategory_id = fields.Many2one(
        'product.category',
        string='Subcategory'
    )

    brand = fields.Char(
        string='Brand',
        index=True
    )

    # ===== Order Information =====
    order_id = fields.Many2one(
        'shipping.order',
        string='Shipping Order',
        required=True,
        ondelete='cascade'
    )

    customer_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        index=True
    )

    customer_type = fields.Selection(
        related='customer_id.customer_type',
        string='Customer Type',
        store=True
    )

    # ===== Shipping Information =====
    shipping_date = fields.Datetime(
        string='Shipping Date',
        required=True,
        index=True
    )

    shipping_month = fields.Char(
        string='Month',
        compute='_compute_date_fields',
        store=True
    )

    shipping_week = fields.Integer(
        string='Week',
        compute='_compute_date_fields',
        store=True
    )

    shipping_day = fields.Char(
        string='Day of Week',
        compute='_compute_date_fields',
        store=True
    )

    # ===== Geographic Information =====
    governorate_id = fields.Many2one(
        'res.country.state',
        string='Governorate',
        domain="[('country_id.code', '=', 'EG')]"
    )

    city = fields.Char(
        string='City'
    )

    # ===== Quantity & Value =====
    quantity = fields.Integer(
        string='Quantity',
        required=True
    )

    unit_price = fields.Float(
        string='Unit Price'
    )

    total_value = fields.Float(
        string='Total Value',
        compute='_compute_total_value',
        store=True
    )

    # ===== Analysis Fields =====
    is_repeat_product = fields.Boolean(
        string='Repeat Product',
        compute='_compute_repeat_product',
        store=True
    )

    days_since_last_order = fields.Integer(
        string='Days Since Last Order',
        compute='_compute_repeat_product',
        store=True
    )

    @api.depends('shipping_date')
    def _compute_date_fields(self):
        for record in self:
            if record.shipping_date:
                dt = record.shipping_date
                record.shipping_month = dt.strftime('%Y-%m')
                record.shipping_week = dt.isocalendar()[1]
                record.shipping_day = dt.strftime('%A')
            else:
                record.shipping_month = False
                record.shipping_week = 0
                record.shipping_day = False

    @api.depends('quantity', 'unit_price')
    def _compute_total_value(self):
        for record in self:
            record.total_value = record.quantity * record.unit_price

    @api.depends('product_name', 'customer_id', 'shipping_date')
    def _compute_repeat_product(self):
        for record in self:
            # Check if customer ordered this product before
            previous = self.search([
                ('customer_id', '=', record.customer_id.id),
                ('product_name', '=', record.product_name),
                ('shipping_date', '<', record.shipping_date),
                ('id', '!=', record.id)
            ], order='shipping_date desc', limit=1)

            record.is_repeat_product = bool(previous)

            if previous:
                delta = record.shipping_date - previous.shipping_date
                record.days_since_last_order = delta.days
            else:
                record.days_since_last_order = 0

    # ===== Analysis Methods =====
    @api.model
    def get_top_products(self, period='month', limit=10):
        """Get top products for a specific period"""
        domain = []

        if period == 'today':
            start = fields.Date.today()
            end = start + timedelta(days=1)
        elif period == 'week':
            today = fields.Date.today()
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=7)
        elif period == 'month':
            today = fields.Date.today()
            start = today.replace(day=1)
            next_month = start + timedelta(days=32)
            end = next_month.replace(day=1)
        else:
            start = fields.Date.today() - timedelta(days=365)
            end = fields.Date.today() + timedelta(days=1)

        domain = [
            ('shipping_date', '>=', start),
            ('shipping_date', '<', end)
        ]

        # SQL query for aggregation
        self.env.cr.execute("""
            SELECT 
                product_name,
                brand,
                SUM(quantity) as total_quantity,
                SUM(total_value) as total_value,
                COUNT(DISTINCT customer_id) as unique_customers,
                COUNT(*) as order_count
            FROM product_analysis
            WHERE shipping_date >= %s AND shipping_date < %s
            GROUP BY product_name, brand
            ORDER BY total_quantity DESC
            LIMIT %s
        """, (start, end, limit))

        results = []
        for row in self.env.cr.fetchall():
            results.append({
                'product_name': row[0],
                'brand': row[1],
                'total_quantity': row[2],
                'total_value': row[3],
                'unique_customers': row[4],
                'order_count': row[5]
            })

        return results

    @api.model
    def get_category_analysis(self, period='month'):
        """Analyze products by category"""
        if period == 'month':
            today = fields.Date.today()
            start = today.replace(day=1)
            next_month = start + timedelta(days=32)
            end = next_month.replace(day=1)
        else:
            start = fields.Date.today() - timedelta(days=365)
            end = fields.Date.today() + timedelta(days=1)

        self.env.cr.execute("""
            SELECT 
                pc.name as category_name,
                COUNT(DISTINCT pa.product_name) as product_count,
                SUM(pa.quantity) as total_quantity,
                SUM(pa.total_value) as total_value,
                AVG(pa.unit_price) as avg_price
            FROM product_analysis pa
            JOIN product_category pc ON pa.category_id = pc.id
            WHERE pa.shipping_date >= %s AND pa.shipping_date < %s
            GROUP BY pc.id, pc.name
            ORDER BY total_value DESC
        """, (start, end))

        results = []
        for row in self.env.cr.fetchall():
            results.append({
                'category': row[0],
                'product_count': row[1],
                'total_quantity': row[2],
                'total_value': row[3],
                'avg_price': row[4]
            })

        return results

    @api.model
    def get_product_combinations(self, product_name=None, min_support=2):
        """Find products that are frequently ordered together"""
        # Market Basket Analysis
        query = """
            WITH order_products AS (
                SELECT 
                    order_id,
                    array_agg(DISTINCT product_name) as products
                FROM product_analysis
                GROUP BY order_id
                HAVING COUNT(DISTINCT product_name) > 1
            )
            SELECT 
                p1.product_name as product_1,
                p2.product_name as product_2,
                COUNT(*) as frequency
            FROM product_analysis p1
            JOIN product_analysis p2 ON p1.order_id = p2.order_id
            WHERE p1.product_name < p2.product_name
        """

        params = []
        if product_name:
            query += " AND (p1.product_name = %s OR p2.product_name = %s)"
            params.extend([product_name, product_name])

        query += """
            GROUP BY p1.product_name, p2.product_name
            HAVING COUNT(*) >= %s
            ORDER BY frequency DESC
            LIMIT 20
        """
        params.append(min_support)

        self.env.cr.execute(query, params)

        results = []
        for row in self.env.cr.fetchall():
            results.append({
                'product_1': row[0],
                'product_2': row[1],
                'frequency': row[2]
            })

        return results

    @api.model
    def get_seasonal_patterns(self):
        """Identify seasonal patterns in product shipping"""
        self.env.cr.execute("""
            SELECT 
                product_name,
                EXTRACT(MONTH FROM shipping_date) as month,
                SUM(quantity) as total_quantity
            FROM product_analysis
            WHERE shipping_date >= date_trunc('year', CURRENT_DATE - interval '1 year')
            GROUP BY product_name, EXTRACT(MONTH FROM shipping_date)
            ORDER BY product_name, month
        """)

        products = {}
        for row in self.env.cr.fetchall():
            product = row[0]
            month = int(row[1])
            quantity = row[2]

            if product not in products:
                products[product] = [0] * 12
            products[product][month - 1] = quantity

        # Identify seasonal products
        seasonal_products = []
        for product, monthly_data in products.items():
            avg = sum(monthly_data) / 12
            max_month = max(monthly_data)

            # Product is seasonal if max month is 2x average
            if max_month > avg * 2:
                peak_month = monthly_data.index(max_month) + 1
                seasonal_products.append({
                    'product': product,
                    'peak_month': peak_month,
                    'peak_quantity': max_month,
                    'average': avg
                })

        return seasonal_products

    @api.model
    def get_geographic_distribution(self, product_name=None):
        """Get geographic distribution of products"""
        query = """
            SELECT 
                gov.name as governorate,
                COUNT(*) as order_count,
                SUM(pa.quantity) as total_quantity,
                SUM(pa.total_value) as total_value
            FROM product_analysis pa
            JOIN res_country_state gov ON pa.governorate_id = gov.id
            WHERE 1=1
        """

        params = []
        if product_name:
            query += " AND pa.product_name = %s"
            params.append(product_name)

        query += """
            GROUP BY gov.id, gov.name
            ORDER BY total_quantity DESC
        """

        self.env.cr.execute(query, params)

        results = []
        for row in self.env.cr.fetchall():
            results.append({
                'governorate': row[0],
                'order_count': row[1],
                'total_quantity': row[2],
                'total_value': row[3]
            })

        return results

    @api.model
    def predict_demand(self, product_name, days=30):
        """Simple demand prediction based on historical data"""
        # Get last 90 days of data
        end_date = fields.Date.today()
        start_date = end_date - timedelta(days=90)

        records = self.search([
            ('product_name', '=', product_name),
            ('shipping_date', '>=', start_date),
            ('shipping_date', '<=', end_date)
        ])

        if not records:
            return {'predicted_quantity': 0, 'confidence': 'low'}

        # Calculate daily average
        total_quantity = sum(records.mapped('quantity'))
        days_with_data = 90
        daily_avg = total_quantity / days_with_data

        # Simple linear prediction
        predicted_quantity = int(daily_avg * days)

        # Determine confidence based on data consistency
        if len(records) > 10:
            confidence = 'high'
        elif len(records) > 5:
            confidence = 'medium'
        else:
            confidence = 'low'

        return {
            'predicted_quantity': predicted_quantity,
            'daily_average': daily_avg,
            'confidence': confidence
        }