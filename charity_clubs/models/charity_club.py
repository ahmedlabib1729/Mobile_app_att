# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CharityClub(models.Model):
    _name = 'charity.club'
    _description = 'نادي الجمعية الخيرية'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    name = fields.Char(
        string='اسم النادي',
        required=True,
        tracking=True
    )

    description = fields.Text(
        string='وصف النادي',
        help='وصف مختصر عن النادي وأهدافه'
    )

    vision = fields.Text(
        string='الرؤية',
        help='رؤية النادي وأهدافه طويلة المدى'
    )

    image = fields.Image(
        string='صورة النادي',
        max_width=1024,
        max_height=1024
    )

    street = fields.Char(string='الشارع')
    street2 = fields.Char(string='الشارع 2')
    city = fields.Char(string='المدينة')
    state_id = fields.Many2one('res.country.state', string='الإمارة')
    zip = fields.Char(string='الرمز البريدي')
    country_id = fields.Many2one(
        'res.country',
        string='الدولة',
        default=lambda self: self.env.ref('base.ae')  # UAE by default
    )

    phone = fields.Char(string='الهاتف')
    mobile = fields.Char(string='الجوال')
    email = fields.Char(string='البريد الإلكتروني')
    website = fields.Char(string='الموقع الإلكتروني')

    manager_id = fields.Many2one(
        'res.users',
        string='مدير النادي',
        tracking=True
    )

    active = fields.Boolean(
        string='نشط',
        default=True,
        tracking=True
    )

    sequence = fields.Integer(
        string='الترتيب',
        default=10,
        help='يستخدم لترتيب النوادي في العرض'
    )

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        default=lambda self: self.env.company
    )

    # علاقة مع البرامج
    program_ids = fields.One2many(
        'club.program',
        'club_id',
        string='البرامج'
    )

    program_count = fields.Integer(
        string='عدد البرامج',
        compute='_compute_program_count',
        store=True
    )

    active_program_count = fields.Integer(
        string='البرامج النشطة',
        compute='_compute_program_count',
        store=True
    )

    total_registrations = fields.Integer(
        string='إجمالي التسجيلات',
        compute='_compute_registration_stats'
    )

    color = fields.Integer(string='اللون', default=1)

    @api.depends('program_ids', 'program_ids.active', 'program_ids.state')
    def _compute_program_count(self):
        for club in self:
            club.program_count = len(club.program_ids)
            # البرامج النشطة هي التي active=True و state في open أو ongoing
            active_programs = club.program_ids.filtered(
                lambda p: p.active and p.state in ['open', 'ongoing']
            )
            club.active_program_count = len(active_programs)

    @api.depends('program_ids.registration_ids')
    def _compute_registration_stats(self):
        for club in self:
            club.total_registrations = sum(
                program.registration_count for program in club.program_ids
            )

    @api.constrains('email')
    def _check_email(self):
        for record in self:
            if record.email and '@' not in record.email:
                raise ValidationError('البريد الإلكتروني غير صحيح!')

    def action_view_programs(self):
        """فتح قائمة البرامج الخاصة بالنادي"""
        return {
            'name': f'برامج {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'club.program',
            'view_mode': 'list,form,kanban',
            'domain': [('club_id', '=', self.id)],
            'context': {'default_club_id': self.id}
        }

    def action_view_registrations(self):
        """فتح قائمة التسجيلات الخاصة بالنادي"""
        return {
            'name': f'تسجيلات {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'program.registration',
            'view_mode': 'list,form,kanban',
            'domain': [('club_id', '=', self.id)],
            'context': {'search_default_club_id': self.id}
        }

    @api.model
    def create(self, vals):
        """عند إنشاء نادي جديد"""
        club = super().create(vals)
        # يمكن إضافة أي منطق إضافي هنا
        return club

    def unlink(self):
        """التحقق قبل حذف النادي"""
        for club in self:
            if club.program_ids:
                raise ValidationError(
                    f'لا يمكن حذف النادي "{club.name}" لأنه يحتوي على برامج!'
                )
        return super().unlink()