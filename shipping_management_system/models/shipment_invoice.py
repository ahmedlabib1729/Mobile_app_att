# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ShipmentOrder(models.Model):
    _inherit = 'shipment.order'

    # ===== ربط الشحنة بفواتير العملاء =====
    invoice_ids = fields.One2many(
        'account.move',
        'shipment_id',
        string='Customer Invoices',
        readonly=True,
        domain=[('move_type', '=', 'out_invoice')]
    )

    invoice_count = fields.Integer(
        string='Invoice Count',
        compute='_compute_invoice_count',
        store=True
    )

    invoice_status = fields.Selection([
        ('no_invoice', 'Not Invoiced'),
        ('to_invoice', 'To Invoice'),
        ('invoiced', 'Invoiced'),
    ], string='Invoice Status',
        compute='_compute_invoice_status',
        store=True,
        default='no_invoice'
    )

    # ===== ربط الشحنة بفواتير الموردين =====
    vendor_bill_ids = fields.One2many(
        'account.move',
        'shipment_vendor_id',
        string='Vendor Bills',
        readonly=True,
        domain=[('move_type', '=', 'in_invoice')]
    )

    vendor_bill_count = fields.Integer(
        string='Vendor Bill Count',
        compute='_compute_vendor_bill_count',
        store=True
    )

    vendor_bill_status = fields.Selection([
        ('no_bill', 'No Bill'),
        ('to_bill', 'To Bill'),
        ('billed', 'Billed'),
    ], string='Vendor Bill Status',
        compute='_compute_vendor_bill_status',
        store=True,
        default='no_bill'
    )

    # ===== Compute Methods للعملاء =====
    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for record in self:
            record.invoice_count = len(record.invoice_ids)

    @api.depends('invoice_ids', 'invoice_ids.state', 'invoice_ids.payment_state')
    def _compute_invoice_status(self):
        for record in self:
            valid_invoices = record.invoice_ids.filtered(lambda inv: inv.state != 'cancel')

            if not valid_invoices:
                record.invoice_status = 'to_invoice' if record.state in ['confirmed', 'picked', 'in_transit',
                                                                         'out_for_delivery',
                                                                         'delivered'] else 'no_invoice'
            else:
                record.invoice_status = 'invoiced'

    # ===== Compute Methods للموردين =====
    @api.depends('vendor_bill_ids')
    def _compute_vendor_bill_count(self):
        for record in self:
            record.vendor_bill_count = len(record.vendor_bill_ids)

    @api.depends('vendor_bill_ids', 'vendor_bill_ids.state', 'shipping_company_id')
    def _compute_vendor_bill_status(self):
        for record in self:
            if not record.shipping_company_id:
                record.vendor_bill_status = 'no_bill'
            else:
                valid_bills = record.vendor_bill_ids.filtered(lambda bill: bill.state != 'cancel')

                if not valid_bills:
                    record.vendor_bill_status = 'to_bill' if record.state in ['confirmed', 'picked', 'in_transit',
                                                                              'out_for_delivery',
                                                                              'delivered'] else 'no_bill'
                else:
                    record.vendor_bill_status = 'billed'

    # ===== Action Methods للعملاء =====
    def action_create_invoice(self):
        """إنشاء فاتورة للعميل مع التفاصيل المحدثة"""
        self.ensure_one()

        # التحقق من الحالة
        if self.state in ['draft', 'cancelled']:
            raise UserError(_('Cannot create invoice for draft or cancelled shipment!'))

        if not self.sender_id:
            raise UserError(_('Please select a customer (sender) first!'))

        # التحقق من الأسعار - استخدام السعر المحسوب الجديد
        if not self.calculated_customer_price or self.calculated_customer_price <= 0:
            raise UserError(_('Please calculate the shipping price first!'))

        # إنشاء الفاتورة
        invoice_vals = self._prepare_invoice_values()
        invoice = self.env['account.move'].create(invoice_vals)

        # عرض الفاتورة
        return {
            'type': 'ir.actions.act_window',
            'name': _('Customer Invoice'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'view_id': False,
            'context': {'default_move_type': 'out_invoice'},
            'target': 'current',
        }

    def action_view_invoices(self):
        """عرض فواتير العملاء المرتبطة بالشحنة"""
        self.ensure_one()

        action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_out_invoice_type')

        if len(self.invoice_ids) > 1:
            action['domain'] = [('id', 'in', self.invoice_ids.ids)]
        elif self.invoice_ids:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            action['views'] = form_view
            action['res_id'] = self.invoice_ids.id
        else:
            action = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Invoices'),
                    'message': _(
                        'No customer invoices found for this shipment. Click "Create Invoice" to generate one.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        return action

    # ===== Action Methods للموردين =====
    def action_create_vendor_bill(self):
        """إنشاء فاتورة مورد لشركة الشحن"""
        self.ensure_one()

        if self.state in ['draft', 'cancelled']:
            raise UserError(_('Cannot create vendor bill for draft or cancelled shipment!'))

        if not self.shipping_company_id:
            raise UserError(_('Please select a shipping company first!'))

        vendor_partner = self._get_shipping_vendor_partner()

        if not vendor_partner:
            raise UserError(_(
                'Could not create vendor partner for shipping company %s.'
            ) % self.shipping_company_id.name)

        if not self.shipping_cost or self.shipping_cost <= 0:
            raise UserError(_('Please calculate the shipping cost first!'))

        vendor_bill_vals = self._prepare_vendor_bill_values()
        vendor_bill = self.env['account.move'].create(vendor_bill_vals)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Vendor Bill'),
            'res_model': 'account.move',
            'res_id': vendor_bill.id,
            'view_mode': 'form',
            'view_id': False,
            'context': {'default_move_type': 'in_invoice'},
            'target': 'current',
        }

    def action_view_vendor_bills(self):
        """عرض فواتير المورد المرتبطة بالشحنة"""
        self.ensure_one()

        action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_in_invoice_type')

        if len(self.vendor_bill_ids) > 1:
            action['domain'] = [('id', 'in', self.vendor_bill_ids.ids)]
        elif self.vendor_bill_ids:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            action['views'] = form_view
            action['res_id'] = self.vendor_bill_ids.id
        else:
            action = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Vendor Bills'),
                    'message': _(
                        'No vendor bills found for this shipment. Click "Create Vendor Bill" to generate one.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        return action

    # ===== Helper Methods للعملاء - محدث =====
    def _prepare_invoice_values(self):
        """تحضير قيم فاتورة العميل - سطر واحد فقط مع اختيار الدافع"""
        self.ensure_one()

        journal = self.env['account.journal'].search([
            ('type', '=', 'sale')
        ], limit=1)

        if not journal:
            raise UserError(_('Please configure a sales journal first!'))

        # تحديد الشريك الذي ستصدر له الفاتورة
        if self.payment_method == 'prepaid' and self.prepaid_payer == 'recipient':
            invoice_partner = self.recipient_id
        else:
            invoice_partner = self.sender_id

        if not invoice_partner:
            raise UserError(_('Please select the invoice partner!'))

        # حساب المبلغ النهائي
        if hasattr(self, 'calculated_customer_price') and self.calculated_customer_price > 0:
            final_amount = self.calculated_customer_price
        else:
            final_amount = self.final_customer_price

        # وصف بسيط
        description = f"Shipping Service - Order #{self.order_number}\n"
        description += f"From: {self.sender_city or 'N/A'} To: {self.recipient_city}\n"

        # إضافة توضيح من يدفع
        if self.payment_method == 'prepaid':
            description += f"Payment by: {invoice_partner.name}"

        invoice_lines = [(0, 0, {
            'name': description,
            'quantity': 1,
            'price_unit': final_amount,
            'account_id': self._get_income_account().id,
        })]

        narration = f'Invoice for Shipment {self.order_number}'
        if self.tracking_number:
            narration += f'\nTracking: {self.tracking_number}'

        if self.payment_method == 'cod':
            narration += f'\n\n⚠️ IMPORTANT: We will collect {self.cod_amount:.2f} EGP from the recipient.'
            narration += f'\nAfter deducting our fees, we will return {self.cod_amount - self.final_customer_price:.2f} EGP to you.'

        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': invoice_partner.id,  # استخدام الشريك المحدد
            'invoice_date': fields.Date.today(),
            'journal_id': journal.id,
            'currency_id': self.env.company.currency_id.id,
            'shipment_id': self.id,
            'ref': self.order_number,
            'narration': narration,
            'invoice_line_ids': invoice_lines,
        }

        return invoice_vals

    def _prepare_invoice_line_company_cost(self, company_costs):
        """تحضير سطر تكاليف الشركة"""
        account = self._get_income_account()

        description = f"Handling & Processing Fees - {self.order_number}\n"
        description += f"Base Fee: {company_costs['base_cost']:.2f} EGP\n"
        if company_costs['weight_cost'] > 0:
            description += f"Weight Charges ({self.total_weight} KG): {company_costs['weight_cost']:.2f} EGP\n"
        if company_costs['handling_fee'] > 0:
            description += f"Handling Fee: {company_costs['handling_fee']:.2f} EGP\n"
        if company_costs.get('pickup_fee', 0) > 0:
            description += f"Pickup Service Fee: {company_costs['pickup_fee']:.2f} EGP"

        return {
            'name': description,
            'quantity': 1,
            'price_unit': company_costs['total'],
            'account_id': account.id if account else False,
        }

    def _prepare_invoice_line_shipping_cost(self, shipping_costs):
        """تحضير سطر تكاليف شركة الشحن"""
        account = self._get_income_account()

        description = f"Shipping Service - {self.shipping_company_id.name if self.shipping_company_id else 'N/A'}\n"
        description += f"From: {self.sender_city or 'N/A'} To: {self.recipient_city}\n"
        description += f"Base Shipping: {shipping_costs['base_cost']:.2f} EGP\n"

        if shipping_costs['weight_cost'] > 0:
            description += f"Weight Charges: {shipping_costs['weight_cost']:.2f} EGP\n"
        if shipping_costs['cod_fee'] > 0:
            description += f"COD Fee: {shipping_costs['cod_fee']:.2f} EGP\n"
        if shipping_costs['insurance_fee'] > 0:
            description += f"Insurance: {shipping_costs['insurance_fee']:.2f} EGP\n"
        if shipping_costs['pickup_fee'] > 0:
            description += f"Pickup Fee: {shipping_costs['pickup_fee']:.2f} EGP"

        return {
            'name': description,
            'quantity': 1,
            'price_unit': shipping_costs['total'],
            'account_id': account.id if account else False,
        }

    def _prepare_invoice_line_additional_fees(self):
        """تحضير سطر الرسوم الإضافية"""
        account = self._get_income_account()

        description = "Additional Services:\n"
        for fee in self.additional_service_ids:
            description += f"• {fee.name}: {fee.fee_amount:.2f} EGP\n"

        return {
            'name': description.rstrip(),
            'quantity': 1,
            'price_unit': self.total_additional_fees,
            'account_id': account.id if account else False,
        }

    def _prepare_invoice_line_discount(self):
        """تحضير سطر الخصم (على تكاليف الشركة فقط)"""
        account = self._get_income_account()

        description = f"Customer Discount ({self.discount_percentage}%)"
        if self.customer_category_id:
            description += f" - Category: {self.customer_category_id.name}\n"

        # توضيح أن الخصم على خدمات الشركة فقط
        discountable = self.total_company_cost + self.total_additional_fees
        description += f"Applied on company services: {discountable:.2f} EGP"

        return {
            'name': description,
            'quantity': 1,
            'price_unit': -self.discount_amount,  # سالب لأنه خصم
            'account_id': account.id if account else False,
        }

    def _get_income_account(self):
        """الحصول على حساب الإيرادات"""
        account = self.env['account.account'].search([
            ('account_type', '=', 'income')
        ], limit=1)

        if not account:
            account = self.env['account.account'].search([
                ('account_type', 'in', ['income', 'income_other'])
            ], limit=1)

        if not account:
            raise UserError(_('No income account found! Please configure your chart of accounts first.'))

        return account

    # ===== Helper Methods للموردين =====
    def _get_shipping_vendor_partner(self):
        """الحصول على شريك المورد لشركة الشحن أو إنشاؤه"""
        self.ensure_one()

        if not self.shipping_company_id:
            return False

        partner = self.env['res.partner'].search([
            ('name', '=', self.shipping_company_id.name),
            ('supplier_rank', '>', 0)
        ], limit=1)

        if not partner:
            partner = self.env['res.partner'].search([
                ('name', '=', self.shipping_company_id.name)
            ], limit=1)

            if partner:
                partner.supplier_rank = 1
            else:
                partner = self.env['res.partner'].create({
                    'name': self.shipping_company_id.name,
                    'supplier_rank': 1,
                    'is_company': True,
                    'phone': self.shipping_company_id.phone or False,
                    'email': self.shipping_company_id.email or False,
                    'website': self.shipping_company_id.website or False,
                    'comment': f'Auto-created vendor for shipping company {self.shipping_company_id.name}'
                })

        return partner

    def _prepare_vendor_bill_values(self):
        """تحضير قيم فاتورة المورد"""
        self.ensure_one()

        journal = self.env['account.journal'].search([
            ('type', '=', 'purchase')
        ], limit=1)

        if not journal:
            raise UserError(_('Please configure a purchase journal first!'))

        vendor_partner = self._get_shipping_vendor_partner()

        invoice_lines = []

        vendor_line_vals = self._prepare_vendor_bill_line()
        invoice_lines.append((0, 0, vendor_line_vals))

        vendor_bill_vals = {
            'move_type': 'in_invoice',
            'partner_id': vendor_partner.id,
            'invoice_date': fields.Date.today(),
            'journal_id': journal.id,
            'currency_id': self.env.company.currency_id.id,
            'shipment_vendor_id': self.id,
            'ref': f'{self.order_number} - {self.tracking_number or ""}',
            'narration': f'Vendor Bill for Shipment {self.order_number} from {self.shipping_company_id.name}',
            'invoice_line_ids': invoice_lines,
        }

        return vendor_bill_vals

    def _prepare_vendor_bill_line(self):
        """تحضير سطر فاتورة المورد"""
        account = self.env['account.account'].search([
            ('account_type', '=', 'expense')
        ], limit=1)

        if not account:
            account = self.env['account.account'].search([
                ('account_type', 'in', ['expense', 'expense_direct_cost'])
            ], limit=1)

        if not account:
            raise UserError(_('No expense account found! Please configure your chart of accounts first.'))

        description = f"Shipping Service - {self.order_number}\n"
        description += f"From: {self.sender_city or 'N/A'} To: {self.recipient_city}\n"
        description += f"Weight: {self.total_weight} KG\n"
        if self.tracking_number:
            description += f"Tracking: {self.tracking_number}"

        return {
            'name': description,
            'quantity': 1,
            'price_unit': self.shipping_cost,
            'account_id': account.id if account else False,
        }


class AccountMove(models.Model):
    _inherit = 'account.move'

    shipment_id = fields.Many2one(
        'shipment.order',
        string='Related Shipment (Customer)',
        readonly=True,
        ondelete='set null'
    )

    shipment_vendor_id = fields.Many2one(
        'shipment.order',
        string='Related Shipment (Vendor)',
        readonly=True,
        ondelete='set null'
    )

    tracking_number = fields.Char(
        compute='_compute_tracking_number',
        string='Tracking Number',
        readonly=True,
        store=True
    )

    shipping_company = fields.Char(
        compute='_compute_shipping_info',
        string='Shipping Company',
        store=True
    )

    @api.depends('shipment_id', 'shipment_vendor_id')
    def _compute_tracking_number(self):
        for record in self:
            if record.shipment_id:
                record.tracking_number = record.shipment_id.tracking_number
            elif record.shipment_vendor_id:
                record.tracking_number = record.shipment_vendor_id.tracking_number
            else:
                record.tracking_number = False

    @api.depends('shipment_id', 'shipment_vendor_id')
    def _compute_shipping_info(self):
        for record in self:
            shipment = record.shipment_id or record.shipment_vendor_id
            if shipment and shipment.shipping_company_id:
                record.shipping_company = shipment.shipping_company_id.name
            else:
                record.shipping_company = False

    def unlink(self):
        """عند حذف الفاتورة، نحدث حالة الشحنة"""
        customer_shipments = self.mapped('shipment_id')
        vendor_shipments = self.mapped('shipment_vendor_id')
        result = super(AccountMove, self).unlink()

        if customer_shipments:
            customer_shipments._compute_invoice_status()
        if vendor_shipments:
            vendor_shipments._compute_vendor_bill_status()

        return result