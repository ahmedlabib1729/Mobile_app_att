# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta


class MemberActivity(models.Model):
    _name = 'club.member.activity'
    _description = 'اشتراكات الأعضاء في الأنشطة'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'
    _order = 'create_date desc'

    # الحقول المحسوبة للاسم
    display_name = fields.Char(
        string='الاسم',
        compute='_compute_display_name',
        store=True
    )

    @api.depends('partner_id', 'activity_id')
    def _compute_display_name(self):
        for record in self:
            if record.partner_id and record.activity_id:
                record.display_name = f"{record.partner_id.name} - {record.activity_id.name}"
            else:
                record.display_name = "اشتراك جديد"

    # المعلومات الأساسية
    partner_id = fields.Many2one(
        'res.partner',
        string='العضو',
        required=True,
        tracking=True,
        domain=[('is_company', '=', False)]
    )

    membership_id = fields.Many2one(
        'club.membership',
        string='العضوية',
        required=True,
        domain="[('partner_id', '=', partner_id), ('state', '=', 'active')]"
    )

    activity_id = fields.Many2one(
        'club.sport.activity',
        string='النشاط الرياضي',
        required=True,
        tracking=True
    )

    # المستوى
    level = fields.Selection([
        ('beginner', 'مبتدئ'),
        ('intermediate', 'متوسط'),
        ('advanced', 'متقدم'),
        ('professional', 'محترف')
    ], string='المستوى', default='beginner', tracking=True)

    # التواريخ
    start_date = fields.Date(
        string='تاريخ البداية',
        required=True,
        default=fields.Date.today,
        tracking=True
    )

    end_date = fields.Date(
        string='تاريخ الانتهاء',
        help="اتركه فارغاً للاشتراك المفتوح"
    )

    # الحالة
    state = fields.Selection([
        ('draft', 'مسودة'),
        ('active', 'نشط'),
        ('suspended', 'معلق'),
        ('expired', 'منتهي'),
        ('cancelled', 'ملغي')
    ], string='الحالة', default='draft', tracking=True)

    # المدرب المسؤول
    instructor_id = fields.Many2one(
        'res.partner',
        string='المدرب',
        domain="[('is_company', '=', False)]"
    )

    # نوع الاشتراك
    subscription_type = fields.Selection([
        ('monthly', 'شهري'),
        ('quarterly', 'ربع سنوي'),
        ('semi_annual', 'نصف سنوي'),
        ('annual', 'سنوي'),
        ('per_session', 'بالحصة')
    ], string='نوع الاشتراك', default='monthly', required=True)

    # المالية
    registration_fee = fields.Float(
        string='رسوم التسجيل',
        related='activity_id.registration_fee',
        readonly=True
    )

    subscription_fee = fields.Float(
        string='رسوم الاشتراك',
        compute='_compute_subscription_fee',
        store=True
    )

    @api.depends('activity_id', 'subscription_type')
    def _compute_subscription_fee(self):
        for record in self:
            if record.activity_id and record.subscription_type:
                monthly_fee = record.activity_id.monthly_fee
                if record.subscription_type == 'monthly':
                    record.subscription_fee = monthly_fee
                elif record.subscription_type == 'quarterly':
                    record.subscription_fee = monthly_fee * 3 * 0.9  # خصم 10%
                elif record.subscription_type == 'semi_annual':
                    record.subscription_fee = monthly_fee * 6 * 0.85  # خصم 15%
                elif record.subscription_type == 'annual':
                    record.subscription_fee = monthly_fee * 12 * 0.8  # خصم 20%
                elif record.subscription_type == 'per_session':
                    record.subscription_fee = record.activity_id.session_fee
            else:
                record.subscription_fee = 0.0

    total_paid = fields.Float(
        string='المبلغ المدفوع',
        default=0.0,
        tracking=True
    )

    payment_state = fields.Selection([
        ('not_paid', 'غير مدفوع'),
        ('partial', 'مدفوع جزئياً'),
        ('paid', 'مدفوع')
    ], string='حالة الدفع', compute='_compute_payment_state', store=True)

    @api.depends('registration_fee', 'subscription_fee', 'total_paid')
    def _compute_payment_state(self):
        for record in self:
            total_due = record.registration_fee + record.subscription_fee
            if record.total_paid >= total_due:
                record.payment_state = 'paid'
            elif record.total_paid > 0:
                record.payment_state = 'partial'
            else:
                record.payment_state = 'not_paid'

    # الحضور والأداء
    attendance_rate = fields.Float(
        string='معدل الحضور %',
        default=0.0,
        help="يتم حسابه تلقائياً من سجل الحضور"
    )

    performance_score = fields.Float(
        string='تقييم الأداء',
        default=0.0,
        help="من 0 إلى 100"
    )

    # الملاحظات
    notes = fields.Text(
        string='ملاحظات'
    )

    medical_notes = fields.Text(
        string='ملاحظات طبية',
        help="أي ملاحظات طبية خاصة"
    )

    # قيود
    @api.constrains('partner_id', 'activity_id', 'state')
    def _check_duplicate_activity(self):
        for record in self:
            if record.state in ['active', 'suspended']:
                duplicate = self.search([
                    ('partner_id', '=', record.partner_id.id),
                    ('activity_id', '=', record.activity_id.id),
                    ('state', 'in', ['active', 'suspended']),
                    ('id', '!=', record.id)
                ], limit=1)
                if duplicate:
                    raise ValidationError(
                        f"العضو {record.partner_id.name} مشترك بالفعل في {record.activity_id.name}!"
                    )

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.end_date and record.start_date > record.end_date:
                raise ValidationError("تاريخ البداية يجب أن يكون قبل تاريخ الانتهاء!")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # التحقق من عمر العضو
            if vals.get('partner_id') and vals.get('activity_id'):
                partner = self.env['res.partner'].browse(vals['partner_id'])
                activity = self.env['club.sport.activity'].browse(vals['activity_id'])

                if partner.birthdate_date:
                    age = (datetime.now().date() - partner.birthdate_date).days // 365
                    if age < activity.min_age:
                        raise UserError(f"عمر العضو أقل من الحد الأدنى المطلوب ({activity.min_age} سنة)")
                    if activity.max_age > 0 and age > activity.max_age:
                        raise UserError(f"عمر العضو أكبر من الحد الأقصى المسموح ({activity.max_age} سنة)")

                # التحقق من الجنس
                if activity.gender != 'all':
                    if activity.gender == 'male' and partner.gender != 'male':
                        raise UserError("هذا النشاط للذكور فقط!")
                    if activity.gender == 'female' and partner.gender != 'female':
                        raise UserError("هذا النشاط للإناث فقط!")

        return super(MemberActivity, self).create(vals_list)

    def action_activate(self):
        """تفعيل الاشتراك"""
        for record in self:
            if record.payment_state != 'paid':
                raise UserError("لا يمكن تفعيل الاشتراك قبل اكتمال الدفع!")

            # التحقق من وجود عضوية نشطة
            if not record.membership_id or record.membership_id.state != 'active':
                raise UserError("يجب أن يكون لدى العضو عضوية نشطة!")

            record.state = 'active'

    def action_suspend(self):
        """تعليق الاشتراك"""
        for record in self:
            if record.state != 'active':
                raise UserError("يمكن تعليق الاشتراكات النشطة فقط!")
            record.state = 'suspended'

    def action_reactivate(self):
        """إعادة تفعيل الاشتراك"""
        for record in self:
            if record.state != 'suspended':
                raise UserError("يمكن إعادة تفعيل الاشتراكات المعلقة فقط!")
            record.state = 'active'

    def action_cancel(self):
        """إلغاء الاشتراك"""
        for record in self:
            if record.state == 'cancelled':
                raise UserError("الاشتراك ملغي بالفعل!")
            record.state = 'cancelled'

    @api.model
    def _cron_check_expiry(self):
        """التحقق من انتهاء الاشتراكات"""
        today = fields.Date.today()
        expired_subscriptions = self.search([
            ('state', '=', 'active'),
            ('end_date', '!=', False),
            ('end_date', '<', today)
        ])
        expired_subscriptions.write({'state': 'expired'})