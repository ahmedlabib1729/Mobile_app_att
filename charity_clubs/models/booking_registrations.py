# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)


class BookingRegistrations(models.Model):
    _name = 'charity.booking.registrations'
    _description = 'حجوزات الأقسام'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'
    _order = 'create_date desc'

    # حقل العرض
    display_name = fields.Char(
        string='اسم الحجز',
        compute='_compute_display_name',
        store=True
    )

    # نوع الحجز
    booking_type = fields.Selection([
        ('new', 'عضوة جديدة'),
        ('existing', 'عضوة مسجلة')
    ], string='نوع الحجز',
        default='new',
        tracking=True,
        help='حدد ما إذا كانت عضوة جديدة أو مسجلة سابقاً'
    )

    # العضوة المسجلة (للسيدات)
    member_id = fields.Many2one(
        'charity.member.profile',
        string='العضوة',
        tracking=True,
        help='اختر العضوة المسجلة سابقاً'
    )

    # معلومات المستفيد
    full_name = fields.Char(
        string='الاسم الثلاثي',
        tracking=True,
        help='أدخل الاسم الثلاثي'
    )

    mobile = fields.Char(
        string='رقم التواصل',
        tracking=True,
        help='رقم الهاتف للتواصل'
    )

    whatsapp = fields.Char(
        string='رقم الواتساب',
        help='رقم الواتساب للتواصل'
    )

    birth_date = fields.Date(
        string='تاريخ الميلاد',
        help='تاريخ الميلاد'
    )

    email = fields.Char(
        string='البريد الإلكتروني',
        help='البريد الإلكتروني للتواصل'
    )

    # صفة السيدة
    lady_type = fields.Selection([
        ('pioneer', 'رائدة'),
        ('volunteer', 'متطوعة'),
        ('member', 'عضوة')
    ], string='صفة السيدة',
        default='member',
        tracking=True,
        help='اختر صفة السيدة'
    )

    # حقول الحجز
    headquarters_id = fields.Many2one(
        'charity.headquarters',
        string='المقر',
        required=True,
        tracking=True,
        help='اختر المقر'
    )

    department_id = fields.Many2one(
        'charity.departments',
        string='القسم',
        domain="[('headquarters_id', '=', headquarters_id), ('type', 'in', ['ladies'])]",
        required=True,
        tracking=True,
        help='اختر القسم'
    )

    department_type = fields.Selection(
        related='department_id.type',
        string='نوع القسم',
        store=True
    )

    department_booking_price = fields.Float(
        string='سعر القسم',
        related='department_id.booking_price',
        readonly=True,
        help='سعر الحجز للقسم'
    )

    # معلومات إضافية
    registration_date = fields.Datetime(
        string='تاريخ إنشاء الحجز',
        default=fields.Datetime.now,
        readonly=True,
        tracking=True
    )

    state = fields.Selection([
        ('draft', 'مسودة'),
        ('confirmed', 'مؤكد'),
        ('approved', 'معتمد'),
        ('rejected', 'مرفوض'),
        ('cancelled', 'ملغي')
    ], string='الحالة',
        default='draft',
        tracking=True,
        help='حالة الحجز'
    )

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        default=lambda self: self.env.company,
        required=True
    )

    # العمر المحسوب
    age = fields.Integer(
        string='العمر',
        compute='_compute_age',
        store=True,
        help='العمر المحسوب من تاريخ الميلاد'
    )

    # الاشتراك المرتبط (للسيدات)
    subscription_id = fields.Many2one(
        'charity.member.subscription',
        string='الاشتراك',
        readonly=True,
        help='الاشتراك المرتبط بهذا الحجز'
    )

    program_ids = fields.Many2many(
        'charity.ladies.program',
        'booking_program_rel',
        'booking_id',
        'program_id',
        string='البرامج المختارة',
        domain="[('department_id', '=', department_id), ('is_active', '=', True)]",
        help='البرامج المختارة في هذا الحجز'
    )

    programs_count = fields.Integer(
        string='عدد البرامج',
        compute='_compute_programs_count',
        help='عدد البرامج المختارة'
    )

    id_card_file = fields.Binary(
        string='صورة الهوية',
        attachment=True,
        store=True,  # مهم
        help='أرفق صورة الهوية'
    )

    id_card_filename = fields.Char(
        string='اسم ملف الهوية'
    )

    passport_file = fields.Binary(
        string='صورة الباسبور',
        attachment=True,
        store=True,
        help='أرفق صورة جواز السفر'
    )

    passport_filename = fields.Char(
        string='اسم ملف الباسبور'
    )

    residence_file = fields.Binary(
        string='صورة الإقامة',
        attachment=True,
        store=True,
        help='أرفق صورة الإقامة'
    )

    residence_filename = fields.Char(
        string='اسم ملف الإقامة'
    )

    invoice_id = fields.Many2one(
        'account.move',
        string='الفاتورة',
        readonly=True,
        help='الفاتورة المرتبطة بهذا الحجز'
    )

    invoice_state = fields.Selection(
        related='invoice_id.state',
        string='حالة الفاتورة',
        store=True
    )

    invoice_payment_state = fields.Selection(
        related='invoice_id.payment_state',
        string='حالة الدفع',
        store=True
    )

    booking_mode = fields.Selection([
        ('programs', 'برامج'),
        ('workshop', 'ورشة')
    ], string='طريقة الحجز',  # تم التغيير من "نوع الحجز" إلى "طريقة الحجز"
        default='programs',
        tracking=True,
        help='اختر طريقة الحجز: برامج متعددة أو ورشة واحدة'
    )

    # الورشة المختارة
    workshop_id = fields.Many2one(
        'charity.ladies.workshop',
        string='الورشة',
        domain="[('department_id', '=', department_id), ('is_active', '=', True)]",
        tracking=True,
        help='الورشة المختارة'
    )

    workshop_price = fields.Float(
        string='سعر الورشة',
        related='workshop_id.price',
        readonly=True
    )

    # تحديث حقل السعر المحسوب
    final_price = fields.Float(
        string='السعر النهائي',
        compute='_compute_final_price',
        store=True,
        digits=(10, 2)
    )

    def fix_attachments(self):
        """إصلاح المرفقات التالفة"""
        for record in self:
            # البحث عن المرفقات الخاصة بهذا السجل
            attachments = self.env['ir.attachment'].search([
                ('res_model', '=', self._name),
                ('res_id', '=', record.id),
                ('res_field', 'in', ['id_card_file', 'passport_file', 'residence_file'])
            ])

            for attachment in attachments:
                try:
                    # التحقق من صحة البيانات
                    if attachment.datas:
                        # محاولة فك التشفير للتأكد من صحة البيانات
                        test_data = base64.b64decode(attachment.datas)
                        _logger.info(f"Attachment {attachment.name} is valid")
                    else:
                        _logger.warning(f"Attachment {attachment.name} has no data")
                except Exception as e:
                    _logger.error(f"Attachment {attachment.name} is corrupted: {str(e)}")
                    # محاولة إصلاح المرفق
                    if record[attachment.res_field]:
                        try:
                            # إعادة إنشاء المرفق
                            data = record[attachment.res_field]
                            if isinstance(data, bytes):
                                attachment.datas = base64.b64encode(data).decode('utf-8')
                                _logger.info(f"Fixed attachment {attachment.name}")
                        except Exception as fix_error:
                            _logger.error(f"Could not fix attachment: {str(fix_error)}")

    @api.model
    def create(self, vals):
        """Override للتأكد من صحة البيانات"""
        import base64

        # فحص الملفات قبل الحفظ
        for field in ['id_card_file', 'passport_file', 'residence_file']:
            if field in vals and vals[field]:
                try:
                    # التأكد أن البيانات base64 صحيحة
                    test_decode = base64.b64decode(vals[field])
                    _logger.info(f"{field}: Valid base64, size={len(test_decode)} bytes")
                except:
                    _logger.error(f"{field}: Invalid base64 data!")
                    # محاولة إصلاحها
                    if isinstance(vals[field], bytes):
                        vals[field] = base64.b64encode(vals[field]).decode('ascii')
                        _logger.info(f"{field}: Converted from bytes to base64")

        return super(BookingRegistrations, self).create(vals)

    @api.depends('full_name', 'department_id')
    def _compute_display_name(self):
        """حساب اسم العرض"""
        for record in self:
            if record.full_name and record.department_id:
                record.display_name = f"{record.full_name} - {record.department_id.name}"
            elif record.full_name:
                record.display_name = record.full_name
            else:
                record.display_name = "حجز جديد"

    @api.depends('birth_date', 'member_id')
    def _compute_age(self):
        """حساب العمر من تاريخ الميلاد"""
        from datetime import date
        from dateutil.relativedelta import relativedelta

        today = date.today()
        for record in self:
            birth_date = record.birth_date
            if record.booking_type == 'existing' and record.member_id:
                birth_date = record.member_id.birth_date

            if birth_date:
                age = relativedelta(today, birth_date)
                record.age = age.years
            else:
                record.age = 0

    @api.depends('program_ids')
    def _compute_programs_count(self):
        """حساب عدد البرامج المختارة"""
        for record in self:
            record.programs_count = len(record.program_ids)

    @api.onchange('booking_type')
    def _onchange_booking_type(self):
        """تنظيف الحقول عند تغيير نوع الحجز"""
        if self.booking_type == 'new':
            self.member_id = False
        else:
            self.full_name = False
            self.mobile = False
            self.whatsapp = False
            self.birth_date = False
            self.email = False
            self.lady_type = 'member'  # إعادة تعيين صفة السيدة

    @api.onchange('member_id')
    def _onchange_member_id(self):
        if self.booking_type == 'existing' and self.member_id:
            self.full_name = self.member_id.full_name
            self.birth_date = self.member_id.birth_date
            self.mobile = self.member_id.mobile
            self.whatsapp = self.member_id.whatsapp
            self.email = self.member_id.email
            self.lady_type = self.member_id.lady_type  # نقل صفة السيدة من ملف العضوة

            # ملء الملفات إذا كانت موجودة
            if self.member_id.id_card_file:
                self.id_card_file = self.member_id.id_card_file
                self.id_card_filename = self.member_id.id_card_filename

            if self.member_id.passport_file:
                self.passport_file = self.member_id.passport_file
                self.passport_filename = self.member_id.passport_filename

            if self.member_id.residence_file:
                self.residence_file = self.member_id.residence_file
                self.residence_filename = self.member_id.residence_filename

    @api.onchange('headquarters_id')
    def _onchange_headquarters_id(self):
        """تحديث domain الأقسام عند تغيير المقر"""
        if self.headquarters_id:
            self.department_id = False
            return {
                'domain': {
                    'department_id': [
                        ('headquarters_id', '=', self.headquarters_id.id),
                        ('type', 'in', ['ladies', 'nursery'])
                    ]
                }
            }

    def action_search_or_create_member(self):
        """البحث عن عضوة موجودة أو إنشاء جديدة"""
        self.ensure_one()

        # هذه الوظيفة خاصة بأقسام السيدات فقط
        if self.department_type != 'ladies':
            return {'type': 'ir.actions.do_nothing'}

        if self.booking_type != 'new' or not self.mobile:
            return {'type': 'ir.actions.do_nothing'}

        # البحث عن عضوة موجودة بنفس رقم الهاتف
        existing_member = self.env['charity.member.profile'].search([
            '|',
            ('mobile', '=', self.mobile),
            ('whatsapp', '=', self.whatsapp)
        ], limit=1)

        if existing_member:
            # عضوة موجودة
            self.booking_type = 'existing'
            self.member_id = existing_member

            # التحقق من وجود اشتراك نشط
            active_sub = self.env['charity.member.subscription'].search([
                ('member_id', '=', existing_member.id),
                ('department_id', '=', self.department_id.id),
                ('state', '=', 'active')
            ], limit=1)

            if active_sub:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'تنبيه',
                        'message': f'العضوة {existing_member.full_name} لديها اشتراك نشط ينتهي في {active_sub.end_date}',
                        'type': 'warning',
                        'sticky': True,
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'تم العثور على العضوة',
                        'message': f'العضوة {existing_member.full_name} موجودة في النظام',
                        'type': 'info',
                        'sticky': False,
                    }
                }

        return {'type': 'ir.actions.do_nothing'}

    def _create_member_and_subscription(self):
        """إنشاء ملف عضوة واشتراك جديد"""
        self.ensure_one()

        if self.booking_type != 'new' or self.department_type != 'ladies':
            return False

        # إنشاء ملف العضوة
        member_vals = {
            'full_name': self.full_name,
            'birth_date': self.birth_date,
            'mobile': self.mobile,
            'whatsapp': self.whatsapp,
            'email': self.email,
            'lady_type': self.lady_type,  # إضافة صفة السيدة
        }

        # إضافة الملفات إذا كانت موجودة
        if self.id_card_file:
            member_vals['id_card_file'] = self.id_card_file
            member_vals['id_card_filename'] = self.id_card_filename

        if self.passport_file:
            member_vals['passport_file'] = self.passport_file
            member_vals['passport_filename'] = self.passport_filename

        if self.residence_file:
            member_vals['residence_file'] = self.residence_file
            member_vals['residence_filename'] = self.residence_filename

        member = self.env['charity.member.profile'].create(member_vals)

        # إنشاء الاشتراك
        subscription_vals = {
            'member_id': member.id,
            'headquarters_id': self.headquarters_id.id,
            'department_id': self.department_id.id,
            'amount': self.department_booking_price,
            'state': 'confirmed'
        }

        # إضافة البرامج إذا تم اختيارها
        if self.program_ids:
            subscription_vals['program_ids'] = [(6, 0, self.program_ids.ids)]

        subscription = self.env['charity.member.subscription'].create(subscription_vals)

        # ربط الحجز بالعضوة والاشتراك
        self.booking_type = 'existing'
        self.member_id = member
        self.subscription_id = subscription

        return True

    def _validate_required_fields(self):
        """التحقق من الحقول المطلوبة"""
        for record in self:
            if record.booking_type == 'new':
                if not record.full_name:
                    raise ValidationError('يجب إدخال الاسم الثلاثي!')
                if not record.birth_date:
                    raise ValidationError('يجب إدخال تاريخ الميلاد!')
                if not record.mobile:
                    raise ValidationError('يجب إدخال رقم التواصل!')
                if record.department_type == 'ladies':
                    if not record.whatsapp:
                        raise ValidationError('يجب إدخال رقم الواتساب!')
                    if not record.lady_type:
                        raise ValidationError('يجب اختيار صفة السيدة!')

                    # التحقق من المستندات الإجبارية للسيدات الجدد
                    if not record.id_card_file:
                        raise ValidationError('يجب رفع صورة الهوية!')
                    if not record.passport_file:
                        raise ValidationError('يجب رفع صورة الباسبور!')
                    if not record.residence_file:
                        raise ValidationError('يجب رفع صورة الإقامة!')

            elif record.booking_type == 'existing' and record.department_type == 'ladies':
                if not record.member_id:
                    raise ValidationError('يجب اختيار العضوة!')

                # للعضوات الموجودات، نتحقق من وجود المستندات إما في الحجز أو في ملف العضوة
                has_id_card = record.id_card_file or (
                        hasattr(record.member_id, 'id_card_file') and record.member_id.id_card_file)
                has_passport = record.passport_file or (
                        hasattr(record.member_id, 'passport_file') and record.member_id.passport_file)
                has_residence = record.residence_file or (
                        hasattr(record.member_id, 'residence_file') and record.member_id.residence_file)

                if not has_id_card:
                    raise ValidationError('يجب رفع صورة الهوية أو التأكد من وجودها في ملف العضوة!')
                if not has_passport:
                    raise ValidationError('يجب رفع صورة الباسبور أو التأكد من وجودها في ملف العضوة!')
                if not has_residence:
                    raise ValidationError('يجب رفع صورة الإقامة أو التأكد من وجودها في ملف العضوة!')

    @api.constrains('mobile', 'whatsapp')
    def _check_phone_numbers(self):
        """التحقق من صحة أرقام الهواتف"""
        import re
        phone_pattern = re.compile(r'^[\d\s\-\+]+$')

        for record in self:
            if record.booking_type == 'new':
                if record.mobile and not phone_pattern.match(record.mobile):
                    raise ValidationError('رقم التواصل غير صحيح!')
                if record.whatsapp and not phone_pattern.match(record.whatsapp):
                    raise ValidationError('رقم الواتساب غير صحيح!')

    @api.constrains('email')
    def _check_email(self):
        """التحقق من صحة البريد الإلكتروني"""
        import re
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        for record in self:
            if record.booking_type == 'new' and record.email and not email_pattern.match(record.email):
                raise ValidationError('البريد الإلكتروني غير صحيح!')

    @api.constrains('birth_date')
    def _check_birth_date(self):
        """التحقق من صحة تاريخ الميلاد"""
        from datetime import date
        for record in self:
            if record.booking_type == 'new' and record.birth_date:
                if record.birth_date > date.today():
                    raise ValidationError('تاريخ الميلاد لا يمكن أن يكون في المستقبل!')

    @api.constrains('department_id')
    def _check_department_type(self):
        """التحقق من أن القسم من نوع سيدات أو حضانة"""
        for record in self:
            if record.department_id and record.department_id.type not in ['ladies']:
                raise ValidationError('يجب اختيار قسم من نوع سيدات أو حضانة!')

    def action_confirm(self):
        """تأكيد الحجز"""
        self.ensure_one()
        if self.state == 'draft':
            # التحقق من الحقول المطلوبة
            self._validate_required_fields()

            # إنشاء ملف العضوة والاشتراك إذا كان حجز جديد لقسم السيدات
            if self.booking_type == 'new' and self.department_type == 'ladies':
                self._create_member_and_subscription()
            elif self.booking_type == 'existing' and self.member_id and self.department_type == 'ladies':
                # تحديث ملفات العضوة الموجودة
                self._update_member_files()

                # إنشاء اشتراك جديد للعضوة الموجودة إذا لم يكن لديها اشتراك
                if not self.subscription_id:
                    subscription_vals = {
                        'member_id': self.member_id.id,
                        'headquarters_id': self.headquarters_id.id,
                        'department_id': self.department_id.id,
                        'amount': self.department_booking_price,
                        'state': 'confirmed'
                    }

                    # إضافة البرامج إذا تم اختيارها
                    if self.program_ids:
                        subscription_vals['program_ids'] = [(6, 0, self.program_ids.ids)]

                    subscription = self.env['charity.member.subscription'].create(subscription_vals)
                    self.subscription_id = subscription

            # إنشاء الفاتورة
            if self.department_type == 'ladies':
                self._create_invoice()

            self.state = 'confirmed'



    @api.depends('booking_mode', 'department_booking_price', 'workshop_price')
    def _compute_final_price(self):
        """حساب السعر النهائي حسب نوع الحجز"""
        for record in self:
            if record.booking_mode == 'workshop' and record.workshop_id:
                record.final_price = record.workshop_price
            else:
                record.final_price = record.department_booking_price

    @api.onchange('booking_mode')
    def _onchange_booking_mode(self):
        """تنظيف الحقول عند تغيير نوع الحجز"""
        if self.booking_mode == 'programs':
            self.workshop_id = False
        else:  # workshop
            self.program_ids = False

    @api.onchange('workshop_id')
    def _onchange_workshop_id(self):
        """التحقق من توفر مقاعد في الورشة"""
        if self.workshop_id and self.workshop_id.available_seats <= 0:
            self.workshop_id = False
            return {
                'warning': {
                    'title': 'الورشة ممتلئة',
                    'message': 'هذه الورشة ممتلئة ولا يمكن التسجيل فيها!'
                }
            }

    @api.constrains('booking_mode', 'program_ids', 'workshop_id')
    def _check_booking_selections(self):
        """التحقق من اختيارات الحجز"""
        for record in self:
            if record.department_type == 'ladies':
                if record.booking_mode == 'programs' and not record.program_ids:
                    raise ValidationError('يجب اختيار برنامج واحد على الأقل!')
                elif record.booking_mode == 'workshop' and not record.workshop_id:
                    raise ValidationError('يجب اختيار ورشة!')

    def _update_member_files(self):
        """تحديث ملفات العضوة الموجودة"""
        self.ensure_one()

        if self.booking_type == 'existing' and self.member_id:
            update_vals = {}

            # تحديث الملفات إذا تم رفع ملفات جديدة
            if self.id_card_file:
                update_vals['id_card_file'] = self.id_card_file
                update_vals['id_card_filename'] = self.id_card_filename

            if self.passport_file:
                update_vals['passport_file'] = self.passport_file
                update_vals['passport_filename'] = self.passport_filename

            if self.residence_file:
                update_vals['residence_file'] = self.residence_file
                update_vals['residence_filename'] = self.residence_filename

            # تحديث ملف العضوة إذا كان هناك تغييرات
            if update_vals:
                self.member_id.write(update_vals)

                # رسالة تأكيد
                self.message_post(
                    body=f"تم تحديث مستندات العضوة {self.member_id.full_name}",
                    subject="تحديث المستندات"
                )

    def action_approve(self):
        """اعتماد الحجز"""
        self.ensure_one()
        if self.state == 'confirmed':
            # تفعيل الاشتراك للسيدات
            if self.subscription_id and self.subscription_id.state == 'confirmed':
                self.subscription_id.action_activate()
            self.state = 'approved'

    def action_reject(self):
        """رفض الحجز"""
        self.ensure_one()
        if self.state in ('draft', 'confirmed'):
            # إلغاء الاشتراك إذا كان موجود
            if self.subscription_id and self.subscription_id.state != 'active':
                self.subscription_id.action_cancel()
            self.state = 'rejected'

    def action_cancel(self):
        """إلغاء الحجز"""
        self.ensure_one()
        if self.state != 'approved':
            # إلغاء الاشتراك إذا كان موجود
            if self.subscription_id and self.subscription_id.state != 'active':
                self.subscription_id.action_cancel()
            self.state = 'cancelled'

    def action_reset_draft(self):
        """إعادة الحجز إلى مسودة"""
        self.ensure_one()
        self.state = 'draft'

    def action_view_subscription(self):
        """عرض الاشتراك المرتبط"""
        self.ensure_one()
        if not self.subscription_id:
            return {'type': 'ir.actions.do_nothing'}

        return {
            'type': 'ir.actions.act_window',
            'name': 'الاشتراك',
            'view_mode': 'form',
            'res_model': 'charity.member.subscription',
            'res_id': self.subscription_id.id,
            'target': 'current',
        }

    def action_view_member(self):
        """عرض ملف العضوة"""
        self.ensure_one()
        if not self.member_id:
            return {'type': 'ir.actions.do_nothing'}

        return {
            'type': 'ir.actions.act_window',
            'name': 'ملف العضوة',
            'view_mode': 'form',
            'res_model': 'charity.member.profile',
            'res_id': self.member_id.id,
            'target': 'current',
        }

    def name_get(self):
        """تخصيص طريقة عرض اسم الحجز"""
        result = []
        for record in self:
            result.append((record.id, record.display_name))
        return result

    @api.constrains('program_ids')
    def _check_programs_capacity(self):
        """التحقق من توفر مقاعد في البرامج المختارة"""
        for record in self:
            if record.department_type == 'ladies' and record.program_ids:
                for program in record.program_ids:
                    if program.available_seats <= 0:
                        raise ValidationError(
                            f'البرنامج "{program.name}" ممتلئ ولا يمكن التسجيل فيه!'
                        )

    @api.constrains('department_id', 'program_ids')
    def _check_programs_department(self):
        """التحقق من أن جميع البرامج تنتمي لنفس القسم"""
        for record in self:
            if record.department_type == 'ladies' and record.program_ids:
                invalid_programs = record.program_ids.filtered(
                    lambda p: p.department_id != record.department_id
                )
                if invalid_programs:
                    raise ValidationError(
                        'جميع البرامج يجب أن تكون من نفس القسم!'
                    )

    @api.onchange('department_id')
    def _onchange_department_id(self):
        """تحديث السعر من القسم وإعادة تعيين البرامج"""
        if self.department_id:
            # مسح البرامج المختارة عند تغيير القسم
            self.program_ids = False

            # تحديث السعر من القسم إذا كان متوفراً
            if self.department_id.booking_price:
                self.department_booking_price = self.department_id.booking_price

    def action_view_programs(self):
        """عرض البرامج المختارة"""
        self.ensure_one()
        if not self.program_ids:
            return {'type': 'ir.actions.do_nothing'}

        return {
            'type': 'ir.actions.act_window',
            'name': 'البرامج المختارة',
            'view_mode': 'kanban,list,form',
            'res_model': 'charity.ladies.program',
            'domain': [('id', 'in', self.program_ids.ids)],
            'context': {
                'default_department_id': self.department_id.id
            }
        }

    def _create_invoice(self):
        """إنشاء فاتورة للحجز"""
        self.ensure_one()

        if self.department_type != 'ladies' or self.invoice_id:
            return False

        # تحديد اسم سطر الفاتورة
        if self.booking_mode == 'workshop':
            line_name = f'حجز ورشة {self.workshop_id.name} - {self.department_id.name}'
            price = self.workshop_price
        else:
            line_name = f'حجز قسم {self.department_id.name}'
            if self.program_ids:
                programs_names = ', '.join([program.name for program in self.program_ids])
                line_name += f' - البرامج: {programs_names}'
            price = self.department_booking_price

        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self._get_or_create_partner().id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'name': line_name,
                'quantity': 1,
                'price_unit': price,
            })],
            'ref': f'حجز رقم {self.id}',
        }

        invoice = self.env['account.move'].create(invoice_vals)
        self.invoice_id = invoice

        # تأكيد الفاتورة
        invoice.action_post()

        return invoice
        return invoice

    def _get_or_create_partner(self):
        """الحصول على أو إنشاء شريك (partner) للعضوة"""
        self.ensure_one()

        # البحث عن partner موجود
        if self.member_id:
            # البحث بناءً على رقم الهاتف
            partner = self.env['res.partner'].search([
                ('mobile', '=', self.member_id.mobile)
            ], limit=1)

            if partner:
                return partner

        # إنشاء partner جديد
        partner_vals = {
            'name': self.full_name or self.member_id.full_name,
            'mobile': self.mobile or self.member_id.mobile,
            'phone': self.whatsapp or self.member_id.whatsapp,
            'email': self.email or self.member_id.email,
            'customer_rank': 1,
            'is_company': False,
        }

        return self.env['res.partner'].create(partner_vals)

    def action_view_invoice(self):
        """عرض الفاتورة المرتبطة"""
        self.ensure_one()
        if not self.invoice_id:
            return {'type': 'ir.actions.do_nothing'}

        return {
            'type': 'ir.actions.act_window',
            'name': 'الفاتورة',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'target': 'current',
        }

    @api.depends('invoice_payment_state', 'subscription_id')
    def _check_and_activate_subscription(self):
        """تفعيل الاشتراك عند دفع الفاتورة"""
        for record in self:
            if (record.invoice_id and
                    record.invoice_payment_state == 'paid' and
                    record.subscription_id and
                    record.subscription_id.state == 'confirmed'):
                # تفعيل الاشتراك
                record.subscription_id.action_activate()

                # إرسال رسالة
                record.message_post(
                    body="تم تفعيل الاشتراك بعد استلام الدفعة",
                    subject="تفعيل الاشتراك"
                )

    # أضف هذا التابع لمراقبة تغيير حالة الدفع:

    def write(self, vals):
        """Override write لمراقبة تغيير حالة الدفع"""
        res = super().write(vals)

        # التحقق من حالة الدفع بعد التحديث
        for record in self:
            if record.invoice_payment_state == 'paid':
                record._check_and_activate_subscription()

        return res

    @api.model
    def _cron_check_paid_invoices(self):
        """Cron job للتحقق من الفواتير المدفوعة وتفعيل الاشتراكات"""
        bookings = self.search([
            ('state', '=', 'confirmed'),
            ('department_type', '=', 'ladies'),
            ('invoice_id', '!=', False),
            ('invoice_payment_state', '=', 'paid'),
            ('subscription_id.state', '=', 'confirmed')
        ])

        for booking in bookings:
            booking.subscription_id.with_context(force_activate=True).action_activate()
            booking.message_post(
                body="تم تفعيل الاشتراك تلقائياً بعد التحقق من دفع الفاتورة",
                subject="تفعيل تلقائي"
            )

    # أضف زر يدوي للتحقق من الدفع:

    def action_check_payment(self):
        """التحقق اليدوي من حالة الدفع وتفعيل الاشتراك"""
        self.ensure_one()

        if (self.invoice_id and
                self.invoice_payment_state == 'paid' and
                self.subscription_id and
                self.subscription_id.state == 'confirmed'):

            self.subscription_id.with_context(force_activate=True).action_activate()

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'تم تفعيل الاشتراك',
                    'message': 'تم تفعيل الاشتراك بنجاح بعد التحقق من الدفع',
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'لم يتم التفعيل',
                    'message': 'الفاتورة غير مدفوعة أو الاشتراك مفعل بالفعل',
                    'type': 'warning',
                    'sticky': False,
                }
            }


class AccountMove(models.Model):
    """توسيع نموذج الفاتورة لتفعيل الاشتراك عند الدفع"""
    _inherit = 'account.move'

    def _compute_amount(self):
        """Override لمراقبة حالة الدفع"""
        res = super()._compute_amount()

        for move in self:
            if move.move_type == 'out_invoice' and move.payment_state == 'paid':
                # البحث عن الحجز المرتبط
                booking = self.env['charity.booking.registrations'].search([
                    ('invoice_id', '=', move.id)
                ], limit=1)

                if booking and booking.subscription_id and booking.subscription_id.state == 'confirmed':
                    booking.subscription_id.with_context(force_activate=True).action_activate()
                    booking.message_post(
                        body="تم تفعيل الاشتراك تلقائياً بعد دفع الفاتورة",
                        subject="تفعيل تلقائي"
                    )

        return res