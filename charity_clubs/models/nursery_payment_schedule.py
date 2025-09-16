# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class NurseryPaymentSchedule(models.Model):
    _name = 'nursery.payment.schedule'
    _description = 'جدول أقساط الحضانة'
    _order = 'registration_id, installment_no'
    _rec_name = 'display_name'

    registration_id = fields.Many2one(
        'nursery.child.registration',
        string='التسجيل',
        required=True,
        ondelete='cascade'
    )

    installment_no = fields.Integer(
        string='رقم القسط',
        required=True
    )

    amount = fields.Float(
        string='المبلغ',
        required=True,
        digits=(10, 2)
    )

    due_date = fields.Date(
        string='تاريخ الاستحقاق',
        required=True
    )

    invoice_id = fields.Many2one(
        'account.move',
        string='الفاتورة',
        readonly=True
    )

    payment_method = fields.Selection([
        ('cash', 'نقدي'),
        ('bank', 'تحويل بنكي'),
        ('cheque', 'شيك'),
        ('mixed', 'مختلط')
    ], string='طريقة الدفع', required=True)

    state = fields.Selection([
        ('draft', 'مسودة'),
        ('invoiced', 'تم إصدار الفاتورة'),
        ('paid', 'مدفوع'),
        ('overdue', 'متأخر')
    ], string='الحالة', default='draft', readonly=True)

    # معلومات الشيك (إذا كانت طريقة الدفع شيك)
    cheque_no = fields.Char(string='رقم الشيك')
    bank_name = fields.Char(string='اسم البنك')
    cheque_date = fields.Date(string='تاريخ الشيك')

    # حقول محسوبة
    display_name = fields.Char(
        string='الاسم',
        compute='_compute_display_name',
        store=True
    )

    child_name = fields.Char(
        string='اسم الطفل',
        related='registration_id.child_full_name',
        store=True
    )

    is_overdue = fields.Boolean(
        string='متأخر',
        compute='_compute_is_overdue',
        store=True
    )

    @api.depends('registration_id', 'installment_no')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"قسط {record.installment_no} - {record.child_name}"

    @api.depends('due_date', 'state')
    def _compute_is_overdue(self):
        today = fields.Date.today()
        for record in self:
            record.is_overdue = record.state not in ['paid'] and record.due_date < today

    def action_create_invoice(self):
        """إنشاء فاتورة للقسط"""
        self.ensure_one()
        if self.invoice_id:
            raise ValidationError('تم إنشاء فاتورة لهذا القسط بالفعل!')

        # الحصول على معلومات التسجيل
        registration = self.registration_id

        # إنشاء/الحصول على partner باسم الطفل
        partner = self._get_partner_id()

        # إنشاء الفاتورة
        invoice_vals = {
            'partner_id': partner,
            'move_type': 'out_invoice',
            'invoice_date': fields.Date.today(),
            'narration': f"""معلومات الطفل:
    الاسم: {registration.child_full_name}
    الصف: {registration.nursery_class_id.class_name if registration.nursery_class_id else 'غير محدد'}
    القسم: {registration.department_id.name}

    معلومات الوالدين:
    الأب: {registration.father_full_name} - {registration.father_mobile}
    الأم: {registration.mother_name} - {registration.mother_mobile}

    معلومات القسط:
    قسط رقم {self.installment_no} من {registration.installments_count}
    تاريخ الاستحقاق: {self.due_date}
    طريقة الدفع: {dict(self._fields['payment_method'].selection).get(self.payment_method, '')}""",
            'invoice_line_ids': [(0, 0, {
                'name': f"قسط {self.installment_no} - {self.child_name} - {registration.department_id.name}",
                'quantity': 1.0,
                'price_unit': self.amount,
            })]
        }

        # إضافة معلومات الشيك إذا كانت طريقة الدفع شيك
        if self.payment_method == 'cheque' and self.cheque_no:
            invoice_vals['narration'] += f"""

    معلومات الشيك:
    رقم الشيك: {self.cheque_no}
    البنك: {self.bank_name}
    تاريخ الشيك: {self.cheque_date}"""

        invoice = self.env['account.move'].create(invoice_vals)
        self.invoice_id = invoice
        self.state = 'invoiced'

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _get_partner_id(self):
        """الحصول على الشريك (الطفل) من التسجيل"""
        registration = self.registration_id

        # اسم الطفل الكامل
        child_name = registration.child_full_name or f"{registration.first_name} {registration.father_name} {registration.family_name}"

        # البحث عن شريك موجود للطفل
        partner = self.env['res.partner'].search([
            ('name', '=', child_name),
            ('ref', '=', registration.identity_number)
        ], limit=1)

        if not partner:
            # البحث باسم الطفل فقط
            partner = self.env['res.partner'].search([
                ('name', '=', child_name),
                ('parent_id', '!=', False)
            ], limit=1)

        if not partner:
            # إنشاء شريك جديد باسم الطفل
            partner = self.env['res.partner'].create({
                'name': child_name,
                'ref': registration.identity_number,
                'is_company': False,
                'email': registration.father_email,
                'mobile': registration.father_mobile,
                'phone': registration.father_phone,
                'street': registration.home_address,
                'customer_rank': 1,
                'comment': f"""معلومات الوالدين:
    الأب: {registration.father_full_name}
    هاتف الأب: {registration.father_mobile}
    بريد الأب: {registration.father_email or 'غير محدد'}

    الأم: {registration.mother_name}
    هاتف الأم: {registration.mother_mobile}
    بريد الأم: {registration.mother_email or 'غير محدد'}"""
            })

            _logger.info(f"Created partner for child: {child_name}")

        return partner.id

    @api.constrains('payment_method', 'cheque_no', 'bank_name', 'cheque_date')
    def _check_cheque_details(self):
        for record in self:
            if record.payment_method == 'cheque':
                # التحقق فقط إذا كان القسط في حالة invoiced أو paid
                if record.state in ['invoiced', 'paid']:
                    if not all([record.cheque_no, record.bank_name, record.cheque_date]):
                        raise ValidationError('يجب إدخال جميع بيانات الشيك!')

    # Cron job لتحديث حالة الأقساط المتأخرة
    @api.model
    def _update_overdue_installments(self):
        today = fields.Date.today()
        overdue_installments = self.search([
            ('state', 'in', ['draft', 'invoiced']),
            ('due_date', '<', today)
        ])
        overdue_installments.write({'state': 'overdue'})

    def action_edit_cheque(self):
        """فتح نافذة لتعديل بيانات الشيك"""
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': f'بيانات شيك القسط {self.installment_no}',
            'res_model': 'nursery.payment.schedule',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'form_view_initial_mode': 'edit',
            },
            'views': [(self.env.ref('charity_clubs.view_nursery_payment_schedule_cheque_form').id, 'form')],
        }