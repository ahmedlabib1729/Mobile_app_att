# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # معلومات إضافية للأعضاء
    is_club_member = fields.Boolean(
        string='عضو نادي',
        compute='_compute_is_club_member',
        store=True
    )

    birthdate_date = fields.Date(
        string='تاريخ الميلاد'
    )

    age = fields.Integer(
        string='العمر',
        compute='_compute_age',
        store=True
    )

    gender = fields.Selection([
        ('male', 'ذكر'),
        ('female', 'أنثى')
    ], string='الجنس')

    blood_type = fields.Selection([
        ('a+', 'A+'),
        ('a-', 'A-'),
        ('b+', 'B+'),
        ('b-', 'B-'),
        ('ab+', 'AB+'),
        ('ab-', 'AB-'),
        ('o+', 'O+'),
        ('o-', 'O-')
    ], string='فصيلة الدم')

    emergency_contact = fields.Char(
        string='رقم الطوارئ'
    )

    emergency_contact_name = fields.Char(
        string='اسم جهة اتصال الطوارئ'
    )

    medical_conditions = fields.Text(
        string='الحالات الطبية',
        help="أي حالات طبية يجب معرفتها"
    )

    # العضويات والأنشطة
    membership_ids = fields.One2many(
        'club.membership',
        'partner_id',
        string='العضويات'
    )

    active_membership_id = fields.Many2one(
        'club.membership',
        string='العضوية النشطة',
        compute='_compute_active_membership',
        store=True
    )

    activity_ids = fields.One2many(
        'club.member.activity',
        'partner_id',
        string='الأنشطة المشترك بها'
    )

    active_activity_ids = fields.One2many(
        'club.member.activity',
        'partner_id',
        string='الأنشطة النشطة',
        domain=[('state', '=', 'active')]
    )

    # الإحصائيات
    total_activities = fields.Integer(
        string='عدد الأنشطة',
        compute='_compute_activity_stats',
        store=True
    )

    active_activities = fields.Integer(
        string='الأنشطة النشطة',
        compute='_compute_activity_stats',
        store=True
    )

    # حقل مؤقت لحل مشكلة قاعدة البيانات
    activity_type_icon = fields.Char(
        string='Activity Type Icon',
        compute='_compute_activity_type_icon',
        store=False
    )

    @api.depends()
    def _compute_activity_type_icon(self):
        for partner in self:
            partner.activity_type_icon = ''

    @api.depends('membership_ids.state')
    def _compute_is_club_member(self):
        for partner in self:
            partner.is_club_member = bool(
                partner.membership_ids.filtered(lambda m: m.state == 'active')
            )

    @api.depends('birthdate_date')
    def _compute_age(self):
        for partner in self:
            if partner.birthdate_date:
                today = datetime.now().date()
                partner.age = (today - partner.birthdate_date).days // 365
            else:
                partner.age = 0

    @api.depends('membership_ids.state')
    def _compute_active_membership(self):
        for partner in self:
            active_membership = partner.membership_ids.filtered(
                lambda m: m.state == 'active'
            )
            partner.active_membership_id = active_membership[0] if active_membership else False

    @api.depends('activity_ids.state')
    def _compute_activity_stats(self):
        for partner in self:
            partner.total_activities = len(partner.activity_ids)
            partner.active_activities = len(
                partner.activity_ids.filtered(lambda a: a.state == 'active')
            )