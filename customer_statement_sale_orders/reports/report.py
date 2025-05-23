# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime


class ReportjtSaleOrderCustomerStatement(models.AbstractModel):
    _name = 'report.customer_statement_sale_orders.action_statement'
    _description = 'SO Customer Statement'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = {}
        filtered_invoices = {}  # قاموس لتخزين الفواتير المصفاة
        partner_ids = data.get('partners') or []
        partners = self.env['res.partner'].browse(partner_ids)
        company = self.env.company
        filter_by = data.get('filter_by', 'sale_order')

        # تحويل التواريخ إلى كائنات datetime
        date_from = None
        date_to = None
        if data.get('date_from') and data.get('date_to'):
            date_from = datetime.strptime(data.get('date_from'), '%Y-%m-%d %H:%M:%S').date()
            date_to = datetime.strptime(data.get('date_to'), '%Y-%m-%d %H:%M:%S').date()

        for partner in partners:
            if filter_by == 'sale_order':
                # التصفية حسب تاريخ أمر البيع (المنطق الأصلي)
                domain = [('state', 'not in', ('draft', 'cancel')),
                          ('company_id', '=', company.id),
                          ('partner_id', '=', partner.id)]

                if date_from and date_to:
                    domain += [('date_order', '>=', data.get('date_from')),
                               ('date_order', '<=', data.get('date_to'))]

                sale_orders = self.env['sale.order'].search(domain)
                docs[partner] = sale_orders
                filtered_invoices[partner.id] = False  # لا نحتاج لتصفية الفواتير في هذه الحالة

            else:  # filter_by == 'invoice'
                # التصفية حسب تاريخ الفاتورة
                invoice_domain = [
                    ('state', 'not in', ('draft', 'cancel')),
                    ('company_id', '=', company.id),
                    ('partner_id', '=', partner.id),
                    ('move_type', 'in', ('out_invoice', 'out_refund'))
                ]

                if date_from and date_to:
                    invoice_domain += [('date', '>=', date_from),
                                       ('date', '<=', date_to)]

                invoices = self.env['account.move'].search(invoice_domain)

                # تخزين معرفات الفواتير المصفاة
                filtered_invoices[partner.id] = invoices.ids

                # الحصول على أوامر البيع المرتبطة بهذه الفواتير
                sale_order_ids = invoices.mapped('invoice_line_ids.sale_line_ids.order_id')
                docs[partner] = sale_order_ids

        values = {
            'doc_ids': partners.ids,
            'doc_model': 'sale.order',
            'data': data,
            'docs': docs,
            'company': company,
            'filter_by': filter_by,
            'filtered_invoices': filtered_invoices,  # إضافة معرفات الفواتير المصفاة
        }

        if date_from and date_to:
            values['dates'] = [date_from, date_to]

        return values