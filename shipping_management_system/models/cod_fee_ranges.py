# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CODFeeRange(models.Model):
    """شرائح رسوم COD مع دعم Fixed و Percentage"""
    _name = 'cod.fee.range'
    _description = 'COD Fee Range'
    _order = 'amount_from'

    # ربط مع شركة الشحن أو فئة العميل
    shipping_company_id = fields.Many2one(
        'shipping.company',
        string='Shipping Company',
        ondelete='cascade'
    )

    customer_category_id = fields.Many2one(
        'customer.price.category',
        string='Customer Category',
        ondelete='cascade'
    )

    # النطاق
    amount_from = fields.Float(
        string='From',
        required=True
    )

    amount_to = fields.Float(
        string='To',
        required=True,
        help='Use 0 for unlimited'
    )

    # ===== النوع: Fixed أو Percentage ===== 🆕
    # ⚠️ مهم: required=False في البداية عشان البيانات القديمة
    fee_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount')
    ], string='Fee Type',
        default='percentage',
        required=False,  # ← هنغيره لـ True بعد الـ migration
        help='Choose between percentage of amount or fixed fee'
    )

    # ===== النسب (للـ Percentage) =====
    cash_percentage = fields.Float(
        string='Cash %',
        default=1.0,
        help='Cash percentage (used when fee_type = percentage)'
    )

    visa_percentage = fields.Float(
        string='Visa %',
        default=2.0,
        help='Visa percentage (used when fee_type = percentage)'
    )

    # ===== القيم الثابتة (للـ Fixed) ===== 🆕
    cash_fixed_amount = fields.Float(
        string='Cash Fixed Amount (EGP)',
        default=0.0,
        help='Fixed cash fee (used when fee_type = fixed)'
    )

    visa_fixed_amount = fields.Float(
        string='Visa Fixed Amount (EGP)',
        default=0.0,
        help='Fixed visa fee (used when fee_type = fixed)'
    )

    # ===== 🔧 حل مشكلة البيانات القديمة =====
    def init(self):
        """تحديث البيانات القديمة عند أول تشغيل"""
        # تحديث كل الـ records اللي مالهاش fee_type
        self.env.cr.execute("""
            UPDATE cod_fee_range
            SET fee_type = 'percentage'
            WHERE fee_type IS NULL OR fee_type = ''
        """)

        # تحديث القيم الثابتة للي مالهاش قيم
        self.env.cr.execute("""
            UPDATE cod_fee_range
            SET 
                cash_fixed_amount = COALESCE(cash_fixed_amount, 0.0),
                visa_fixed_amount = COALESCE(visa_fixed_amount, 0.0)
            WHERE cash_fixed_amount IS NULL 
               OR visa_fixed_amount IS NULL
        """)

    @api.model
    def create(self, vals):
        """تأكد من وجود fee_type عند الإنشاء"""
        if 'fee_type' not in vals or not vals.get('fee_type'):
            vals['fee_type'] = 'percentage'
        return super(CODFeeRange, self).create(vals)

    def write(self, vals):
        """تأكد من وجود fee_type عند التعديل"""
        for record in self:
            if not record.fee_type and 'fee_type' not in vals:
                vals['fee_type'] = 'percentage'
        return super(CODFeeRange, self).write(vals)

    @api.constrains('amount_from', 'amount_to')
    def _check_amounts(self):
        for record in self:
            if record.amount_from < 0:
                raise ValidationError(_('From amount cannot be negative!'))
            if record.amount_to > 0 and record.amount_to <= record.amount_from:
                raise ValidationError(_('To amount must be greater than from amount!'))

    @api.constrains('cash_percentage', 'visa_percentage', 'cash_fixed_amount', 'visa_fixed_amount')
    def _check_fees(self):
        """التحقق من صحة الرسوم"""
        for record in self:
            if record.cash_percentage < 0:
                raise ValidationError(_('Cash percentage cannot be negative!'))
            if record.visa_percentage < 0:
                raise ValidationError(_('Visa percentage cannot be negative!'))
            if record.cash_fixed_amount < 0:
                raise ValidationError(_('Cash fixed amount cannot be negative!'))
            if record.visa_fixed_amount < 0:
                raise ValidationError(_('Visa fixed amount cannot be negative!'))

    def name_get(self):
        """عرض اسم مفهوم للـ Range"""
        result = []
        for record in self:
            # ✅ تأكد من وجود fee_type
            fee_type = record.fee_type or 'percentage'

            if record.amount_to > 0:
                range_text = f"{record.amount_from:.0f}-{record.amount_to:.0f} EGP"
            else:
                range_text = f"{record.amount_from:.0f}+ EGP"

            if fee_type == 'fixed':
                fee_text = f"Fixed: {record.cash_fixed_amount:.0f}/{record.visa_fixed_amount:.0f}"
            else:
                fee_text = f"{record.cash_percentage:.1f}%/{record.visa_percentage:.1f}%"

            name = f"{range_text} - {fee_text}"
            result.append((record.id, name))
        return result