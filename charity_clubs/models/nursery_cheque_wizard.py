# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


# nursery_cheque_wizard.py - الكود الكامل والصحيح

class NurseryChequeWizard(models.TransientModel):
    _name = 'nursery.cheque.wizard'
    _description = 'معالج إدخال بيانات الشيكات'

    registration_id = fields.Many2one(
        'nursery.child.registration',
        string='التسجيل',
        required=True,
        readonly=True
    )

    child_name = fields.Char(
        string='اسم الطفل',
        related='registration_id.child_full_name',
        readonly=True
    )

    total_amount = fields.Float(
        string='المبلغ الإجمالي',
        related='registration_id.registration_price',
        readonly=True
    )

    installments_count = fields.Integer(
        string='عدد الأقساط',
        related='registration_id.installments_count',
        readonly=True
    )

    cheque_line_ids = fields.One2many(
        'nursery.cheque.wizard.line',
        'wizard_id',
        string='بيانات الشيكات'
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        registration_id = self.env.context.get('default_registration_id') or self.env.context.get('active_id')

        if registration_id:
            try:
                registration = self.env['nursery.child.registration'].browse(registration_id)

                if registration.exists():
                    res['registration_id'] = registration_id

                    # التأكد من وجود السعر النهائي
                    if not registration.final_price or registration.final_price <= 0:
                        registration._compute_final_price()

                    total_amount = float(registration.final_price) if registration.final_price else 0

                    if total_amount <= 0:
                        raise ValidationError('لا يوجد سعر نهائي محدد للتسجيل.')

                    # تحديد عدد الشيكات بناءً على نوع الدفع
                    if registration.payment_type == 'full':
                        # دفعة واحدة = شيك واحد فقط
                        cheque_lines = [(0, 0, {
                            'installment_no': 1,
                            'amount': total_amount,
                            'cheque_date': registration.join_date or fields.Date.today(),
                            'cheque_no': '',
                            'bank_name': '',
                        })]
                    else:
                        # أقساط متعددة
                        installments_count = int(registration.installments_count)
                        installment_amount = round(total_amount / installments_count, 2)

                        cheque_lines = []
                        base_date = registration.join_date or fields.Date.today()

                        for i in range(installments_count):
                            due_date = base_date + relativedelta(months=i)
                            cheque_lines.append((0, 0, {
                                'installment_no': i + 1,
                                'amount': installment_amount,
                                'cheque_date': due_date,
                                'cheque_no': '',
                                'bank_name': '',
                            }))

                    res['cheque_line_ids'] = cheque_lines
                    _logger.info(f"Created {len(cheque_lines)} cheque line(s)")

            except Exception as e:
                _logger.error(f"Error in default_get: {str(e)}")
                raise ValidationError(f'خطأ في تحضير بيانات الشيكات: {str(e)}')

        return res

    def action_confirm(self):
        """تأكيد بيانات الشيكات والمتابعة مع الاعتماد"""
        self.ensure_one()

        # قراءة البيانات مباشرة من السطور المحفوظة
        lines_data = []
        for idx, line in enumerate(self.cheque_line_ids, 1):
            # التحقق من البيانات
            if not line.cheque_no or line.cheque_no.strip() == '':
                raise ValidationError(f'يجب إدخال رقم الشيك للقسط رقم {idx}!')
            if not line.bank_name or line.bank_name.strip() == '':
                raise ValidationError(f'يجب إدخال اسم البنك للقسط رقم {idx}!')
            if not line.cheque_date:
                raise ValidationError(f'يجب إدخال تاريخ الشيك للقسط رقم {idx}!')
            if line.amount <= 0:
                raise ValidationError(f'مبلغ القسط رقم {idx} غير صحيح!')

            lines_data.append({
                'installment_no': idx,  # استخدم الـ index بدلاً من line.installment_no
                'cheque_no': line.cheque_no.strip(),
                'bank_name': line.bank_name.strip(),
                'cheque_date': line.cheque_date,
                'cheque_amount': line.amount,
            })
            _logger.info(f"Cheque data for installment {idx}: amount={line.amount}, cheque_no={line.cheque_no}")

        # التحقق من عدم تكرار أرقام الشيكات
        cheque_numbers = [d['cheque_no'] for d in lines_data]
        if len(cheque_numbers) != len(set(cheque_numbers)):
            raise ValidationError('لا يمكن استخدام نفس رقم الشيك أكثر من مرة!')

        # تمرير البيانات للتسجيل واعتماده
        self.registration_id.with_context(cheque_data=lines_data).action_approve()

        return {'type': 'ir.actions.act_window_close'}

    @api.onchange('registration_id')
    def _onchange_registration_id(self):
        """ملء بيانات الشيكات عند تغيير التسجيل"""
        if self.registration_id and self.registration_id.installments_count > 0:
            # مسح السطور القديمة
            self.cheque_line_ids = [(5, 0, 0)]

            # حساب قيمة القسط
            total_amount = self.registration_id.registration_price
            installments_count = self.registration_id.installments_count
            installment_amount = total_amount / installments_count if installments_count > 0 else 0

            _logger.info(f"OnChange - Total: {total_amount}, Count: {installments_count}, Per: {installment_amount}")

            # إنشاء سطور جديدة
            lines = []
            base_date = self.registration_id.join_date or fields.Date.today()

            for i in range(installments_count):
                due_date = base_date + relativedelta(months=i)
                lines.append((0, 0, {
                    'installment_no': i + 1,
                    'amount': installment_amount,
                    'cheque_date': due_date,
                    'cheque_no': '',
                    'bank_name': '',
                }))

            self.cheque_line_ids = lines


class NurseryChequeWizardLine(models.TransientModel):
    _name = 'nursery.cheque.wizard.line'
    _description = 'سطر بيانات الشيك'
    _order = 'id'  # استخدم id بدلاً من installment_no

    wizard_id = fields.Many2one(
        'nursery.cheque.wizard',
        string='المعالج',
        required=True,
        ondelete='cascade'
    )

    installment_no = fields.Integer(
        string='رقم القسط'
    )

    amount = fields.Float(
        string='المبلغ',
        digits=(10, 2)
    )

    cheque_no = fields.Char(
        string='رقم الشيك',
        required=False
    )

    bank_name = fields.Char(
        string='اسم البنك',
        required=False
    )

    cheque_date = fields.Date(
        string='تاريخ الشيك',
        required=False
    )