# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, timedelta


class SubscriptionRequest(models.Model):
    _name = 'subscription.request'
    _description = 'طلب اشتراك'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'create_date desc'

    name = fields.Char(
        string='رقم الطلب',
        required=True,
        copy=False,
        readonly=True,
        default='جديد'
    )

    request_date = fields.Date(
        string='تاريخ الطلب',
        required=True,
        default=fields.Date.context_today,
        readonly=True,
        tracking=True
    )

    request_type = fields.Selection([
        ('new', 'اشتراك جديد'),
        ('renewal', 'تجديد')
    ], string='نوع الطلب', required=True, default='new', tracking=True)

    # Parent Information
    parent_exists = fields.Boolean(
        string='ولي أمر مسجل',
        default=False
    )

    parent_id = fields.Many2one(
        'club.parent',
        string='ولي الأمر',
        domain=[('active', '=', True)],
        tracking=True
    )

    # New Parent Fields (when parent doesn't exist)
    new_parent_name = fields.Char(string='اسم ولي الأمر')
    new_parent_identification = fields.Char(string='رقم الهوية/الباسبور')
    new_parent_id_type = fields.Selection([
        ('national_id', 'بطاقة وطنية'),
        ('passport', 'جواز سفر'),
        ('residence', 'إقامة')
    ], string='نوع الهوية')
    new_parent_phone = fields.Char(string='رقم الهاتف')
    new_parent_email = fields.Char(string='البريد الإلكتروني')
    new_parent_address = fields.Text(string='العنوان')

    state = fields.Selection([
        ('draft', 'مسودة'),
        ('sent', 'مرسل'),
        ('review', 'قيد المراجعة'),
        ('approved', 'موافق عليه'),
        ('rejected', 'مرفوض'),
        ('cancelled', 'ملغي')
    ], string='الحالة', default='draft', tracking=True)

    rejection_reason = fields.Text(
        string='سبب الرفض',
        readonly=True
    )

    line_ids = fields.One2many(
        'subscription.request.line',
        'request_id',
        string='تفاصيل الطلب'
    )

    total_amount = fields.Monetary(
        string='إجمالي المبلغ',
        compute='_compute_total_amount',
        store=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='العملة',
        related='company_id.currency_id',
        readonly=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        default=lambda self: self.env.company,
        required=True
    )

    created_subscriptions_count = fields.Integer(
        string='الاشتراكات المنشأة',
        compute='_compute_created_subscriptions'
    )

    created_subscription_ids = fields.One2many(
        'player.subscription',
        'source_request_id',  # بدلاً من 'request_id'
        string='الاشتراكات المنشأة'
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'جديد') == 'جديد':
                vals['name'] = self.env['ir.sequence'].next_by_code('subscription.request') or 'جديد'
        return super().create(vals_list)

    @api.depends('line_ids.subtotal')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = sum(line.subtotal for line in record.line_ids)

    @api.depends('created_subscription_ids')
    def _compute_created_subscriptions(self):
        for record in self:
            record.created_subscriptions_count = len(record.created_subscription_ids)

    @api.onchange('parent_exists')
    def _onchange_parent_exists(self):
        if not self.parent_exists:
            self.parent_id = False
        else:
            self.new_parent_name = False
            self.new_parent_identification = False
            self.new_parent_id_type = False
            self.new_parent_phone = False
            self.new_parent_email = False
            self.new_parent_address = False

    @api.onchange('parent_id')
    def _onchange_parent_id(self):
        if self.parent_id:
            # جلب اللاعبين التابعين لولي الأمر
            for line in self.line_ids:
                if not line.player_id:
                    line.existing_players_domain = [('parent_id', '=', self.parent_id.id)]

    @api.constrains('new_parent_identification')
    def _check_parent_identification(self):
        for record in self:
            if not record.parent_exists and record.new_parent_identification:
                # التحقق من عدم تكرار رقم الهوية
                existing_parent = self.env['club.parent'].search([
                    ('identification_number', '=', record.new_parent_identification),
                    ('active', 'in', [True, False])  # البحث حتى في غير النشطين
                ], limit=1)

                if existing_parent:
                    raise ValidationError(_(
                        'رقم الهوية/الباسبور موجود مسبقاً لولي الأمر: %s\n'
                        'يرجى اختيار "ولي أمر مسجل" واختياره من القائمة.'
                    ) % existing_parent.name)

    def action_send(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_('يمكن إرسال الطلبات في حالة المسودة فقط.'))
            if not record.line_ids:
                raise UserError(_('لا يمكن إرسال طلب بدون تفاصيل.'))
            record.state = 'sent'

    def action_review(self):
        for record in self:
            if record.state != 'sent':
                raise UserError(_('يمكن مراجعة الطلبات المرسلة فقط.'))
            record.state = 'review'

    def action_approve(self):
        for record in self:
            if record.state != 'review':
                raise UserError(_('يمكن الموافقة على الطلبات قيد المراجعة فقط.'))

            # التحقق من البيانات المطلوبة
            if not record.parent_exists:
                if not all([record.new_parent_name, record.new_parent_identification,
                            record.new_parent_id_type, record.new_parent_phone]):
                    raise UserError(_('يجب إكمال جميع بيانات ولي الأمر الجديد.'))

            for line in record.line_ids:
                if not line.player_exists:
                    if not all([line.new_player_name, line.new_player_birth_date,
                                line.new_player_gender]):
                        raise UserError(_('يجب إكمال جميع بيانات اللاعبين الجدد.'))

            record.state = 'approved'
            # يمكن استدعاء دالة تنفيذ الطلب هنا
            record.action_execute_request()

    def action_reject(self):
        for record in self:
            if record.state != 'review':
                raise UserError(_('يمكن رفض الطلبات قيد المراجعة فقط.'))

            # فتح wizard لإدخال سبب الرفض
            return {
                'type': 'ir.actions.act_window',
                'name': 'سبب الرفض',
                'res_model': 'subscription.request.reject.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_request_id': record.id}
            }

    def action_cancel(self):
        for record in self:
            if record.state not in ['draft', 'sent']:
                raise UserError(_('يمكن إلغاء الطلبات في حالة المسودة أو المرسلة فقط.'))
            record.state = 'cancelled'

    def action_execute_request(self):
        """تنفيذ الطلب وإنشاء البيانات المطلوبة"""
        self.ensure_one()

        # إنشاء ولي الأمر إذا لم يكن موجوداً
        if not self.parent_exists:
            parent = self.env['club.parent'].create({
                'name': self.new_parent_name,
                'identification_number': self.new_parent_identification,
                'id_type': self.new_parent_id_type,
                'phone': self.new_parent_phone,
                'email': self.new_parent_email,
                'address': self.new_parent_address,
            })
            self.parent_id = parent

        # إنشاء اللاعبين والاشتراكات
        for line in self.line_ids:
            # إنشاء اللاعب إذا لم يكن موجوداً
            if not line.player_exists:
                player = self.env['club.player'].create({
                    'name': line.new_player_name,
                    'parent_id': self.parent_id.id,
                    'birth_date': line.new_player_birth_date,
                    'gender': line.new_player_gender,
                    'medical_conditions': line.new_player_medical_conditions,
                })
                line.player_id = player

            # إنشاء الاشتراك
            subscription = self.env['player.subscription'].create({
                'player_id': line.player_id.id,
                'parent_id': self.parent_id.id,
                'sport_id': line.sport_id.id,
                'subscription_period': line.subscription_period,
                'subscription_fee': line.subtotal,
                'source_request_id': self.id,
                'state': 'draft',
            })

    def action_view_subscriptions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'الاشتراكات المنشأة',
            'view_mode': 'list,form',
            'res_model': 'player.subscription',
            'domain': [('request_id', '=', self.id)],
            'context': {}
        }


class SubscriptionRequestLine(models.Model):
    _name = 'subscription.request.line'
    _description = 'سطر طلب الاشتراك'

    request_id = fields.Many2one(
        'subscription.request',
        string='طلب الاشتراك',
        required=True,
        ondelete='cascade'
    )

    # Player Information
    player_exists = fields.Boolean(
        string='لاعب مسجل',
        default=False
    )

    player_id = fields.Many2one(
        'club.player',
        string='اللاعب'
    )

    # New Player Fields
    new_player_name = fields.Char(string='اسم اللاعب')
    new_player_birth_date = fields.Date(string='تاريخ الميلاد')
    new_player_gender = fields.Selection([
        ('male', 'ذكر'),
        ('female', 'أنثى')
    ], string='الجنس')
    new_player_medical_conditions = fields.Text(string='الحالة الصحية')

    sport_id = fields.Many2one(
        'club.sport',
        string='اللعبة',
        required=True
    )

    subscription_period = fields.Selection([
        ('1', 'شهر'),
        ('3', '3 شهور'),
        ('6', '6 شهور'),
        ('12', 'سنة')
    ], string='مدة الاشتراك', required=True, default='1')

    subtotal = fields.Monetary(
        string='الرسوم',
        compute='_compute_subtotal',
        store=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='request_id.currency_id',
        readonly=True
    )

    note = fields.Text(string='ملاحظات')

    existing_players_domain = fields.Char(
        compute='_compute_existing_players_domain',
        readonly=True
    )

    @api.depends('request_id.parent_id')
    def _compute_existing_players_domain(self):
        for line in self:
            if line.request_id.parent_id:
                line.existing_players_domain = [('parent_id', '=', line.request_id.parent_id.id)]
            else:
                line.existing_players_domain = []

    @api.depends('sport_id', 'subscription_period')
    def _compute_subtotal(self):
        for line in self:
            if line.sport_id and line.subscription_period:
                # حساب الرسوم بناءً على المدة
                monthly_fee = line.sport_id.monthly_fee
                months = int(line.subscription_period)

                # يمكن إضافة خصومات للمدد الطويلة
                if months == 1:
                    line.subtotal = monthly_fee
                elif months == 3:
                    line.subtotal = monthly_fee * 3 * 0.95  # خصم 5%
                elif months == 6:
                    line.subtotal = monthly_fee * 6 * 0.9  # خصم 10%
                elif months == 12:
                    line.subtotal = monthly_fee * 12 * 0.85  # خصم 15%
            else:
                line.subtotal = 0

    @api.onchange('player_exists')
    def _onchange_player_exists(self):
        if not self.player_exists:
            self.player_id = False
        else:
            self.new_player_name = False
            self.new_player_birth_date = False
            self.new_player_gender = False
            self.new_player_medical_conditions = False

    @api.onchange('player_id')
    def _onchange_player_id(self):
        if self.player_id:
            # التحقق من الاشتراكات النشطة
            active_subscriptions = self.env['player.subscription'].search([
                ('player_id', '=', self.player_id.id),
                ('sport_id', '=', self.sport_id.id),
                ('state', '=', 'active')
            ])

            if active_subscriptions:
                return {
                    'warning': {
                        'title': 'تنبيه',
                        'message': 'يوجد اشتراك نشط لهذا اللاعب في نفس اللعبة!'
                    }
                }