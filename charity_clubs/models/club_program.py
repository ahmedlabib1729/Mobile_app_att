# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, time


class ClubProgram(models.Model):
    _name = 'club.program'
    _description = 'برنامج النادي'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'
    _order = 'club_id, sequence, name'

    name = fields.Char(
        string='اسم البرنامج',
        required=True,
        tracking=True
    )

    display_name = fields.Char(
        string='الاسم الكامل',
        compute='_compute_display_name',
        store=True
    )

    club_id = fields.Many2one(
        'charity.club',
        string='النادي',
        required=True,
        ondelete='cascade',
        tracking=True
    )

    description = fields.Text(
        string='وصف البرنامج'
    )

    vision = fields.Text(
        string='الرؤية والأهداف',
        required=True,
        help='رؤية البرنامج وأهدافه التعليمية والتربوية'
    )

    # معلومات الفئة المستهدفة
    age_from = fields.Integer(
        string='العمر من',
        required=True,
        default=4
    )

    age_to = fields.Integer(
        string='العمر إلى',
        required=True,
        default=12
    )

    gender = fields.Selection([
        ('both', 'الجميع'),
        ('male', 'ذكور فقط'),
        ('female', 'إناث فقط')
    ], string='الجنس المستهدف', default='both', required=True)

    # الجدول الزمني
    schedule_day = fields.Selection([
        ('0', 'الإثنين'),
        ('1', 'الثلاثاء'),
        ('2', 'الأربعاء'),
        ('3', 'الخميس'),
        ('4', 'الجمعة'),
        ('5', 'السبت'),
        ('6', 'الأحد')
    ], string='يوم البرنامج', required=True)

    time_from = fields.Float(
        string='من الساعة',
        required=True,
        help='مثال: 10.5 تعني 10:30'
    )

    time_to = fields.Float(
        string='إلى الساعة',
        required=True,
        help='مثال: 12.5 تعني 12:30'
    )

    schedule_display = fields.Char(
        string='الجدول',
        compute='_compute_schedule_display',
        store=True
    )

    # الأسعار
    term1_price = fields.Float(
        string='سعر الترم الأول',
        required=True,
        digits='Product Price'
    )

    term2_price = fields.Float(
        string='سعر الترم الثاني',
        required=True,
        digits='Product Price'
    )

    term3_price = fields.Float(
        string='سعر الترم الثالث',
        required=True,
        digits='Product Price'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='العملة',
        default=lambda self: self.env.company.currency_id
    )

    total_year_price = fields.Monetary(
        string='إجمالي السنة',
        compute='_compute_total_year_price',
        currency_field='currency_id',
        store=True
    )

    # السعة والتسجيل
    max_capacity = fields.Integer(
        string='السعة القصوى',
        required=True,
        default=30
    )

    registration_ids = fields.One2many(
        'program.registration',
        'program_id',
        string='التسجيلات'
    )

    registration_count = fields.Integer(
        string='عدد المسجلين',
        compute='_compute_registration_stats',
        store=True
    )

    confirmed_count = fields.Integer(
        string='المؤكدين',
        compute='_compute_registration_stats',
        store=True
    )

    available_seats = fields.Integer(
        string='المقاعد المتاحة',
        compute='_compute_registration_stats',
        store=True
    )

    is_full = fields.Boolean(
        string='ممتلئ',
        compute='_compute_registration_stats',
        store=True
    )

    # معلومات إضافية
    instructor_id = fields.Many2one(
        'res.partner',
        string='المدرب',
        domain=[('is_company', '=', False)]
    )

    start_date = fields.Date(
        string='تاريخ البداية',
        required=True
    )

    end_date = fields.Date(
        string='تاريخ النهاية',
        required=True
    )

    active = fields.Boolean(
        string='نشط',
        default=True,
        tracking=True
    )

    sequence = fields.Integer(
        string='الترتيب',
        default=10
    )

    state = fields.Selection([
        ('draft', 'مسودة'),
        ('open', 'التسجيل مفتوح'),
        ('ongoing', 'جاري'),
        ('done', 'منتهي'),
        ('cancelled', 'ملغي')
    ], string='الحالة', default='draft', tracking=True)

    image = fields.Image(
        string='صورة البرنامج',
        max_width=1024,
        max_height=1024
    )

    color = fields.Integer(string='اللون')

    @api.depends('term1_price', 'term2_price', 'term3_price')
    def _compute_total_year_price(self):
        for program in self:
            program.total_year_price = program.term1_price + program.term2_price + program.term3_price

    @api.depends('name', 'club_id.name')
    def _compute_display_name(self):
        for program in self:
            program.display_name = f"{program.club_id.name} - {program.name}"

    @api.depends('schedule_day', 'time_from', 'time_to')
    def _compute_schedule_display(self):
        days = {
            '0': 'الإثنين',
            '1': 'الثلاثاء',
            '2': 'الأربعاء',
            '3': 'الخميس',
            '4': 'الجمعة',
            '5': 'السبت',
            '6': 'الأحد'
        }
        for program in self:
            if program.schedule_day and program.time_from and program.time_to:
                day = days.get(program.schedule_day, '')
                time_from = f"{int(program.time_from)}:{int((program.time_from % 1) * 60):02d}"
                time_to = f"{int(program.time_to)}:{int((program.time_to % 1) * 60):02d}"
                program.schedule_display = f"{day} {time_from} - {time_to}"
            else:
                program.schedule_display = ''

    @api.depends('registration_ids', 'registration_ids.state', 'max_capacity')
    def _compute_registration_stats(self):
        for program in self:
            registrations = program.registration_ids
            program.registration_count = len(registrations)
            program.confirmed_count = len(registrations.filtered(
                lambda r: r.state == 'confirmed'
            ))
            program.available_seats = max(0, program.max_capacity - program.confirmed_count)
            program.is_full = program.available_seats == 0

    @api.constrains('age_from', 'age_to')
    def _check_age_range(self):
        for program in self:
            if program.age_from < 0 or program.age_to < 0:
                raise ValidationError('العمر يجب أن يكون موجب!')
            if program.age_from > program.age_to:
                raise ValidationError('العمر "من" يجب أن يكون أصغر من أو يساوي العمر "إلى"!')
            if program.age_from < 3:
                raise ValidationError('الحد الأدنى للعمر هو 3 سنوات!')
            if program.age_to > 18:
                raise ValidationError('الحد الأقصى للعمر هو 18 سنة!')

    @api.constrains('time_from', 'time_to')
    def _check_time_range(self):
        for program in self:
            if program.time_from >= program.time_to:
                raise ValidationError('وقت البداية يجب أن يكون قبل وقت النهاية!')
            if program.time_from < 6 or program.time_from > 22:
                raise ValidationError('وقت البداية يجب أن يكون بين 6 صباحاً و 10 مساءً!')
            if program.time_to < 6 or program.time_to > 22:
                raise ValidationError('وقت النهاية يجب أن يكون بين 6 صباحاً و 10 مساءً!')

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for program in self:
            if program.start_date and program.end_date:
                if program.start_date > program.end_date:
                    raise ValidationError('تاريخ البداية يجب أن يكون قبل تاريخ النهاية!')

    @api.constrains('term1_price', 'term2_price', 'term3_price')
    def _check_prices(self):
        for program in self:
            if program.term1_price < 0 or program.term2_price < 0 or program.term3_price < 0:
                raise ValidationError('الأسعار يجب أن تكون موجبة!')

    @api.constrains('max_capacity')
    def _check_capacity(self):
        for program in self:
            if program.max_capacity <= 0:
                raise ValidationError('السعة القصوى يجب أن تكون أكبر من صفر!')
            if program.max_capacity < program.confirmed_count:
                raise ValidationError('السعة القصوى لا يمكن أن تكون أقل من عدد المسجلين المؤكدين!')

    def action_open_registration(self):
        """فتح التسجيل في البرنامج"""
        self.state = 'open'

    def action_start_program(self):
        """بدء البرنامج"""
        self.state = 'ongoing'

    def action_end_program(self):
        """إنهاء البرنامج"""
        self.state = 'done'

    def action_cancel_program(self):
        """إلغاء البرنامج"""
        if self.confirmed_count > 0:
            raise ValidationError('لا يمكن إلغاء البرنامج وبه طلاب مسجلين!')
        self.state = 'cancelled'

    def action_view_registrations(self):
        """عرض التسجيلات"""
        return {
            'name': f'تسجيلات {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'program.registration',
            'view_mode': 'list,form,kanban',
            'domain': [('program_id', '=', self.id)],
            'context': {'default_program_id': self.id}
        }

    @api.model
    def get_available_programs(self, club_id=None):
        """الحصول على البرامج المتاحة للتسجيل"""
        domain = [
            ('state', '=', 'open'),
            ('active', '=', True),
            ('is_full', '=', False)
        ]
        if club_id:
            domain.append(('club_id', '=', club_id))
        return self.search(domain)