# models/sales_report.py
from odoo import models, fields, api
from datetime import datetime
import json
import logging

_logger = logging.getLogger(__name__)


class SalesReportWizard(models.TransientModel):
    _name = 'sales.report.wizard'
    _description = 'Sales Report Wizard'
    _rec_name = 'report_type'


    report_type = fields.Selection([
        ('itemwise_details', 'Invoice Details'),
        ('employeewise_summary', 'Employeewise Summary'),
        ('customerwise_datewise', 'Customerwise Datewise Summary'),
    ], string='Report Type', default='itemwise_details', required=True)

    date_from = fields.Date('From Date', default=lambda self: datetime.now().replace(day=1))
    date_to = fields.Date('To Date', default=fields.Date.today())

    partner_ids = fields.Many2many('res.partner', string='Customers')
    partner_type = fields.Selection([
        ('customer', 'Customer'),
        ('vendor', 'Vendor'),
        ('all', 'All'),
    ], string='Partner Type', default='all')

    salesman_ids = fields.Many2many(
        'res.partner',
        'sales_report_salesman_rel',
        string='Salesmen',
        domain=[('is_salesman', '=', True)]
    )

    # حقول البحث والفلترة
    search_text = fields.Char('Search', help='Search in product name, code, or remark type')

    # حقل جديد لاختيار المنتجات
    product_ids = fields.Many2many('product.product', string='Products',
                                   domain=[('sale_ok', '=', True)])

    # حقل جديد لفلترة حسب Remark Type
    remark_type_ids = fields.Many2many('product.remark.type', string='Remark Types')

    # حقل لتخزين نتائج البحث
    report_html = fields.Html('Report Results', compute='_compute_report_html')

    @api.model
    def default_get(self, fields):
        """Override default_get to check if remark type model exists"""
        res = super().default_get(fields)

        # Check if product.remark.type model exists and has access
        try:
            self.env['product.remark.type'].check_access_rights('read')
        except:
            _logger.warning("No access to product.remark.type model")
            # Remove remark_type_ids from view if no access
            if 'remark_type_ids' in res:
                del res['remark_type_ids']

        return res

    @api.onchange('report_type', 'date_from', 'date_to', 'partner_type', 'partner_ids',
                  'search_text', 'product_ids', 'remark_type_ids', 'salesman_ids')
    def _onchange_filters(self):
        """تحديث التقرير تلقائياً عند تغيير أي فلتر"""
        pass

    @api.depends('report_type', 'date_from', 'date_to', 'partner_ids',
                 'product_ids', 'remark_type_ids', 'search_text', 'salesman_ids')
    def _compute_report_html(self):
        """يُحسب تلقائياً عند تغيير أي فلتر"""
        for wizard in self:
            data = wizard.get_report_data()
            wizard.report_html = wizard._generate_html_report(data)

    def _generate_html_report(self, data):
        """Generate HTML table from report data"""
        if not data or not data.get('rows'):
            return '<div style="text-align: center; padding: 20px; color: #666;">No data found for selected criteria</div>'

        # Summary Cards HTML
        summary = data.get('summary', {})

        # عرض البطاقات حسب نوع التقرير
        if self.report_type == 'itemwise_details':
            html = f'''
            <div style="margin-bottom: 20px;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px;">
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <div style="font-size: 28px; font-weight: bold;">{summary.get('invoices', 0)}</div>
                        <div style="font-size: 14px; opacity: 0.9;">Total Invoices</div>
                    </div>
                    <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <div style="font-size: 28px; font-weight: bold;">{int(summary.get('items', 0))}</div>
                        <div style="font-size: 14px; opacity: 0.9;">Total Items</div>
                    </div>
                    <div style="background: linear-gradient(135deg, #667eea 0%, #4e54c8 100%); color: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <div style="font-size: 28px; font-weight: bold;">{summary.get('total', 0):,.2f}</div>
                        <div style="font-size: 14px; opacity: 0.9;">Total Sales</div>
                    </div>
                    <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <div style="font-size: 28px; font-weight: bold;">{summary.get('cost', 0):,.2f}</div>
                        <div style="font-size: 14px; opacity: 0.9;">Total Cost</div>
                    </div>
                    <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <div style="font-size: 28px; font-weight: bold;">{summary.get('profit', 0):,.2f}</div>
                        <div style="font-size: 14px; opacity: 0.9;">Total Profit</div>
                    </div>
                    <div style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); color: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <div style="font-size: 28px; font-weight: bold;">{summary.get('profit_margin', 0):.1f}%</div>
                        <div style="font-size: 14px; opacity: 0.9;">Profit Margin</div>
                    </div>
                </div>
            </div>
            '''
        elif self.report_type == 'employeewise_summary':
            html = f'''
            <div style="margin-bottom: 20px;">
                <div style="display: flex; gap: 15px; flex-wrap: wrap;">
                    <div style="background: #6c63ff; color: white; padding: 20px; border-radius: 10px; flex: 1; min-width: 200px;">
                        <div style="font-size: 28px; font-weight: bold;">{summary.get('invoices', 0)}</div>
                        <div style="font-size: 14px;">Total Invoices</div>
                    </div>
                    <div style="background: #00b4d8; color: white; padding: 20px; border-radius: 10px; flex: 1; min-width: 200px;">
                        <div style="font-size: 28px; font-weight: bold;">{int(summary.get('items', 0))}</div>
                        <div style="font-size: 14px;">Total Quantity</div>
                    </div>
                    <div style="background: #27ae60; color: white; padding: 20px; border-radius: 10px; flex: 1; min-width: 200px;">
                        <div style="font-size: 28px; font-weight: bold;">{summary.get('total', 0):,.2f}</div>
                        <div style="font-size: 14px;">Total Sales</div>
                    </div>
                </div>
            </div>
            '''
        else:  # customerwise_datewise
            html = f'''
            <div style="margin-bottom: 20px;">
                <div style="display: flex; gap: 15px; flex-wrap: wrap;">
                    <div style="background: #9b59b6; color: white; padding: 20px; border-radius: 10px; flex: 1; min-width: 200px;">
                        <div style="font-size: 28px; font-weight: bold;">{summary.get('invoices', 0)}</div>
                        <div style="font-size: 14px;">Total Invoices</div>
                    </div>
                    <div style="background: #3498db; color: white; padding: 20px; border-radius: 10px; flex: 1; min-width: 200px;">
                        <div style="font-size: 28px; font-weight: bold;">{summary.get('total', 0):,.2f}</div>
                        <div style="font-size: 14px;">Total Amount</div>
                    </div>
                    <div style="background: #e74c3c; color: white; padding: 20px; border-radius: 10px; flex: 1; min-width: 200px;">
                        <div style="font-size: 28px; font-weight: bold;">{summary.get('tax', 0):,.2f}</div>
                        <div style="font-size: 14px;">Total Tax</div>
                    </div>
                </div>
            </div>
            '''

        # Table HTML
        rows = data.get('rows', [])
        if rows:
            html += '<div style="overflow-x: auto; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);"><table class="table table-striped table-bordered" style="width: 100%; font-size: 13px; margin: 0;">'

            # Headers
            html += '<thead><tr style="background: #2c3e50;">'
            for key in rows[0].keys():
                header = key.replace('_', ' ').title()
                html += f'<th style="color: white; padding: 12px 8px; white-space: nowrap; font-weight: 600;">{header}</th>'
            html += '</tr></thead>'

            # Body
            html += '<tbody>'
            for i, row in enumerate(rows):
                # Alternating row colors
                bg_color = '#ffffff' if i % 2 == 0 else '#f8f9fa'
                html += f'<tr style="background: {bg_color};">'

                for key, value in row.items():
                    if isinstance(value, float):
                        # تلوين الأرباح والخسائر
                        if 'profit' in key.lower():
                            color = '#27ae60' if value >= 0 else '#e74c3c'
                            html += f'<td style="padding: 10px 8px; text-align: right; color: {color}; font-weight: bold;">{value:,.2f}</td>'
                        elif 'margin' in key.lower() or 'percentage' in key.lower():
                            color = '#27ae60' if value >= 0 else '#e74c3c'
                            html += f'<td style="padding: 10px 8px; text-align: right; color: {color}; font-weight: bold;">{value:.1f}%</td>'
                        else:
                            html += f'<td style="padding: 10px 8px; text-align: right;">{value:,.2f}</td>'
                    else:
                        html += f'<td style="padding: 10px 8px;">{value}</td>'
                html += '</tr>'
            html += '</tbody>'

            # Footer with totals for itemwise report
            if self.report_type == 'itemwise_details' and rows:
                html += '<tfoot><tr style="font-weight: bold; background: #ecf0f1;">'
                html += '<td colspan="7" style="text-align: right; padding: 12px; font-size: 14px;">TOTALS:</td>'

                # Calculate totals
                total_qty = sum(r.get('quantity', 0) for r in rows)
                total_sales = sum(r.get('total', 0) for r in rows)
                total_cost = sum(r.get('cost', 0) for r in rows)
                total_profit = sum(r.get('profit', 0) for r in rows)
                avg_margin = (total_profit / total_sales * 100) if total_sales else 0

                html += f'<td style="text-align: right; padding: 12px; font-size: 14px;">{total_qty:,.2f}</td>'
                html += '<td></td>'  # Price column
                html += '<td></td>'  # Discount column
                html += '<td></td>'  # Tax column
                html += f'<td style="text-align: right; padding: 12px; font-size: 14px;">{total_sales:,.2f}</td>'
                html += f'<td style="text-align: right; padding: 12px; font-size: 14px;">{total_cost:,.2f}</td>'
                html += f'<td style="text-align: right; padding: 12px; font-size: 14px; color: {"#27ae60" if total_profit >= 0 else "#e74c3c"};">{total_profit:,.2f}</td>'
                html += f'<td style="text-align: right; padding: 12px; font-size: 14px; color: {"#27ae60" if avg_margin >= 0 else "#e74c3c"};">{avg_margin:.1f}%</td>'
                html += '</tr></tfoot>'

            html += '</table></div>'

            # إضافة معلومات إضافية
            html += f'''
            <div style="margin-top: 20px; padding: 15px; background: #ecf0f1; border-radius: 8px;">
                <p style="margin: 0; color: #7f8c8d; font-size: 12px;">
                    Report generated on {fields.Date.today()} | Total Records: {len(rows)}
                </p>
            </div>
            '''

        return html

    def get_report_data(self):
        """Generate report data based on filters"""
        self.ensure_one()

        domain = [
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
        ]

        if self.date_from:
            domain.append(('invoice_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('invoice_date', '<=', self.date_to))

        if self.salesman_ids:
            domain.append(('salesman_id', 'in', self.salesman_ids.ids))

        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
        elif self.partner_type == 'customer':
            domain.append(('partner_id.customer_rank', '>', 0))
        elif self.partner_type == 'vendor':
            domain.append(('partner_id.supplier_rank', '>', 0))

        invoices = self.env['account.move'].search(domain)

        if not invoices:
            return {'summary': {}, 'rows': []}

        # Summary variables
        total_sales = 0
        total_cost = 0
        total_profit = 0
        total_items = 0

        # Generate report rows based on type
        rows = []

        if self.report_type == 'itemwise_details':
            for invoice in invoices:
                # Get related sale order
                sale_order = self.env['sale.order'].search([
                    ('name', '=', invoice.invoice_origin)
                ], limit=1)

                # Filter invoice lines
                invoice_lines = invoice.invoice_line_ids.filtered(lambda l: l.product_id)

                # Apply product filter if selected
                if self.product_ids:
                    invoice_lines = invoice_lines.filtered(lambda l: l.product_id.id in self.product_ids.ids)

                # Apply remark type filter if selected and accessible
                if self.remark_type_ids:
                    try:
                        invoice_lines = invoice_lines.filtered(lambda l:
                                                               l.product_id.product_tmpl_id.remark_type_id.id in self.remark_type_ids.ids
                                                               if hasattr(l.product_id.product_tmpl_id,
                                                                          'remark_type_id') and l.product_id.product_tmpl_id.remark_type_id
                                                               else False
                                                               )
                    except:
                        _logger.warning("Error filtering by remark type")

                # Apply search text filter if provided
                if self.search_text:
                    search_terms = self.search_text.lower().split()

                    def matches_search(line):
                        """Check if line matches all search terms"""
                        searchable_text = ' '.join([
                            (line.product_id.name or ''),
                            (line.product_id.default_code or ''),
                            (line.product_id.barcode or ''),
                        ])

                        # Add remark type name if accessible
                        try:
                            if hasattr(line.product_id.product_tmpl_id,
                                       'remark_type_id') and line.product_id.product_tmpl_id.remark_type_id:
                                searchable_text += ' ' + line.product_id.product_tmpl_id.remark_type_id.name
                        except:
                            pass

                        searchable_text = searchable_text.lower()
                        return all(term in searchable_text for term in search_terms)

                    invoice_lines = invoice_lines.filtered(matches_search)

                for line in invoice_lines:
                    # Calculate cost and profit
                    cost_price = line.product_id.standard_price
                    total_cost_line = cost_price * line.quantity
                    profit = line.price_subtotal - total_cost_line
                    profit_margin = (profit / line.price_subtotal * 100) if line.price_subtotal else 0

                    # Update totals
                    total_sales += line.price_total
                    total_cost += total_cost_line
                    total_profit += profit
                    total_items += line.quantity

                    # Get remark type name safely
                    remark_type_name = ''
                    try:
                        if hasattr(line.product_id.product_tmpl_id,
                                   'remark_type_id') and line.product_id.product_tmpl_id.remark_type_id:
                            remark_type_name = line.product_id.product_tmpl_id.remark_type_id.name
                    except:
                        _logger.warning(f"Could not get remark type for product {line.product_id.name}")

                    rows.append({
                        'sale_order': sale_order.name if sale_order else invoice.invoice_origin or 'N/A',
                        'invoice_no': invoice.name,
                        'date': invoice.invoice_date.strftime('%d/%m/%Y') if invoice.invoice_date else '',
                        'customer': invoice.partner_id.name,
                        'salesman': invoice.salesman_id.name if hasattr(invoice,'salesman_id') and invoice.salesman_id else '',
                        # أضف هذا السطر
                        'item_code': line.product_id.default_code or '',
                        'item_name': line.product_id.name,
                        'remark_type': remark_type_name,
                        'quantity': line.quantity,
                        'price': line.price_unit,
                        'discount': line.discount,
                        'tax': line.price_total - line.price_subtotal,
                        'total': line.price_total,
                        'cost': total_cost_line,
                        'profit': profit,
                        'margin_%': round(profit_margin, 1),
                    })


        elif self.report_type == 'customerwise_datewise':

            customer_data = {}

            for invoice in invoices:

                key = (invoice.partner_id.id, invoice.invoice_date)

                if key not in customer_data:

                    # احصل على اسم Salesman

                    salesman_name = ''

                    if hasattr(invoice, 'salesman_id') and invoice.salesman_id:

                        salesman_name = invoice.salesman_id.name

                    elif invoice.invoice_user_id:

                        salesman_name = invoice.invoice_user_id.name + ' (User)'

                    customer_data[key] = {

                        'customer': invoice.partner_id.name,

                        'date': invoice.invoice_date.strftime('%d/%m/%Y') if invoice.invoice_date else '',

                        'salesman': salesman_name,  # أضف هذا السطر

                        'phone': invoice.partner_id.phone or invoice.partner_id.mobile or '',

                        'invoices': 0,

                        'total': 0,

                    }

                customer_data[key]['invoices'] += 1

                customer_data[key]['total'] += invoice.amount_total

                total_sales += invoice.amount_total

                total_items += len(invoice.invoice_line_ids.filtered(lambda l: l.product_id))

            rows = list(customer_data.values())

            rows.sort(key=lambda x: x['total'], reverse=True)



        # في models/sales_report.py - تحديث employeewise_summary

        elif self.report_type == 'employeewise_summary':

            salesman_data = {}

            for invoice in invoices:

                # استخدم Salesman إذا كان موجود

                if hasattr(invoice, 'salesman_id') and invoice.salesman_id:

                    key = invoice.salesman_id.id

                    name = invoice.salesman_id.name

                    code = invoice.salesman_id.ref or f'SM{invoice.salesman_id.id}'

                else:

                    # وإلا استخدم المستخدم

                    user = invoice.invoice_user_id or invoice.create_uid

                    key = f'user_{user.id}'

                    name = f"{user.name} (User)"

                    code = user.partner_id.ref or f'U{user.id}'

                if key not in salesman_data:
                    salesman_data[key] = {

                        'employee_code': code,

                        'employee': name,

                        'invoices': 0,

                        'quantity': 0,

                        'total': 0,

                    }

                salesman_data[key]['invoices'] += 1

                salesman_data[key]['quantity'] += sum(

                    line.quantity for line in invoice.invoice_line_ids.filtered(lambda l: l.product_id)

                )

                salesman_data[key]['total'] += invoice.amount_total

                total_sales += invoice.amount_total

                total_items += salesman_data[key]['quantity']

            # Calculate percentages

            for data in salesman_data.values():
                data['percentage'] = round((data['total'] / total_sales * 100) if total_sales else 0, 2)

            rows = list(salesman_data.values())

            rows.sort(key=lambda x: x['total'], reverse=True)

        # Calculate summary
        summary = {
            'invoices': len(invoices),
            'items': int(total_items),
            'total': total_sales,
            'tax': sum(inv.amount_tax for inv in invoices),
        }

        # Add cost and profit for itemwise report
        if self.report_type == 'itemwise_details':
            summary['cost'] = total_cost
            summary['profit'] = total_profit
            summary['profit_margin'] = round((total_profit / total_sales * 100) if total_sales else 0, 1)

        return {
            'summary': summary,
            'rows': rows,
        }

    def action_generate_report(self):
        """Generate report without creating new record"""
        # فقط حدّث الصفحة الحالية
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sales.report.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
            'flags': {'mode': 'readonly'}
        }

    def action_search(self):
        """Search button action - refresh the view with results"""
        target = self.env.context.get('default_target', 'current')

        return {
            'name': 'Sales Report',  # هذا العنوان الذي سيظهر
            'type': 'ir.actions.act_window',
            'res_model': 'sales.report.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': target,
            'context': dict(self.env.context, show_results=True),
            'flags': {'mode': 'readonly', 'breadcrumbs': False}  # أضف هذا
        }

    @api.onchange('search_text')
    def _onchange_search_text(self):
        """Auto-refresh when search text changes"""
        if self.report_type == 'itemwise_details':
            # This will trigger the recompute of report_html
            return {}

    def action_refresh(self):
        """Refresh button action"""
        # نفس الشيء للـ refresh
        target = self.env.context.get('default_target', 'current')

        return {
            'name': 'Sales Report',
            'type': 'ir.actions.act_window',
            'res_model': 'sales.report.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': target,
            'context': dict(self.env.context, show_results=True)
        }

    def action_export_excel(self):
        """Export to Excel action"""
        import xlsxwriter
        import io
        import base64

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Sales Report')

        # Formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1
        })

        money_format = workbook.add_format({
            'num_format': '#,##0.00',
            'border': 1
        })

        profit_format = workbook.add_format({
            'num_format': '#,##0.00',
            'font_color': 'green',
            'border': 1
        })

        loss_format = workbook.add_format({
            'num_format': '#,##0.00',
            'font_color': 'red',
            'border': 1
        })

        # Get report data
        data = self.get_report_data()

        # Write summary
        row = 0
        summary = data.get('summary', {})
        worksheet.write(row, 0, 'SALES REPORT SUMMARY', header_format)
        row += 1
        worksheet.write(row, 0, f"Report Type: {dict(self._fields['report_type'].selection).get(self.report_type)}")
        worksheet.write(row, 1, f"From: {self.date_from}")
        worksheet.write(row, 2, f"To: {self.date_to}")
        row += 1
        worksheet.write(row, 0, f"Total Invoices: {summary.get('invoices', 0)}")
        worksheet.write(row, 1, f"Total Items: {summary.get('items', 0)}")
        worksheet.write(row, 2, f"Total Sales: {summary.get('total', 0):,.2f}")
        if self.report_type == 'itemwise_details':
            worksheet.write(row, 3, f"Total Cost: {summary.get('cost', 0):,.2f}")
            worksheet.write(row, 4, f"Total Profit: {summary.get('profit', 0):,.2f}")
            worksheet.write(row, 5, f"Margin: {summary.get('profit_margin', 0):.1f}%")
        row += 2

        # Write headers
        rows_data = data.get('rows', [])
        if rows_data:
            headers = list(rows_data[0].keys())
            for col, header in enumerate(headers):
                worksheet.write(row, col, header.replace('_', ' ').title(), header_format)

            # Write data
            for row_data in rows_data:
                row += 1
                for col, header in enumerate(headers):
                    value = row_data[header]
                    if header == 'profit':
                        format_to_use = profit_format if value >= 0 else loss_format
                        worksheet.write(row, col, value, format_to_use)
                    elif isinstance(value, float) and header in ['total', 'cost', 'price', 'tax']:
                        worksheet.write(row, col, value, money_format)
                    else:
                        worksheet.write(row, col, value)

        workbook.close()
        output.seek(0)

        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': f'sales_report_{self.report_type}_{fields.Date.today()}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    def action_export_csv(self):
        """Export to CSV action"""
        import csv
        import io
        import base64

        output = io.StringIO()
        data = self.get_report_data()
        rows = data.get('rows', [])

        if rows:
            writer = csv.DictWriter(output, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': f'sales_report_{fields.Date.today()}.csv',
            'type': 'binary',
            'datas': base64.b64encode(output.getvalue().encode()),
            'mimetype': 'text/csv'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    def action_open_fullscreen(self):
        """Open report in fullscreen mode"""
        return {
            'name': 'Sales Report',
            'type': 'ir.actions.act_window',
            'res_model': 'sales.report.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'main',  # بدلاً من 'new' لفتحه في الصفحة الرئيسية
            'context': self.env.context,
        }

    def action_print(self):
        """Print action"""
        # For now, just close the window
        return {'type': 'ir.actions.act_window_close'}


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_salesman = fields.Boolean('Is Salesman', help='Check if this partner is a salesman')


class AccountMove(models.Model):
    _inherit = 'account.move'

    salesman_id = fields.Many2one(
        'res.partner',
        string='Salesman',
        domain=[('is_salesman', '=', True)],
        tracking=True,
        help='Salesman responsible for this invoice'
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to inherit salesman from sale order"""
        for vals in vals_list:
            # إذا كانت الفاتورة من أمر بيع ولم يتم تحديد salesman
            if 'invoice_origin' in vals and not vals.get('salesman_id'):
                # ابحث عن أمر البيع
                sale_order = self.env['sale.order'].search([
                    ('name', '=', vals['invoice_origin'])
                ], limit=1)
                if sale_order and sale_order.salesman_id:
                    vals['salesman_id'] = sale_order.salesman_id.id

        return super().create(vals_list)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    salesman_id = fields.Many2one(
        'res.partner',
        string='Salesman',
        domain=[('is_salesman', '=', True)],
        tracking=True,
        required=True,
        help='Select the salesman responsible for this order'
    )

    def _prepare_invoice(self):
        """Override to add salesman_id to invoice vals"""
        invoice_vals = super()._prepare_invoice()
        if self.salesman_id:
            invoice_vals['salesman_id'] = self.salesman_id.id
        return invoice_vals