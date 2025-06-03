# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, timedelta
import re


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

    new_parent_country_code = fields.Selection([
        ('+966', 'السعودية (+966)'),
        ('+971', 'الإمارات (+971)'),
        ('+965', 'الكويت (+965)'),
        ('+968', 'عمان (+968)'),
        ('+974', 'قطر (+974)'),
        ('+973', 'البحرين (+973)'),
        ('+20', 'مصر (+20)'),
        ('+962', 'الأردن (+962)'),
    ], string='كود الدولة', default='+966')

    new_parent_mobile = fields.Char(
        string='رقم الموبايل',
        help='رقم الموبايل بدون كود الدولة'
    )

    new_parent_full_mobile = fields.Char(
        string='رقم الموبايل الكامل',
        compute='_compute_full_mobile',
        store=True
    )

    new_parent_email = fields.Char(string='البريد الإلكتروني')
    new_parent_address = fields.Text(string='العنوان')

    # حقل للتحقق من الموبايل
    is_mobile_verified = fields.Boolean(
        string='تم التحقق من الموبايل',
        default=False,
        help='يتم تعيينه بعد التحقق من رقم الموبايل'
    )

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
        'source_request_id',
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

    @api.depends('new_parent_country_code', 'new_parent_mobile')
    def _compute_full_mobile(self):
        for record in self:
            if record.new_parent_country_code and record.new_parent_mobile:
                # إزالة الصفر الأول إذا موجود
                mobile = record.new_parent_mobile
                if mobile.startswith('0'):
                    mobile = mobile[1:]
                record.new_parent_full_mobile = record.new_parent_country_code + mobile
            else:
                record.new_parent_full_mobile = False

    @api.onchange('parent_exists')
    def _onchange_parent_exists(self):
        if not self.parent_exists:
            self.parent_id = False
        else:
            self.new_parent_name = False
            self.new_parent_country_code = '+966'  # إعادة تعيين للقيمة الافتراضية
            self.new_parent_mobile = False
            self.new_parent_email = False
            self.new_parent_address = False

    @api.onchange('parent_id')
    def _onchange_parent_id(self):
        if self.parent_id:
            # جلب اللاعبين التابعين لولي الأمر
            for line in self.line_ids:
                if not line.player_id:
                    line.existing_players_domain = [('parent_id', '=', self.parent_id.id)]

    @api.constrains('new_parent_mobile', 'new_parent_country_code')
    def _check_parent_mobile(self):
        for record in self:
            if not record.parent_exists and record.new_parent_mobile:
                clean_mobile = re.sub(r'[^0-9]', '', record.new_parent_mobile)

                # إزالة الصفر الأول إذا موجود
                if clean_mobile.startswith('0'):
                    clean_mobile = clean_mobile[1:]

                # التحقق حسب كود الدولة
                if record.new_parent_country_code == '+966':
                    if not (len(clean_mobile) == 9 and clean_mobile.startswith('5')):
                        raise ValidationError(_('رقم الموبايل السعودي يجب أن يكون 9 أرقام ويبدأ بـ 5'))

                elif record.new_parent_country_code == '+971':
                    if not (len(clean_mobile) == 9 and clean_mobile[:2] in ['50', '52', '54', '55', '56', '58']):
                        raise ValidationError(_('رقم الموبايل الإماراتي غير صحيح'))

                elif record.new_parent_country_code == '+20':
                    if not (len(clean_mobile) == 10 and clean_mobile[:2] in ['10', '11', '12', '15']):
                        raise ValidationError(_('رقم الموبايل المصري يجب أن يكون 10 أرقام'))

                # التحقق من عدم التكرار
                full_mobile = record.new_parent_full_mobile
                existing_parent = self.env['club.parent'].search([
                    ('full_mobile', '=', full_mobile),
                    ('active', 'in', [True, False])
                ], limit=1)

                if existing_parent:
                    raise ValidationError(_(
                        'رقم الموبايل موجود مسبقاً لولي الأمر: %s\n'
                        'يرجى اختيار "ولي أمر مسجل" واختياره من القائمة.'
                    ) % existing_parent.name)

    def _validate_mobile(self, mobile):
        """التحقق من صحة رقم الموبايل السعودي"""
        if not mobile:
            return False

        # إزالة المسافات والرموز
        mobile = re.sub(r'[^0-9]', '', mobile)

        # التحقق من الطول والبداية
        if len(mobile) == 10 and mobile.startswith('05'):
            return True
        elif len(mobile) == 12 and mobile.startswith('9665'):
            return True
        elif len(mobile) == 13 and mobile.startswith('+9665'):
            return True

        return False

    @api.model
    def check_mobile_exists(self, country_code, mobile):
        """دالة للتحقق من وجود رقم الموبايل (تستخدم من Ajax)"""
        if not mobile or not country_code:
            return {'exists': False}

        # تنظيف الرقم
        clean_mobile = re.sub(r'[^0-9]', '', mobile)
        if clean_mobile.startswith('0'):
            clean_mobile = clean_mobile[1:]

        # البحث بالرقم الكامل
        full_mobile = country_code + clean_mobile
        parent = self.env['club.parent'].search([
            ('full_mobile', '=', full_mobile),
            ('active', '=', True)
        ], limit=1)

        if parent:
            return {
                'exists': True,
                'parent_id': parent.id,
                'parent_name': parent.name,
                'parent_email': parent.email,
                'parent_address': parent.address,
                'children': [{
                    'id': child.id,
                    'name': child.name,
                    'sports': ', '.join(child.sport_ids.mapped('name'))
                } for child in parent.player_ids]
            }

        return {'exists': False}

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
                if not all([record.new_parent_name, record.new_parent_mobile]):
                    raise UserError(_('يجب إكمال اسم ولي الأمر ورقم الموبايل.'))

            for line in record.line_ids:
                if not line.player_exists:
                    if not all([line.new_player_name, line.new_player_birth_date,
                                line.new_player_gender]):
                        raise UserError(_('يجب إكمال جميع بيانات اللاعبين الجدد.'))

            record.state = 'approved'
            record.action_execute_request()

    def action_reject(self):
        for record in self:
            if record.state != 'review':
                raise UserError(_('يمكن رفض الطلبات قيد المراجعة فقط.'))

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
            # تنظيف رقم الموبايل
            clean_mobile = re.sub(r'[^0-9]', '', self.new_parent_mobile)
            if clean_mobile.startswith('0'):
                clean_mobile = clean_mobile[1:]

            parent = self.env['club.parent'].create({
                'name': self.new_parent_name,
                'country_code': self.new_parent_country_code,
                'mobile': clean_mobile,
                'email': self.new_parent_email,
                'address': self.new_parent_address,
            })
            self.parent_id = parent

        # إنشاء اللاعبين والاشتراكات
        for line in self.line_ids:
            # إنشاء اللاعب إذا لم يكن موجوداً
            if not line.player_exists:
                player_vals = {
                    'name': line.new_player_name,
                    'parent_id': self.parent_id.id,
                    'birth_date': line.new_player_birth_date,
                    'gender': line.new_player_gender,
                    'medical_conditions': line.new_player_medical_conditions,
                }

                # إضافة الجنسية إذا كانت موجودة
                if line.new_player_nationality_id:
                    player_vals['nationality_id'] = line.new_player_nationality_id.id

                # إضافة رقم الهوية إذا كان موجوداً
                if line.new_player_id_number:
                    player_vals['id_number'] = line.new_player_id_number
                else:
                    # إنشاء رقم مؤقت إذا كان مطلوباً ولم يتم إدخاله
                    player_vals['id_number'] = 'TEMP-' + str(fields.Datetime.now().timestamp()).replace('.', '')[:10]

                player = self.env['club.player'].create(player_vals)
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
            'domain': [('source_request_id', '=', self.id)],
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

    new_player_nationality_id = fields.Many2one(
        'res.country',
        string='الجنسية',
        help='جنسية اللاعب الجديد'
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

    new_player_nationality_id = fields.Many2one(
        'res.country',
        string='جنسية اللاعب'
    )

    new_player_id_number = fields.Char(
        string='رقم الهوية/الجواز'
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