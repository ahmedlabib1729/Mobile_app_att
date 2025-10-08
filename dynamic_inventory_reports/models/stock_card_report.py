# models/stock_card_report.py
from odoo import models, fields, api
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class StockCardWizard(models.TransientModel):
    _name = 'stock.card.wizard'
    _description = 'Stock Card Report Wizard'
    _rec_name = 'report_type'

    report_type = fields.Selection([
        ('stock_card', 'Stock Card'),
    ], string='Report Type', default='stock_card', required=True)

    # Quick date filter
    date_filter = fields.Selection([
        ('today', 'Today'),
        ('this_week', 'This Week'),
        ('this_month', 'This Month'),
        ('this_quarter', 'This Quarter'),
        ('this_year', 'This Year'),
        ('last_month', 'Last Month'),
        ('last_quarter', 'Last Quarter'),
        ('last_year', 'Last Year'),
        ('all', 'All Time'),
        ('custom', 'Custom Range'),
    ], string='Period', default='this_year')

    date_from = fields.Date('From Date', compute='_compute_dates', store=True, readonly=False)
    date_to = fields.Date('To Date', compute='_compute_dates', store=True, readonly=False)

    # Product Selection
    product_ids = fields.Many2many(
        'product.product',
        'stock_card_product_rel',
        string='Products',
    )

    # Category Selection
    category_ids = fields.Many2many(
        'product.category',
        'stock_card_category_rel',
        string='Product Categories'
    )

    # Location Selection
    location_ids = fields.Many2many(
        'stock.location',
        'stock_card_location_rel',
        string='Locations',
        domain=[('usage', '=', 'internal')]
    )

    # Search field
    search_text = fields.Char('Search', help='Search in product name or code')

    # حقل لتخزين نتائج البحث - يتم حسابه تلقائياً
    report_html = fields.Html('Report Results', compute='_compute_report_html', store=False, sanitize=False)

    # حقل لتتبع آخر تحديث (اختياري)
    last_update = fields.Datetime('Last Update', readonly=True)

    @api.depends('date_filter' , 'date_filter', 'date_from', 'date_to', 'product_ids',
             'category_ids', 'location_ids')
    def _compute_dates(self):
        """Compute date_from and date_to based on date_filter"""
        from dateutil.relativedelta import relativedelta

        for wizard in self:
            today = fields.Date.today()

            if wizard.date_filter == 'today':
                wizard.date_from = today
                wizard.date_to = today
            elif wizard.date_filter == 'this_week':
                wizard.date_from = today - relativedelta(days=today.weekday())
                wizard.date_to = today
            elif wizard.date_filter == 'this_month':
                wizard.date_from = today.replace(day=1)
                wizard.date_to = today
            elif wizard.date_filter == 'this_quarter':
                quarter_start_month = ((today.month - 1) // 3) * 3 + 1
                wizard.date_from = today.replace(month=quarter_start_month, day=1)
                wizard.date_to = today
            elif wizard.date_filter == 'this_year':
                wizard.date_from = today.replace(month=1, day=1)
                wizard.date_to = today
            elif wizard.date_filter == 'last_month':
                first_day_this_month = today.replace(day=1)
                wizard.date_to = first_day_this_month - relativedelta(days=1)
                wizard.date_from = wizard.date_to.replace(day=1)
            elif wizard.date_filter == 'last_quarter':
                quarter_start_month = ((today.month - 1) // 3) * 3 + 1
                this_quarter_start = today.replace(month=quarter_start_month, day=1)
                wizard.date_to = this_quarter_start - relativedelta(days=1)
                wizard.date_from = wizard.date_to.replace(month=((wizard.date_to.month - 1) // 3) * 3 + 1, day=1)
            elif wizard.date_filter == 'last_year':
                wizard.date_from = today.replace(year=today.year - 1, month=1, day=1)
                wizard.date_to = today.replace(year=today.year - 1, month=12, day=31)
            elif wizard.date_filter == 'all':
                wizard.date_from = False
                wizard.date_to = False

    @api.depends('report_type', 'date_filter', 'date_from', 'date_to', 'product_ids',
                 'category_ids', 'location_ids', 'search_text')
    def _compute_report_html(self):
        """يحسب تلقائياً عند تغيير أي فلتر"""
        for wizard in self:
            try:
                _logger.info("🔄 Auto-computing report HTML...")
                data = wizard.get_report_data()
                wizard.report_html = wizard._generate_html_report(data)
                wizard.last_update = fields.Datetime.now()
                _logger.info("✅ Report auto-computed successfully")
            except Exception as e:
                _logger.error(f"❌ Error auto-computing report: {str(e)}")
                wizard.report_html = f'''
                    <div style="color: red; padding: 20px; background: #fee; border-radius: 8px;">
                        <h3>Error generating report</h3>
                        <p>{str(e)}</p>
                    </div>
                '''

    # إضافة onchange للتحديث الفوري عند تغيير المنتجات
    @api.onchange('product_ids', 'category_ids', 'location_ids', 'search_text')
    def _onchange_filters(self):
        """تحديث فوري عند تغيير الفلاتر"""
        try:
            data = self.get_report_data()
            self.report_html = self._generate_html_report(data)
            self.last_update = fields.Datetime.now()
        except Exception as e:
            _logger.error(f"Error in onchange: {str(e)}")
            self.report_html = f'<div style="color: red;">Error: {str(e)}</div>'

    @api.onchange('product_ids')
    def _onchange_product_ids(self):
        """تحديث مخصص للمنتجات"""
        if self.product_ids:
            _logger.info(f"Products changed: {len(self.product_ids)} selected")
        pass  # سيتم التحديث تلقائياً من خلال computed field

    def _generate_html_report(self, data):
        """Generate HTML table from report data - ENHANCED VERSION"""
        if not data:
            return '<div style="text-align: center; padding: 20px; color: #666;">No data returned from get_report_data()</div>'

        if not data.get('products'):
            summary = data.get('summary', {})
            return f'''
            <div style="text-align: center; padding: 40px; color: #666;">
                <i class="fa fa-inbox fa-3x" style="color: #ddd; margin-bottom: 20px;"></i>
                <h3>No Stock Movements Found</h3>
                <p>No movements found for the selected products in the specified period.</p>
                <div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px; max-width: 500px; margin: 20px auto;">
                    <p style="margin: 5px 0;"><strong>Selected Products:</strong> {len(self.product_ids) if self.product_ids else 'All (limit 50)'}</p>
                    <p style="margin: 5px 0;"><strong>Selected Categories:</strong> {len(self.category_ids) if self.category_ids else 'None'}</p>
                    <p style="margin: 5px 0;"><strong>Period:</strong> {self.date_from} to {self.date_to}</p>
                </div>
                <p style="margin-top: 20px; color: #888;">Try adjusting your filters or date range.</p>
            </div>
            '''

        # Summary Cards HTML
        summary = data.get('summary', {})
        html = f'''
        <div style="margin-bottom: 20px;">
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <div style="font-size: 28px; font-weight: bold;">{summary.get('total_products', 0)}</div>
                    <div style="font-size: 14px; opacity: 0.9;">Total Products</div>
                </div>
                <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <div style="font-size: 28px; font-weight: bold;">{summary.get('total_movements', 0)}</div>
                    <div style="font-size: 14px; opacity: 0.9;">Total Movements</div>
                </div>
                <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <div style="font-size: 28px; font-weight: bold;">{summary.get('total_receipts', 0):,.2f}</div>
                    <div style="font-size: 14px; opacity: 0.9;">Total Receipts</div>
                </div>
                <div style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); color: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <div style="font-size: 28px; font-weight: bold;">{summary.get('total_issues', 0):,.2f}</div>
                    <div style="font-size: 14px; opacity: 0.9;">Total Issues</div>
                </div>
            </div>
        </div>
        '''

        # عرض كل منتج في جدول منفصل
        products_data = data.get('products', [])

        for product_info in products_data:
            product_name = product_info['product_name']
            product_code = product_info['product_code']
            opening_balance = product_info['opening_balance']
            closing_balance = product_info['closing_balance']
            movements = product_info['movements']

            # Product Header
            html += f'''
            <div style="margin-top: 30px; padding: 15px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        color: white; border-radius: 10px 10px 0 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h3 style="margin: 0; font-size: 18px; font-weight: 600;">📦 {product_name}</h3>
                        <p style="margin: 5px 0 0 0; opacity: 0.9;">Code: {product_code or 'N/A'}</p>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 14px; opacity: 0.9;">Opening: <strong>{opening_balance:,.2f}</strong></div>
                        <div style="font-size: 14px; opacity: 0.9;">Closing: <strong>{closing_balance:,.2f}</strong></div>
                    </div>
                </div>
            </div>
            '''

            # Movements Table - ENHANCED
            if movements:
                html += '''
                <div style="overflow-x: auto; border-radius: 0 0 8px 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <table class="table table-striped table-bordered" style="width: 100%; font-size: 13px; margin: 0;">
                        <thead>
                            <tr style="background: #2c3e50;">
                                <th style="color: white; padding: 12px 8px; white-space: nowrap; font-weight: 600;">Date</th>
                                <th style="color: white; padding: 12px 8px; white-space: nowrap; font-weight: 600;">Document</th>
                                <th style="color: white; padding: 12px 8px; white-space: nowrap; font-weight: 600;">SO/PO Ref</th>
                                <th style="color: white; padding: 12px 8px; white-space: nowrap; font-weight: 600;">Type</th>
                                <th style="color: white; padding: 12px 8px; white-space: nowrap; font-weight: 600;">Partner</th>
                                <th style="color: white; padding: 12px 8px; white-space: nowrap; font-weight: 600;">Salesman</th>
                                <th style="color: white; padding: 12px 8px; white-space: nowrap; font-weight: 600;">Location From</th>
                                <th style="color: white; padding: 12px 8px; white-space: nowrap; font-weight: 600;">Location To</th>
                                <th style="color: white; padding: 12px 8px; white-space: nowrap; font-weight: 600; text-align: right;">Receipt Qty</th>
                                <th style="color: white; padding: 12px 8px; white-space: nowrap; font-weight: 600; text-align: right;">Issue Qty</th>
                                <th style="color: white; padding: 12px 8px; white-space: nowrap; font-weight: 600; text-align: right;">Balance</th>
                            </tr>
                        </thead>
                        <tbody>
                '''

                for i, move in enumerate(movements):
                    bg_color = '#ffffff' if i % 2 == 0 else '#f8f9fa'
                    receipt_color = '#27ae60' if move['receipt_qty'] > 0 else '#7f8c8d'
                    issue_color = '#e74c3c' if move['issue_qty'] > 0 else '#7f8c8d'

                    receipt_display = f"{move['receipt_qty']:,.2f}" if move['receipt_qty'] > 0 else ''
                    issue_display = f"{move['issue_qty']:,.2f}" if move['issue_qty'] > 0 else ''

                    # تلوين المرجع حسب النوع
                    ref_color = '#3498db'  # أزرق للـ SO
                    reference = move.get('reference', '')
                    if reference.startswith('PO'):
                        ref_color = '#9b59b6'  # بنفسجي للـ PO
                    elif reference.startswith('RET'):
                        ref_color = '#e67e22'  # برتقالي للمرتجعات

                    html += f'''
                    <tr style="background: {bg_color};">
                        <td style="padding: 10px 8px;">{move['date']}</td>
                        <td style="padding: 10px 8px;">{move['document']}</td>
                        <td style="padding: 10px 8px; color: {ref_color}; font-weight: bold;">
                            {reference or '-'}
                        </td>
                        <td style="padding: 10px 8px;">{move['type']}</td>
                        <td style="padding: 10px 8px;">{move['partner']}</td>
                        <td style="padding: 10px 8px; color: #8e44ad;">
                            {move.get('salesman', '') or '-'}
                        </td>
                        <td style="padding: 10px 8px;">{move['location_from']}</td>
                        <td style="padding: 10px 8px;">{move['location_to']}</td>
                        <td style="padding: 10px 8px; text-align: right; color: {receipt_color}; font-weight: bold;">
                            {receipt_display}
                        </td>
                        <td style="padding: 10px 8px; text-align: right; color: {issue_color}; font-weight: bold;">
                            {issue_display}
                        </td>
                        <td style="padding: 10px 8px; text-align: right; font-weight: bold;">{move['balance']:,.2f}</td>
                    </tr>
                    '''

                # Footer with totals
                total_receipts = sum(m['receipt_qty'] for m in movements)
                total_issues = sum(m['issue_qty'] for m in movements)

                html += f'''
                        </tbody>
                        <tfoot>
                            <tr style="font-weight: bold; background: #ecf0f1;">
                                <td colspan="8" style="text-align: right; padding: 12px; font-size: 14px;">TOTALS:</td>
                                <td style="text-align: right; padding: 12px; font-size: 14px; color: #27ae60;">{total_receipts:,.2f}</td>
                                <td style="text-align: right; padding: 12px; font-size: 14px; color: #e74c3c;">{total_issues:,.2f}</td>
                                <td style="text-align: right; padding: 12px; font-size: 14px;">{closing_balance:,.2f}</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
                '''
            else:
                html += f'''
                <div style="padding: 30px; background: white; border-radius: 0 0 8px 8px; text-align: center; border: 1px solid #e8ecf1;">
                    <i class="fa fa-info-circle fa-2x" style="color: #3498db; margin-bottom: 15px;"></i>
                    <p style="margin: 0; font-size: 15px; color: #7f8c8d;">No movements found for this product in the selected period</p>
                    <p style="margin: 10px 0; font-size: 13px; color: #95a5a6;">
                        Opening Balance: <strong>{opening_balance:,.2f}</strong> | 
                        Closing Balance: <strong>{closing_balance:,.2f}</strong>
                    </p>
                </div>
                '''

        # Report Footer
        html += f'''
        <div style="margin-top: 20px; padding: 15px; background: #ecf0f1; border-radius: 8px;">
            <p style="margin: 0; color: #7f8c8d; font-size: 12px;">
                Report generated on {fields.Date.today()} | Period: {self.date_from or 'All'} to {self.date_to or 'All'}
                | Last Update: {self.last_update.strftime('%H:%M:%S') if self.last_update else 'N/A'}
            </p>
        </div>
        '''

        return html

    def get_report_data(self):
        """Generate stock card data based on filters"""
        self.ensure_one()

        _logger.info("=" * 80)
        _logger.info("Starting Stock Card Report Generation")
        _logger.info(f"Date Filter: {self.date_filter}")
        _logger.info(f"Date Range: {self.date_from} to {self.date_to}")
        _logger.info(f"Selected Products: {len(self.product_ids)} products")
        _logger.info(f"Selected Categories: {len(self.category_ids)} categories")
        _logger.info(f"Selected Locations: {len(self.location_ids)} locations")

        # Determine which products to include
        products = self._get_filtered_products()
        _logger.info(f"Filtered Products Count: {len(products)}")

        if products:
            _logger.info(f"First 5 products: {', '.join([p.name for p in products[:5]])}")

        if not products:
            _logger.warning("No products found matching filters!")
            return {'summary': {}, 'products': []}

        # Determine locations
        locations = self.location_ids if self.location_ids else self.env['stock.location'].search([
            ('usage', '=', 'internal')
        ])
        _logger.info(f"Locations Count: {len(locations)}")

        # Initialize summary
        total_movements = 0
        total_receipts = 0
        total_issues = 0
        products_data = []

        # Process each product
        for product in products:
            _logger.info(f"Processing product: {product.name} (ID: {product.id})")
            product_data = self._get_product_stock_card(product, locations)

            _logger.info(f"  - Opening Balance: {product_data['opening_balance']}")
            _logger.info(f"  - Movements Count: {len(product_data['movements'])}")
            _logger.info(f"  - Closing Balance: {product_data['closing_balance']}")

            products_data.append(product_data)
            total_movements += len(product_data['movements'])
            total_receipts += sum(m['receipt_qty'] for m in product_data['movements'])
            total_issues += sum(m['issue_qty'] for m in product_data['movements'])

        summary = {
            'total_products': len(products_data),
            'total_movements': total_movements,
            'total_receipts': total_receipts,
            'total_issues': total_issues,
        }

        _logger.info("=" * 80)
        _logger.info(f"Report Summary: {summary}")
        _logger.info("=" * 80)

        return {
            'summary': summary,
            'products': products_data,
        }

    def _get_filtered_products(self):
        """Get products based on filters - IMPROVED VERSION"""
        _logger.info("--- _get_filtered_products called ---")

        # If specific products selected
        if self.product_ids:
            _logger.info(f"Using specific products: {len(self.product_ids)} selected")
            # أعد تحميل المنتجات لضمان البيانات الكاملة
            product_ids = self.product_ids.ids
            products = self.env['product.product'].browse(product_ids)
            # أو استخدم search للتأكد من السياق
            products = self.env['product.product'].search([('id', 'in', product_ids)])
            return products

        # Build domain
        domain = [('active', '=', True)]

        # If categories selected, get products from those categories
        if self.category_ids:
            _logger.info(f"Filtering by categories: {', '.join([c.name for c in self.category_ids])}")
            domain.append(('categ_id', 'child_of', self.category_ids.ids))

        # Apply search text - IMPROVED LOGIC
        if self.search_text:
            _logger.info(f"Applying search text: {self.search_text}")
            search_text_lower = self.search_text.lower()

            # البحث المباشر باستخدام OR domain
            search_domain = ['|', '|', '|',
                             ('name', 'ilike', self.search_text),
                             ('default_code', 'ilike', self.search_text),
                             ('barcode', '=', self.search_text),
                             ('default_code', '=', self.search_text)  # البحث الدقيق بالكود
                             ]

            # دمج domain البحث مع domain الأساسي
            final_domain = domain + search_domain

            # البحث مع limit معقول
            products = self.env['product.product'].search(final_domain, limit=100)

            _logger.info(f"Search found {len(products)} products")

            # إذا لم نجد نتائج بالبحث الدقيق، جرب البحث العام
            if not products:
                _logger.info("No exact matches found, trying fuzzy search...")
                # البحث بطريقة أكثر مرونة
                search_terms = search_text_lower.split()
                products = self.env['product.product'].search(domain, limit=200)

                def matches_search(product):
                    searchable_text = ' '.join([
                        (product.name or ''),
                        (product.default_code or ''),
                        (product.barcode or ''),
                    ]).lower()
                    return all(term in searchable_text for term in search_terms)

                products = products.filtered(matches_search)[:50]  # حد أقصى 50 منتج
                _logger.info(f"Fuzzy search found {len(products)} products")

            return products

        # If no specific filter, return first 50 products
        if not self.product_ids and not self.category_ids and not self.search_text:
            _logger.info("No filters applied, returning first 50 products")
            products = self.env['product.product'].search(domain, limit=50)
            _logger.info(f"Found {len(products)} products")
            return products

        # البحث بـ domain فقط (للفئات)
        products = self.env['product.product'].search(domain, limit=100)
        _logger.info(f"Found {len(products)} products with domain: {domain}")
        return products

    @api.onchange('search_text')
    def _onchange_search_text(self):
        """تحديث فوري عند تغيير نص البحث"""
        # هذا سيؤدي لإعادة حساب report_html تلقائياً
        pass

    @api.onchange('product_ids')
    def _onchange_product_ids_force_refresh(self):
        """Force immediate refresh when products change"""
        if self.product_ids:
            # فورس الحساب مباشرة
            self._compute_report_html()
            # أو يمكنك استدعاء get_report_data مباشرة
            data = self.get_report_data()
            self.report_html = self._generate_html_report(data)

    def _get_product_stock_card(self, product, locations):
        """Get stock card for a specific product - ENHANCED VERSION"""

        _logger.info(f"    Getting stock card for: {product.name} (ID: {product.id})")

        # Calculate opening balance (before date_from)
        opening_balance = 0
        if self.date_from:
            opening_balance = self._calculate_opening_balance(product, locations, self.date_from)
            _logger.info(f"    Opening balance: {opening_balance}")

        # Get all stock moves for this product in the date range
        domain = [
            ('product_id', '=', product.id),
            ('state', '=', 'done'),
        ]

        if self.date_from:
            domain.append(('date', '>=', fields.Datetime.to_datetime(self.date_from)))
        if self.date_to:
            end_datetime = fields.Datetime.to_datetime(self.date_to).replace(hour=23, minute=59, second=59)
            domain.append(('date', '<=', end_datetime))

        # Filter by locations (either source or destination)
        if locations:
            location_ids = locations.ids
            domain.append('|')
            domain.append(('location_id', 'in', location_ids))
            domain.append(('location_dest_id', 'in', location_ids))

        _logger.info(f"    Searching moves with domain: {domain}")
        moves = self.env['stock.move'].search(domain, order='date asc, id asc')
        _logger.info(f"    Found {len(moves)} moves")

        # Process movements
        movements = []
        running_balance = opening_balance

        for move in moves:
            receipt_qty = 0
            issue_qty = 0

            # Check if location is internal
            from_internal = move.location_id.usage == 'internal'
            to_internal = move.location_dest_id.usage == 'internal'

            # تحديد نوع الحركة
            if locations:
                from_in_filter = move.location_id.id in locations.ids
                to_in_filter = move.location_dest_id.id in locations.ids

                if to_in_filter and not from_in_filter:
                    receipt_qty = move.product_uom_qty
                elif from_in_filter and not to_in_filter:
                    issue_qty = move.product_uom_qty
                elif from_in_filter and to_in_filter:
                    continue
                else:
                    continue
            else:
                if to_internal and not from_internal:
                    receipt_qty = move.product_uom_qty
                elif from_internal and not to_internal:
                    issue_qty = move.product_uom_qty
                elif from_internal and to_internal:
                    receipt_qty = move.product_uom_qty
                    issue_qty = move.product_uom_qty

            running_balance += receipt_qty - issue_qty

            # === الإضافات الجديدة ===

            # 1. الحصول على رقم Sales Order أو Purchase Order
            sale_order_name = ''
            purchase_order_name = ''
            salesman_name = ''

            if move.picking_id:
                # Check if it's from a sale order
                if move.picking_id.sale_id:
                    sale_order_name = move.picking_id.sale_id.name
                    # الحصول على اسم السيلزمان من السيلز أوردر
                    if hasattr(move.picking_id.sale_id, 'salesman_id') and move.picking_id.sale_id.salesman_id:
                        salesman_name = move.picking_id.sale_id.salesman_id.name
                    elif move.picking_id.sale_id.user_id:
                        salesman_name = move.picking_id.sale_id.user_id.name

                # Check if it's from a purchase order
                elif hasattr(move.picking_id, 'purchase_id') and move.picking_id.purchase_id:
                    purchase_order_name = move.picking_id.purchase_id.name
                else:
                    # Try to find via origin
                    if move.picking_id.origin:
                        # Check if origin is a sale order
                        sale_order = self.env['sale.order'].search([
                            ('name', '=', move.picking_id.origin)
                        ], limit=1)
                        if sale_order:
                            sale_order_name = sale_order.name
                            if hasattr(sale_order, 'salesman_id') and sale_order.salesman_id:
                                salesman_name = sale_order.salesman_id.name
                            elif sale_order.user_id:
                                salesman_name = sale_order.user_id.name
                        else:
                            # Check if origin is a purchase order
                            purchase_order = self.env['purchase.order'].search([
                                ('name', '=', move.picking_id.origin)
                            ], limit=1)
                            if purchase_order:
                                purchase_order_name = purchase_order.name

            # في حالة عدم وجود picking_id، ابحث عن المصدر من move line
            elif move.move_line_ids:
                for line in move.move_line_ids:
                    if line.move_id.sale_line_id:
                        sale_order = line.move_id.sale_line_id.order_id
                        sale_order_name = sale_order.name
                        if hasattr(sale_order, 'salesman_id') and sale_order.salesman_id:
                            salesman_name = sale_order.salesman_id.name
                        elif sale_order.user_id:
                            salesman_name = sale_order.user_id.name
                        break
                    elif hasattr(line.move_id, 'purchase_line_id') and line.move_id.purchase_line_id:
                        purchase_order = line.move_id.purchase_line_id.order_id
                        purchase_order_name = purchase_order.name
                        break

            # Get partner info
            partner_name = ''
            if move.picking_id:
                if move.picking_id.partner_id:
                    partner_name = move.picking_id.partner_id.name
                elif move.picking_id.picking_type_id:
                    partner_name = move.picking_id.picking_type_id.name

            # Get document type
            doc_type = ''
            if move.picking_id and move.picking_id.picking_type_id:
                doc_type = move.picking_id.picking_type_id.name

            # تحديد نوع المستند (SO/PO/Return)
            reference_doc = ''
            if sale_order_name:
                # Check if it's a return
                if 'return' in doc_type.lower() or move.origin_returned_move_id:
                    reference_doc = f"RET-{sale_order_name}"
                else:
                    reference_doc = sale_order_name
            elif purchase_order_name:
                # Check if it's a return
                if 'return' in doc_type.lower() or move.origin_returned_move_id:
                    reference_doc = f"RET-{purchase_order_name}"
                else:
                    reference_doc = purchase_order_name

            movements.append({
                'date': move.date.strftime('%d/%m/%Y') if move.date else '',
                'document': move.picking_id.name if move.picking_id else move.reference or '',
                'reference': reference_doc,  # SO/PO number
                'type': doc_type,
                'partner': partner_name,
                'salesman': salesman_name if issue_qty > 0 else '',  # فقط في حالة الخروج
                'location_from': move.location_id.complete_name or move.location_id.name,
                'location_to': move.location_dest_id.complete_name or move.location_dest_id.name,
                'receipt_qty': receipt_qty,
                'issue_qty': issue_qty,
                'balance': running_balance,
            })

        return {
            'product_name': product.name,
            'product_code': product.default_code,
            'opening_balance': opening_balance,
            'closing_balance': running_balance,
            'movements': movements,
        }

    def _calculate_opening_balance(self, product, locations, date_from):
        """Calculate opening balance for a product"""
        domain = [
            ('product_id', '=', product.id),
            ('state', '=', 'done'),
            ('date', '<', date_from),
        ]

        if locations:
            location_ids = locations.ids
            domain.append('|')
            domain.append(('location_id', 'in', location_ids))
            domain.append(('location_dest_id', 'in', location_ids))

        moves = self.env['stock.move'].search(domain)

        balance = 0
        for move in moves:
            from_internal = move.location_id.usage == 'internal'
            to_internal = move.location_dest_id.usage == 'internal'

            if locations:
                from_in_filter = move.location_id.id in locations.ids
                to_in_filter = move.location_dest_id.id in locations.ids

                if to_in_filter and not from_in_filter:
                    balance += move.product_uom_qty
                elif from_in_filter and not to_in_filter:
                    balance -= move.product_uom_qty
            else:
                if to_internal and not from_internal:
                    balance += move.product_uom_qty
                elif from_internal and not to_internal:
                    balance -= move.product_uom_qty

        return balance

    def action_export_excel(self):
        """Export to Excel action"""
        import xlsxwriter
        import io
        import base64

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)

        # Formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })

        product_header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#667eea',
            'font_color': 'white',
            'font_size': 12,
            'border': 1
        })

        money_format = workbook.add_format({
            'num_format': '#,##0.00',
            'border': 1
        })

        receipt_format = workbook.add_format({
            'num_format': '#,##0.00',
            'font_color': 'green',
            'border': 1
        })

        issue_format = workbook.add_format({
            'num_format': '#,##0.00',
            'font_color': 'red',
            'border': 1
        })

        # Get report data
        data = self.get_report_data()
        products_data = data.get('products', [])

        if not products_data:
            worksheet = workbook.add_worksheet('No Data')
            worksheet.write(0, 0, 'No data found for selected criteria')
            workbook.close()
            output.seek(0)
        else:
            # Create a worksheet for each product
            for product_info in products_data:
                sheet_name = product_info['product_code'] or product_info['product_name']
                sheet_name = sheet_name[:31].replace('/', '-').replace('\\', '-')

                worksheet = workbook.add_worksheet(sheet_name)

                # Write product header
                row = 0
                worksheet.merge_range(row, 0, row, 8,
                                      f"{product_info['product_name']} ({product_info['product_code'] or 'N/A'})",
                                      product_header_format)

                row += 1
                worksheet.write(row, 0, f"Opening Balance: {product_info['opening_balance']:,.2f}")
                worksheet.write(row, 8, f"Closing Balance: {product_info['closing_balance']:,.2f}")

                row += 2

                # Write headers
                headers = ['Date', 'Document', 'Type', 'Partner', 'Location From',
                           'Location To', 'Receipt Qty', 'Issue Qty', 'Balance']
                for col, header in enumerate(headers):
                    worksheet.write(row, col, header, header_format)

                # Write movements
                for movement in product_info['movements']:
                    row += 1
                    worksheet.write(row, 0, movement['date'])
                    worksheet.write(row, 1, movement['document'])
                    worksheet.write(row, 2, movement['type'])
                    worksheet.write(row, 3, movement['partner'])
                    worksheet.write(row, 4, movement['location_from'])
                    worksheet.write(row, 5, movement['location_to'])
                    worksheet.write(row, 6, movement['receipt_qty'],
                                    receipt_format if movement['receipt_qty'] > 0 else money_format)
                    worksheet.write(row, 7, movement['issue_qty'],
                                    issue_format if movement['issue_qty'] > 0 else money_format)
                    worksheet.write(row, 8, movement['balance'], money_format)

                # Auto-fit columns
                worksheet.set_column('A:A', 12)
                worksheet.set_column('B:B', 20)
                worksheet.set_column('C:C', 15)
                worksheet.set_column('D:D', 25)
                worksheet.set_column('E:F', 20)
                worksheet.set_column('G:I', 12)

        workbook.close()
        output.seek(0)

        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': f'stock_card_report_{fields.Date.today()}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    def action_refresh(self):
        """Refresh button action - for manual refresh if needed"""
        _logger.info("🔄 Manual refresh triggered")
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.card.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
            'context': dict(self.env.context)
        }