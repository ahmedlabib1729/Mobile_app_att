# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import re


class ProgramRegistration(models.Model):
    _name = 'program.registration'
    _description = 'تسجيل في البرنامج'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'
    _order = 'create_date desc'

    # معلومات التسجيل الأساسية
    program_id = fields.Many2one(
        'club.program',
        string='البرنامج',
        required=True,
        ondelete='restrict',
        tracking=True
    )

    club_id = fields.Many2one(
        'charity.club',
        string='النادي',
        related='program_id.club_id',
        store=True,
        readonly=True
    )

    display_name = fields.Char(
        string='اسم التسجيل',
        compute='_compute_display_name',
        store=True
    )

    registration_number = fields.Char(
        string='رقم التسجيل',
        required=True,
        copy=False,
        readonly=True,
        default='New'
    )

    registration_date = fields.Datetime(
        string='تاريخ التسجيل',
        default=fields.Datetime.now,
        required=True,
        tracking=True
    )

    # معلومات الطالب الشخصية
    student_name = fields.Char(
        string='اسم الطالب الثلاثى (كما في الهوية)',
        required=True,
        tracking=True
    )

    birth_date = fields.Date(
        string='تاريخ الميلاد',
        required=True
    )

    age = fields.Float(
        string='العمر',
        compute='_compute_age',
        store=True
    )

    gender = fields.Selection([
        ('male', 'ذكر'),
        ('female', 'أنثى')
    ], string='الجنس', required=True)

    nationality_id = fields.Many2one(
        'res.country',
        string='الجنسية',
        required=True
    )

    native_language = fields.Selection([
        ('arabic', 'Arabic A : Native speakers / لغة عربية للناطقين '),
        ('english', 'Arabic B : Non Native speakers  / لغة عربية لغير الناطقين'),

    ], string='تعلم اللغة العربية بالمدرسة', required=True)

    school_name = fields.Char(
        string='المدرسة'
    )
    school_name = fields.Char(
        string='المدرسة'
    )

    class_level = fields.Char(
        string='الصف الدراسي'
    )

    # أسئلة إضافية
    attended_arabic_club = fields.Selection([
        ('yes', 'نعم'),
        ('no', 'لا')
    ], string='هل كان مشترك بنادي لغة عربية سابقا', default='no')

    attended_summer_activities = fields.Selection([
        ('yes', 'نعم'),
        ('no', 'لا')
    ], string='هل كان مشترك بنوادي رؤيتي سابقا', default='no')

    interested_quran = fields.Selection([
        ('yes', 'نعم'),
        ('no', 'لا')
    ], string='هل اخذ القاعدة النورانية سابقا', default='no')

    # معلومات ولي الأمر
    father_name = fields.Char(
        string='اسم الأب',
        required=True
    )

    mother_name = fields.Char(
        string='اسم الأم',
        required=True
    )

    quran_memorisation = fields.Char(
        string=' مقدار حفظ القرآن',

    )
    parent_mobile = fields.Char(
        string='رقم جوال ولي الأمر',
        required=True
    )

    mother_whatsapp = fields.Char(
        string='WhatsApp الأم'
    )

    parent_email = fields.Char(
        string='البريد الإلكتروني'
    )

    # العنوان
    street = fields.Char(string='الشارع')
    city = fields.Char(string='المدينة')
    state_id = fields.Many2one('res.country.state', string='الإمارة')

    # المرفقات
    emirates_id_copy = fields.Binary(
        string=' نسخة من الهوية الإماراتية للوجهين',
        required=True
    )

    emirates_id_filename = fields.Char(string='اسم ملف الهوية')

    student_photo = fields.Binary(
        string='صورة الطالب'
    )

    student_photo_filename = fields.Char(string='اسم ملف الصورة')

    # معلومات طبية
    medical_conditions = fields.Text(
        string='حالات طبية خاصة',
        help='أي حالات طبية يجب أن نكون على علم بها'
    )

    allergies = fields.Text(
        string='الحساسية',
        help='أي حساسية من الطعام أو الأدوية'
    )

    # الحالة والموافقات
    state = fields.Selection([
        ('draft', 'مسودة'),
        ('submitted', 'مقدم'),
        ('confirmed', 'مؤكد'),
        ('waitlist', 'قائمة انتظار'),
        ('cancelled', 'ملغي')
    ], string='الحالة', default='draft', tracking=True)



    photo_permission = fields.Boolean(
        string='السماح بالتصوير',
        help='السماح باستخدام صور الطالب في أنشطة الجمعية'
    )

    # المعلومات المالية
    selected_terms = fields.Selection([
        ('term1', 'الترم الأول'),
        ('term2', 'الترم الثاني'),
        ('term3', 'الترم الثالث'),
        ('all', 'جميع الترمات')
    ], string='الترمات المختارة', required=True, default='all')

    total_amount = fields.Float(
        string='المبلغ الإجمالي',
        compute='_compute_total_amount',
        store=True,
        digits='Product Price'
    )

    paid_amount = fields.Float(
        string='المبلغ المدفوع',
        digits='Product Price',
        tracking=True
    )

    remaining_amount = fields.Float(
        string='المبلغ المتبقي',
        compute='_compute_remaining_amount',
        store=True,
        digits='Product Price'
    )

    payment_state = fields.Selection([
        ('not_paid', 'غير مدفوع'),
        ('partial', 'مدفوع جزئياً'),
        ('paid', 'مدفوع بالكامل')
    ], string='حالة الدفع', compute='_compute_payment_state', store=True)

    currency_id = fields.Many2one(
        'res.currency',
        string='العملة',
        related='program_id.currency_id',
        store=True,
        readonly=True
    )

    # ربط بالفواتير
    invoice_ids = fields.One2many(
        'account.move',
        'registration_id',
        string='الفواتير',
        domain=[('move_type', '=', 'out_invoice')]
    )

    invoice_count = fields.Integer(
        string='عدد الفواتير',
        compute='_compute_invoice_count'
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='ولي الأمر',
        compute='_compute_partner_id',
        store=True,
        readonly=False
    )

    # معلومات إضافية
    notes = fields.Text(string='ملاحظات')
    rejection_reason = fields.Text(string='سبب الرفض')

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        default=lambda self: self.env.company
    )

    @api.model
    def create(self, vals):
        """إنشاء رقم تسجيل تلقائي"""
        if vals.get('registration_number', 'New') == 'New':
            vals['registration_number'] = self.env['ir.sequence'].next_by_code(
                'program.registration'
            ) or 'New'

        # التحقق من السعة المتاحة
        if vals.get('program_id'):
            program = self.env['club.program'].browse(vals['program_id'])
            if program.is_full and vals.get('state') != 'waitlist':
                raise UserError('البرنامج ممتلئ! سيتم وضعك في قائمة الانتظار.')

        return super().create(vals)

    @api.depends('student_name', 'program_id.name')
    def _compute_display_name(self):
        for reg in self:
            reg.display_name = f"{reg.student_name} - {reg.program_id.name}"

    @api.depends('birth_date')
    def _compute_age(self):
        today = date.today()
        for reg in self:
            if reg.birth_date:
                age = relativedelta(today, reg.birth_date)
                reg.age = age.years + (age.months / 12.0)
            else:
                reg.age = 0

    @api.depends('selected_terms', 'program_id')
    def _compute_total_amount(self):
        for reg in self:
            if not reg.program_id:
                reg.total_amount = 0
                continue

            amount = 0
            if reg.selected_terms == 'term1':
                amount = reg.program_id.term1_price
            elif reg.selected_terms == 'term2':
                amount = reg.program_id.term2_price
            elif reg.selected_terms == 'term3':
                amount = reg.program_id.term3_price
            elif reg.selected_terms == 'all':
                amount = (reg.program_id.term1_price +
                          reg.program_id.term2_price +
                          reg.program_id.term3_price)

            reg.total_amount = amount

    @api.depends('total_amount', 'paid_amount')
    def _compute_remaining_amount(self):
        # تم نقل هذا المنطق إلى _compute_payment_amounts
        pass

    @api.depends('total_amount', 'paid_amount')
    def _compute_payment_state(self):
        for reg in self:
            if reg.paid_amount <= 0:
                reg.payment_state = 'not_paid'
            elif reg.paid_amount < reg.total_amount:
                reg.payment_state = 'partial'
            else:
                reg.payment_state = 'paid'

    @api.constrains('birth_date', 'program_id')
    def _check_age_eligibility(self):
        """التحقق من أهلية العمر"""
        for reg in self:
            if reg.birth_date and reg.program_id:
                if reg.age < reg.program_id.age_from:
                    raise ValidationError(
                        f'عمر الطالب ({reg.age:.1f} سنة) أقل من الحد الأدنى المطلوب ({reg.program_id.age_from} سنة)'
                    )
                if reg.age > reg.program_id.age_to:
                    raise ValidationError(
                        f'عمر الطالب ({reg.age:.1f} سنة) أكبر من الحد الأقصى المسموح ({reg.program_id.age_to} سنة)'
                    )

    @api.constrains('gender', 'program_id')
    def _check_gender_eligibility(self):
        """التحقق من أهلية الجنس"""
        for reg in self:
            if reg.program_id.gender != 'both' and reg.gender != reg.program_id.gender:
                gender_text = 'الذكور' if reg.program_id.gender == 'male' else 'الإناث'
                raise ValidationError(f'هذا البرنامج مخصص لـ {gender_text} فقط!')

    @api.constrains('parent_mobile', 'mother_whatsapp')
    def _check_phone_numbers(self):
        """التحقق من صحة أرقام الهواتف"""
        phone_pattern = re.compile(r'^[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{4,10}$')
        for reg in self:
            if reg.parent_mobile and not phone_pattern.match(reg.parent_mobile):
                raise ValidationError('رقم جوال ولي الأمر غير صحيح!')
            if reg.mother_whatsapp and not phone_pattern.match(reg.mother_whatsapp):
                raise ValidationError('رقم WhatsApp غير صحيح!')

    @api.constrains('parent_email')
    def _check_email(self):
        """التحقق من صحة البريد الإلكتروني"""
        for reg in self:
            if reg.parent_email:
                if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', reg.parent_email):
                    raise ValidationError('البريد الإلكتروني غير صحيح!')




    def action_submit(self):
        """تقديم طلب التسجيل"""
        for reg in self:
            if not reg.emirates_id_copy:
                raise UserError('يجب إرفاق نسخة من الهوية الإماراتية!')

            # التحقق من السعة
            if reg.program_id.is_full:
                reg.state = 'waitlist'
                # إرسال إشعار بقائمة الانتظار
            else:
                reg.state = 'submitted'
                # إرسال إشعار بالتقديم

    @api.depends('father_name', 'parent_mobile', 'parent_email')
    def _compute_partner_id(self):
        """إنشاء أو ربط ولي الأمر كـ partner"""
        Partner = self.env['res.partner']
        for reg in self:
            if reg.parent_email:
                partner = Partner.search([
                    ('email', '=', reg.parent_email)
                ], limit=1)
                if not partner and reg.father_name:
                    partner = Partner.create({
                        'name': reg.father_name,
                        'email': reg.parent_email,
                        'phone': reg.parent_mobile,
                        'is_company': False,
                        'customer_rank': 1,
                    })
                reg.partner_id = partner
            else:
                reg.partner_id = False

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for reg in self:
            reg.invoice_count = len(reg.invoice_ids)

    def action_confirm(self):
        """تأكيد التسجيل وإنشاء فاتورة"""
        for reg in self:
            if reg.state != 'submitted':
                raise UserError('يمكن تأكيد التسجيلات المقدمة فقط!')

            # التحقق من السعة مرة أخرى
            if reg.program_id.is_full:
                raise UserError('البرنامج ممتلئ! لا يمكن تأكيد التسجيل.')

            reg.state = 'confirmed'

            # إنشاء فاتورة
            reg._create_invoice()

            # إرسال إشعار بالتأكيد (يمكن إضافة template)
            reg.message_post(
                body='تم تأكيد التسجيل بنجاح',
                message_type='notification'
            )

    def _create_invoice(self):
        """إنشاء فاتورة للتسجيل"""
        for reg in self:
            if not reg.partner_id:
                raise UserError('يجب تحديد ولي الأمر أولاً!')

            # إنشاء الفاتورة
            invoice_vals = {
                'move_type': 'out_invoice',
                'partner_id': reg.partner_id.id,
                'registration_id': reg.id,
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': [(0, 0, {
                    'name': f'تسجيل {reg.student_name} في {reg.program_id.name}',
                    'quantity': 1.0,
                    'price_unit': reg.total_amount,
                    'tax_ids': [(6, 0, [])],  # بدون ضرائب
                })]
            }

            invoice = self.env['account.move'].create(invoice_vals)

            # إرسال رسالة في الشات
            reg.message_post(
                body=f'تم إنشاء فاتورة رقم {invoice.name}',
                message_type='notification'
            )

            return invoice

    def action_view_invoices(self):
        """عرض الفواتير المرتبطة"""
        return {
            'name': 'الفواتير',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('registration_id', '=', self.id)],
            'context': {
                'default_registration_id': self.id,
                'default_partner_id': self.partner_id.id,
            }
        }

    # تحديث الحقول
    paid_amount = fields.Float(
        string='المبلغ المدفوع',
        compute='_compute_payment_amounts',
        store=True,
        digits='Product Price'
    )

    remaining_amount = fields.Float(
        string='المبلغ المتبقي',
        compute='_compute_payment_amounts',
        store=True,
        digits='Product Price'
    )

    @api.depends('invoice_ids', 'invoice_ids.payment_state', 'invoice_ids.amount_total_signed',
                 'invoice_ids.amount_residual_signed')
    def _compute_payment_amounts(self):
        """حساب المبالغ المدفوعة من الفواتير"""
        for reg in self:
            total_paid = 0
            total_invoiced = 0

            for invoice in reg.invoice_ids.filtered(lambda i: i.state == 'posted'):
                total_invoiced += invoice.amount_total_signed
                # المدفوع = الإجمالي - المتبقي
                total_paid += (invoice.amount_total_signed - invoice.amount_residual_signed)

            reg.paid_amount = abs(total_paid)  # abs للتأكد من القيمة الموجبة
            reg.remaining_amount = reg.total_amount - abs(total_paid)

    @api.depends('total_amount', 'paid_amount')
    def _compute_payment_state(self):
        for reg in self:
            if reg.paid_amount <= 0:
                reg.payment_state = 'not_paid'
            elif reg.paid_amount < reg.total_amount:
                reg.payment_state = 'partial'
            else:
                reg.payment_state = 'paid'

    def action_cancel(self):
        """إلغاء التسجيل"""
        for reg in self:
            if reg.payment_state == 'paid':
                raise UserError('لا يمكن إلغاء التسجيل المدفوع! يرجى التواصل مع الإدارة.')
            reg.state = 'cancelled'

    def action_reset_draft(self):
        """إعادة للمسودة"""
        for reg in self:
            if reg.state == 'confirmed':
                raise UserError('لا يمكن إعادة التسجيل المؤكد للمسودة!')
            reg.state = 'draft'

    def action_register_payment(self):
        """تسجيل دفعة"""
        # يمكن فتح wizard لتسجيل الدفعة
        pass

    @api.model
    def check_waitlist(self):
        """فحص قائمة الانتظار عند توفر مقاعد"""
        waitlist = self.search([('state', '=', 'waitlist')], order='create_date')
        for reg in waitlist:
            if not reg.program_id.is_full:
                reg.state = 'submitted'
                # إرسال إشعار بتوفر مقعد