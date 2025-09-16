# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class NurseryChildProfile(models.Model):
    _name = 'nursery.child.profile'
    _description = 'ملف طفل الحضانة'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'full_name'

    # الاسم الكامل
    full_name = fields.Char(
        string='الاسم الكامل',
        compute='_compute_full_name',
        store=True
    )
    registration_count = fields.Integer(
        string='عدد التسجيلات',
        compute='_compute_registration_count'
    )

    image = fields.Binary(string='الصورة', attachment=True)

    # بيانات الطفل
    first_name = fields.Char(string='الاسم الأول', required=True, tracking=True)
    father_name = fields.Char(string='اسم الأب', required=True, tracking=True)
    family_name = fields.Char(string='العائلة', required=True, tracking=True)
    birth_date = fields.Date(string='تاريخ الميلاد', required=True, tracking=True)
    gender = fields.Selection([
        ('male', 'ذكر'),
        ('female', 'أنثى')
    ], string='الجنس', required=True, tracking=True)

    # الوثائق
    passport_number = fields.Char(string='رقم جواز السفر')
    identity_number = fields.Char(string='رقم الهوية', required=True)

    # التسجيلات
    registration_ids = fields.One2many(
        'nursery.child.registration',
        'child_profile_id',
        string='التسجيلات'
    )
    child_order = fields.Integer(string='ترتيب الطفل بين إخوته')
    # أضف هذه الحقول بعد حقل image الموجود:

    # صور هوية الطفل
    child_id_front = fields.Binary(
        string='هوية الطفل - الوجه الأمامي',
        attachment=True,

    )
    child_id_front_filename = fields.Char(string='اسم ملف الوجه الأمامي')

    child_id_back = fields.Binary(
        string='هوية الطفل - الوجه الخلفي',
        attachment=True,

    )
    child_id_back_filename = fields.Char(string='اسم ملف الوجه الخلفي')

    # صور هوية ولي الأمر
    guardian_id_front = fields.Binary(
        string='هوية ولي الأمر - الوجه الأمامي',
        attachment=True,

    )
    guardian_id_front_filename = fields.Char(string='اسم ملف الوجه الأمامي لولي الأمر')

    guardian_id_back = fields.Binary(
        string='هوية ولي الأمر - الوجه الخلفي',
        attachment=True,

    )

    has_paid_registration_fee = fields.Boolean(
        string='دفع رسوم التسجيل',
        default=False,
        readonly=True,
        help='يتم تحديدها تلقائياً عند دفع رسوم التسجيل لأول مرة'
    )

    registration_fee_invoice_id = fields.Many2one(
        'account.move',
        string='فاتورة رسوم التسجيل',
        readonly=True,
        help='الفاتورة المرتبطة برسوم التسجيل'
    )
    guardian_id_back_filename = fields.Char(string='اسم ملف الوجه الخلفي لولي الأمر')

    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.depends('first_name', 'father_name', 'family_name')
    def _compute_full_name(self):
        for record in self:
            names = [record.first_name, record.father_name, record.family_name]
            record.full_name = ' '.join(filter(None, names))

    @api.constrains('identity_number', 'passport_number')
    def _check_unique_documents(self):
        """منع تكرار رقم الهوية أو جواز السفر"""
        for record in self:
            # فحص رقم الهوية
            if record.identity_number:
                duplicate = self.search([
                    ('identity_number', '=', record.identity_number),
                    ('id', '!=', record.id)
                ])
                if duplicate:
                    raise ValidationError(
                        f'رقم الهوية {record.identity_number} مسجل بالفعل للطفل {duplicate.full_name}!')

            # فحص جواز السفر
            if record.passport_number:
                duplicate = self.search([
                    ('passport_number', '=', record.passport_number),
                    ('id', '!=', record.id)
                ])
                if duplicate:
                    raise ValidationError(
                        f'رقم جواز السفر {record.passport_number} مسجل بالفعل للطفل {duplicate.full_name}!')

    @api.depends('registration_ids')
    def _compute_registration_count(self):
        for record in self:
            record.registration_count = len(record.registration_ids)

    def action_view_registrations(self):
        """فتح نافذة التسجيلات الخاصة بالطفل"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'تسجيلات {self.full_name}',
            'res_model': 'nursery.child.registration',
            'view_mode': 'list,form',
            'domain': [('child_profile_id', '=', self.id)],
            'context': {'default_child_profile_id': self.id}
        }


