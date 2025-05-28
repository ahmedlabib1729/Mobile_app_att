# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class QuranClass(models.Model):
    _name = 'quran.class'
    _description = 'Quran Class'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'code'

    code = fields.Char(
        string='كود الصف',
        required=True,
        copy=False,
        readonly=True,
        default='New'
    )

    name = fields.Char(
        string='تفاصيل الصف',
        required=True
    )

    program_type = fields.Selection([
        ('clubs', 'برامج النوادي'),
        ('ladies', 'برامج السيدات')
    ], string='نوع البرنامج', required=True)

    covenant_id = fields.Many2one(
        'quran.study.covenant',
        string='الميثاق',
        required=True,
        domain="[('program_type', '=', program_type)]"
    )

    teacher_id = fields.Many2one(
        'hr.employee',
        string='المدرس',
        related='covenant_id.teacher_id',
        readonly=True,
        store=True
    )

    start_date = fields.Date(
        string='تاريخ البدء',
        required=True,
        default=fields.Date.context_today
    )

    end_date = fields.Date(
        string='تاريخ الانتهاء',
        required=True
    )

    age_from = fields.Integer(
        string='العمر من',
        required=True,
        default=5
    )

    age_to = fields.Integer(
        string='العمر إلى',
        required=True,
        default=15
    )

    total_sessions = fields.Integer(
        string='عدد الحصص الإجمالي',
        required=True,
        default=1
    )

    session_duration = fields.Float(
        string='مدة الجلسة',
        help='مدة الجلسة بالساعات',
        required=True,
        default=1.0
    )

    terms_conditions = fields.Text(
        string='الشروط والأحكام'
    )

    # Students
    # عدّل حقل student_ids ليكون:
    student_ids = fields.Many2many(
        'quran.student',
        'quran_class_student_rel',
        'class_id',
        'student_id',
        string='الطلاب المشتركين',
        domain=[('state', '=', 'active')]
    )

    student_count = fields.Integer(
        string='عدد الطلاب',
        compute='_compute_student_count',
        store=True
    )

    active = fields.Boolean(
        string='نشط',
        default=True
    )

    state = fields.Selection([
        ('draft', 'مسودة'),
        ('confirmed', 'مؤكد'),
        ('in_progress', 'جاري'),
        ('completed', 'مكتمل'),
        ('cancelled', 'ملغي')
    ], string='الحالة', default='draft', tracking=True)

    # Schedule lines
    schedule_line_ids = fields.One2many(
        'quran.class.schedule',
        'class_id',
        string='جدول الحصص'
    )

    # Sessions
    session_ids = fields.One2many(
        'quran.session',
        'class_id',
        string='الجلسات'
    )

    session_count = fields.Integer(
        string='عدد الجلسات',
        compute='_compute_session_count',
        store=True
    )

    @api.onchange('program_type')
    def _onchange_program_type(self):
        """Clear covenant when program type changes"""
        if self.program_type:
            if self.covenant_id and self.covenant_id.program_type != self.program_type:
                self.covenant_id = False
            return {
                'domain': {
                    'covenant_id': [('program_type', '=', self.program_type)]
                }
            }
        else:
            self.covenant_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'New') == 'New':
                vals['code'] = self.env['ir.sequence'].next_by_code('quran.class') or 'New'
        return super().create(vals_list)

    @api.depends('student_ids')
    def _compute_student_count(self):
        for record in self:
            record.student_count = len(record.student_ids)

    @api.depends('session_ids')
    def _compute_session_count(self):
        for record in self:
            record.session_count = len(record.session_ids)

    @api.constrains('end_date', 'start_date')
    def _check_dates(self):
        for record in self:
            if record.end_date and record.start_date:
                if record.end_date < record.start_date:
                    raise ValidationError(_('تاريخ الانتهاء يجب أن يكون بعد تاريخ البدء'))

    @api.constrains('age_from', 'age_to')
    def _check_age_range(self):
        for record in self:
            if record.age_from < 0 or record.age_to < 0:
                raise ValidationError(_('العمر يجب أن يكون قيمة موجبة'))
            if record.age_to < record.age_from:
                raise ValidationError(_('العمر إلى يجب أن يكون أكبر من أو يساوي العمر من'))

    @api.constrains('total_sessions')
    def _check_total_sessions(self):
        for record in self:
            if record.total_sessions <= 0:
                raise ValidationError(_('عدد الحصص يجب أن يكون أكبر من صفر'))

    @api.constrains('session_duration')
    def _check_session_duration(self):
        for record in self:
            if record.session_duration <= 0:
                raise ValidationError(_('مدة الجلسة يجب أن تكون أكبر من صفر'))

    @api.constrains('student_ids')
    def _check_student_ages(self):
        for record in self:
            for student in record.student_ids:
                if student.age < record.age_from or student.age > record.age_to:
                    raise ValidationError(
                        _('الطالب %s عمره %s سنة وهو خارج النطاق العمري المسموح (%s - %s)') %
                        (student.name_ar, student.age, record.age_from, record.age_to)
                    )

    # الكود الموجود بالفعل _check_student_ages يتحقق من العمر
    # سنضيف بعده مباشرة:

    @api.constrains('student_ids', 'program_type')
    def _check_students_program_eligibility(self):
        """التحقق من أهلية الطلاب حسب نوع البرنامج"""
        for record in self:
            if record.program_type and record.student_ids:
                for student in record.student_ids:
                    # برامج النوادي
                    if record.program_type == 'clubs':
                        if student.age < 6 or student.age > 18:
                            raise ValidationError(
                                f'برامج النوادي مخصصة للأعمار من 6 إلى 18 سنة.\n'
                                f'الطالب {student.name_ar} عمره {student.age} سنة.'
                            )

                    # برامج السيدات
                    elif record.program_type == 'ladies':
                        if student.gender != 'female':
                            raise ValidationError(
                                f'برامج السيدات مخصصة للإناث فقط.\n'
                                f'الطالب {student.name_ar} غير مؤهل.'
                            )
                        if student.age < 18:
                            raise ValidationError(
                                f'برامج السيدات مخصصة للسيدات من عمر 18 سنة فأكثر.\n'
                                f'الطالبة {student.name_ar} عمرها {student.age} سنة.'
                            )

    @api.onchange('student_ids')
    def _onchange_student_ids(self):
        """تحذير فوري عند إضافة طالب غير مناسب"""
        if self.program_type and self.student_ids:
            invalid_students = []

            for student in self.student_ids:
                if self.program_type == 'clubs':
                    if student.age < 6 or student.age > 18:
                        invalid_students.append(f'{student.name_ar} (العمر: {student.age} سنة)')

                elif self.program_type == 'ladies':
                    if student.gender != 'female':
                        invalid_students.append(f'{student.name_ar} (ذكر)')
                    elif student.age < 18:
                        invalid_students.append(f'{student.name_ar} (العمر: {student.age} سنة)')

            if invalid_students:
                return {
                    'warning': {
                        'title': 'تحذير: طلاب غير مؤهلين',
                        'message': 'الطلاب التالية أسماؤهم غير مؤهلين لهذا البرنامج:\n' + '\n'.join(invalid_students)
                    }
                }

    def action_confirm(self):
        self.state = 'confirmed'

    def action_start(self):
        self.state = 'in_progress'

    def action_complete(self):
        self.state = 'completed'

    def action_cancel(self):
        self.state = 'cancelled'

    def action_draft(self):
        self.state = 'draft'

    def action_view_students(self):
        return {
            'name': _('طلاب الصف'),
            'view_mode': 'list,form',
            'res_model': 'quran.student',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.student_ids.ids)],
            'context': {'create': False}
        }

    def action_view_sessions(self):
        return {
            'name': _('جلسات الصف'),
            'view_mode': 'list,form',
            'res_model': 'quran.session',
            'type': 'ir.actions.act_window',
            'domain': [('class_id', '=', self.id)],
            'context': {'default_class_id': self.id}
        }

        # أضف بعد action_view_sessions
        def action_enroll_students(self):
            """فتح wizard لتسجيل الطلاب"""
            return {
                'name': 'تسجيل طلاب',
                'type': 'ir.actions.act_window',
                'res_model': 'quran.class.enrollment.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_class_id': self.id,
                }
            }

    def action_generate_sessions(self):
        """Generate sessions based on class schedule"""
        self.ensure_one()

        if not self.schedule_line_ids:
            raise ValidationError(_('يرجى إضافة جدول الحصص أولاً'))

        if not self.start_date or not self.end_date:
            raise ValidationError(_('يرجى تحديد تاريخ البداية والنهاية'))

        # Check if sessions already exist
        existing_sessions = self.session_ids.filtered(lambda s: s.state != 'cancelled')
        if existing_sessions:
            return {
                'name': _('تأكيد توليد الجلسات'),
                'type': 'ir.actions.act_window',
                'res_model': 'quran.class.generate.sessions.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_class_id': self.id,
                    'existing_sessions_count': len(existing_sessions)
                }
            }

        self._generate_sessions()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('نجح'),
                'message': _('تم توليد الجلسات بنجاح'),
                'type': 'success',
                'sticky': False,
            }
        }

    def _generate_sessions(self, regenerate=False):
        """Generate sessions for the class based on schedule"""
        from datetime import datetime, timedelta

        if regenerate:
            # Delete existing non-completed sessions
            self.session_ids.filtered(
                lambda s: s.state in ['scheduled', 'ongoing']
            ).unlink()

        sessions_to_create = []
        current_date = self.start_date

        while current_date <= self.end_date:
            weekday = str(current_date.weekday())

            # Map Python weekday (0=Monday) to our weekday (0=Sunday)
            weekday_map = {'6': '0', '0': '1', '1': '2', '2': '3', '3': '4', '4': '5', '5': '6'}
            mapped_weekday = weekday_map.get(weekday)

            # Find schedules for this weekday
            day_schedules = self.schedule_line_ids.filtered(
                lambda s: s.weekday == mapped_weekday and s.active
            )

            for schedule in day_schedules:
                # Calculate datetime
                start_hour = int(schedule.start_time)
                start_minute = int((schedule.start_time - start_hour) * 60)
                end_hour = int(schedule.end_time)
                end_minute = int((schedule.end_time - end_hour) * 60)

                start_datetime = datetime.combine(
                    current_date,
                    datetime.min.time().replace(hour=start_hour, minute=start_minute)
                )
                end_datetime = datetime.combine(
                    current_date,
                    datetime.min.time().replace(hour=end_hour, minute=end_minute)
                )

                sessions_to_create.append({
                    'class_id': self.id,
                    'session_date': current_date,
                    'start_datetime': start_datetime,
                    'end_datetime': end_datetime,
                    'state': 'scheduled'
                })

            current_date += timedelta(days=1)

        # Create all sessions
        if sessions_to_create:
            self.env['quran.session'].create(sessions_to_create)