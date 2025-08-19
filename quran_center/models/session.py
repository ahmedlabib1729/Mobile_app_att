# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class QuranSession(models.Model):
    _name = 'quran.session'
    _description = 'Quran Session'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_datetime desc'
    _rec_name = 'name'

    name = fields.Char(
        string='اسم الجلسة',
        compute='_compute_name',
        store=True
    )

    class_id = fields.Many2one(
        'quran.class',
        string='الصف',
        required=True,
        ondelete='cascade'
    )

    class_session_type = fields.Selection(
        string='نوع الصف',
        related='class_id.class_session_type',
        store=True)

    covenant_id = fields.Many2one(
        related='class_id.covenant_id',
        string='الميثاق',
        store=True
    )

    teacher_id = fields.Many2one(
        related='class_id.teacher_id',
        string='المدرس الأول',
        store=True
    )

    teacher_id2 = fields.Many2one(
        related='class_id.teacher_id2',
        string='المدرس الثانى',
        store=True
    )

    program_type = fields.Selection(
        related='class_id.program_type',
        string='نوع البرنامج',
        store=True
    )

    session_date = fields.Date(
        string='تاريخ الجلسة',
        required=True
    )

    start_datetime = fields.Datetime(
        string='وقت البداية',
        required=True
    )

    end_datetime = fields.Datetime(
        string='وقت النهاية',
        required=True
    )

    state = fields.Selection([
        ('draft', 'مسودة'),
        ('scheduled', 'مجدولة'),
        ('ongoing', 'جارية'),
        ('completed', 'منتهية'),
        ('cancelled', 'ملغاة')
    ], string='الحالة', default='draft', tracking=True)

    # ============ حقول الاجتماع الأونلاين الجديدة ============

    # معلومات القناة والاجتماع
    meeting_channel_id = fields.Many2one(
        'discuss.channel',
        string='قناة الاجتماع',
        readonly=True,
        ondelete='set null'
    )

    meeting_url = fields.Char(
        string='رابط الاجتماع',
        readonly=True,
        copy=False
    )

    meeting_id = fields.Char(
        string='معرف الاجتماع',
        readonly=True,
        copy=False,
        help='معرف فريد للاجتماع يستخدم في الروابط'
    )

    # حالة الاجتماع
    meeting_state = fields.Selection([
        ('not_started', 'لم يبدأ'),
        ('ongoing', 'جاري'),
        ('ended', 'انتهى')
    ], string='حالة الاجتماع', default='not_started', tracking=True)

    meeting_start_time = fields.Datetime(
        string='وقت بدء الاجتماع الفعلي',
        readonly=True
    )

    meeting_end_time = fields.Datetime(
        string='وقت انتهاء الاجتماع الفعلي',
        readonly=True
    )

    is_meeting_active = fields.Boolean(
        string='الاجتماع نشط',
        default=False,
        readonly=True
    )

    # إعدادات الاجتماع
    allow_student_camera = fields.Boolean(
        string='السماح بكاميرا الطلاب',
        default=True
    )

    allow_student_mic = fields.Boolean(
        string='السماح بمايك الطلاب',
        default=True
    )

    auto_record_meeting = fields.Boolean(
        string='تسجيل الجلسة تلقائياً',
        default=False
    )

    meeting_recording_url = fields.Char(
        string='رابط التسجيل',
        readonly=True
    )

    # إحصائيات الاجتماع
    online_attendees_count = fields.Integer(
        string='عدد الحاضرين أونلاين',
        compute='_compute_online_stats',
        store=True
    )

    meeting_duration = fields.Float(
        string='مدة الاجتماع (بالدقائق)',
        compute='_compute_meeting_duration',
        store=True
    )

    # حقل محسوب لمعرفة إذا كان يمكن بدء الاجتماع
    can_start_meeting = fields.Boolean(
        string='يمكن بدء الاجتماع',
        compute='_compute_can_start_meeting'
    )

    # حقل محسوب لمعرفة إذا كان يمكن الانضمام للاجتماع
    can_join_meeting = fields.Boolean(
        string='يمكن الانضمام للاجتماع',
        compute='_compute_can_join_meeting'
    )

    # ============ نهاية الحقول الجديدة ============

    # Student Attendance
    enrolled_student_ids = fields.Many2many(
        related='class_id.student_ids',
        string='الطلاب المسجلين'
    )

    attendance_line_ids = fields.One2many(
        'quran.session.attendance',
        'session_id',
        string='سجل الحضور'
    )

    present_count = fields.Integer(
        string='عدد الحاضرين',
        compute='_compute_attendance_stats',
        store=True
    )

    absent_count = fields.Integer(
        string='عدد الغائبين',
        compute='_compute_attendance_stats',
        store=True
    )

    attendance_rate = fields.Float(
        string='نسبة الحضور',
        compute='_compute_attendance_stats',
        store=True
    )

    notes = fields.Text(
        string='ملاحظات'
    )

    @api.depends('class_id', 'session_date')
    def _compute_name(self):
        for record in self:
            if record.class_id and record.session_date:
                record.name = f"{record.class_id.name} - {record.session_date}"
            else:
                record.name = "جلسة جديدة"

    @api.depends('attendance_line_ids.status', 'attendance_line_ids.attendance_type')
    def _compute_attendance_stats(self):
        for record in self:
            attendance_lines = record.attendance_line_ids
            record.present_count = len(attendance_lines.filtered(lambda a: a.status == 'present'))
            record.absent_count = len(attendance_lines.filtered(lambda a: a.status == 'absent'))
            total = len(attendance_lines)
            record.attendance_rate = (record.present_count / total * 100) if total > 0 else 0

    @api.depends('attendance_line_ids.attendance_type', 'attendance_line_ids.status')
    def _compute_online_stats(self):
        for record in self:
            online_attendees = record.attendance_line_ids.filtered(
                lambda a: a.attendance_type == 'online' and a.status == 'present'
            )
            record.online_attendees_count = len(online_attendees)

    @api.depends('meeting_start_time', 'meeting_end_time', 'is_meeting_active')
    def _compute_meeting_duration(self):
        for record in self:
            if record.meeting_start_time:
                if record.meeting_end_time:
                    # الاجتماع انتهى - احسب المدة الكاملة
                    duration = record.meeting_end_time - record.meeting_start_time
                    record.meeting_duration = duration.total_seconds() / 60.0
                elif record.is_meeting_active:
                    # الاجتماع ما زال جاري - احسب من البداية حتى الآن
                    current_time = fields.Datetime.now()
                    duration = current_time - record.meeting_start_time
                    record.meeting_duration = duration.total_seconds() / 60.0
                else:
                    record.meeting_duration = 0.0
            else:
                record.meeting_duration = 0.0

    @api.model
    def update_active_meetings_duration(self):
        """Cron job لتحديث مدة الاجتماعات النشطة"""
        active_meetings = self.search([
            ('is_meeting_active', '=', True),
            ('meeting_start_time', '!=', False)
        ])
        for meeting in active_meetings:
            meeting._compute_meeting_duration()
            # تحديث حسابات الحضور أيضاً
            for attendance in meeting.attendance_line_ids:
                if attendance.is_online_now:
                    attendance._compute_online_duration()
                    attendance._compute_attendance_percentage()

    def action_refresh_calculations(self):
        """تحديث الحسابات يدوياً"""
        self.ensure_one()
        self._compute_online_duration()
        self._compute_attendance_percentage()
        return True



    def action_refresh_meeting_duration(self):
        """تحديث مدة الاجتماع يدوياً"""
        self.ensure_one()
        self._compute_meeting_duration()

        # تحديث حسابات الحضور أيضاً
        for attendance in self.attendance_line_ids:
            if attendance.attendance_type == 'online':
                attendance._compute_online_duration()
                attendance._compute_attendance_percentage()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('تم التحديث'),
                'message': _('تم تحديث مدة الاجتماع وحسابات الحضور'),
                'type': 'info',
                'sticky': False,
            }
        }

    def action_refresh_all_attendances(self):
        """تحديث حسابات جميع سجلات الحضور"""
        self.ensure_one()
        for attendance in self.attendance_line_ids:
            attendance._compute_online_duration()
            attendance._compute_attendance_percentage()
        return True

    @api.depends('class_session_type', 'state', 'start_datetime', 'is_meeting_active')
    def _compute_can_start_meeting(self):
        for record in self:
            can_start = (
                record.class_session_type == 'Online' and
                record.state in ['scheduled', 'ongoing'] and
                not record.is_meeting_active  # مهم: يجب أن يكون الاجتماع غير نشط
            )
            record.can_start_meeting = can_start

    @api.depends('class_session_type', 'is_meeting_active', 'meeting_channel_id')
    def _compute_can_join_meeting(self):
        for record in self:
            can_join = (
                record.class_session_type == 'Online' and
                record.is_meeting_active and
                bool(record.meeting_url)  # التأكد من وجود رابط
            )
            record.can_join_meeting = can_join

    @api.constrains('start_datetime', 'end_datetime')
    def _check_datetime_validity(self):
        for record in self:
            if record.end_datetime <= record.start_datetime:
                raise ValidationError(_('وقت النهاية يجب أن يكون بعد وقت البداية'))

    @api.model
    def create(self, vals):
        session = super().create(vals)
        # Create attendance lines only if state is scheduled or beyond
        if session.state in ['scheduled', 'ongoing', 'completed']:
            session._create_attendance_lines()
        return session

    def write(self, vals):
        result = super().write(vals)
        # إذا تم تغيير الحالة إلى scheduled، أنشئ سجلات الحضور
        if vals.get('state') == 'scheduled':
            self._create_attendance_lines()
        return result

    def _create_attendance_lines(self):
        """Create attendance lines for all enrolled students"""
        for session in self:
            # إنشاء سجلات الحضور فقط للجلسات المجدولة أو ما بعدها
            if session.state in ['scheduled', 'ongoing', 'completed']:
                existing_students = session.attendance_line_ids.mapped('student_id')
                for student in session.enrolled_student_ids:
                    if student not in existing_students:
                        self.env['quran.session.attendance'].create({
                            'session_id': session.id,
                            'student_id': student.id,
                            'status': 'absent',  # Default to absent
                            'attendance_type': 'online' if session.class_session_type == 'Online' else 'physical'
                        })

    # ============ دوال الاجتماع الأونلاين الجديدة ============

    def action_start_meeting(self):
        """فتح wizard بدء الاجتماع الأونلاين"""
        self.ensure_one()

        if not self.can_start_meeting:
            raise ValidationError(_('لا يمكن بدء الاجتماع في الوقت الحالي'))

        # فتح الـ wizard بدلاً من البدء المباشر
        return {
            'name': _('بدء الاجتماع الأونلاين'),
            'type': 'ir.actions.act_window',
            'res_model': 'quran.session.start.meeting.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_session_id': self.id,
            }
        }

    def _grant_portal_access_to_meeting(self):
        """منح صلاحيات الوصول للاجتماع لمستخدمي البورتال"""
        self.ensure_one()

        if not self.meeting_channel_id:
            return

        # إضافة جميع الطلاب للقناة
        portal_partners = []
        for student in self.enrolled_student_ids:
            if student.user_id and student.user_id.has_group('base.group_portal'):
                portal_partners.append(student.user_id.partner_id.id)

        if portal_partners:
            # إضافة الشركاء للقناة
            self.meeting_channel_id.write({
                'channel_partner_ids': [(4, partner_id) for partner_id in portal_partners]
            })

            # منح صلاحيات القراءة للقناة
            self.meeting_channel_id.sudo().write({
                'group_public_id': [(4, self.env.ref('base.group_portal').id)]
            })

    def action_start_meeting_direct(self):
        """بدء الاجتماع مباشرة (تستخدم من الـ wizard)"""
        self.ensure_one()

        # إنشاء معرف فريد للاجتماع
        meeting_id = self.env['ir.sequence'].next_by_code('quran.session.meeting') or \
                     f"QRN-{self.id}-{datetime.now().strftime('%Y%m%d%H%M')}"

        # تحديث معلومات الاجتماع
        self.write({
            'meeting_id': meeting_id,
            'meeting_state': 'ongoing',
            'meeting_start_time': fields.Datetime.now(),  # مهم: استخدم fields.Datetime.now()
            'is_meeting_active': True,
            'state': 'ongoing' if self.state == 'scheduled' else self.state
        })

        # إرسال إشعار للطلاب
        self._send_meeting_notification('started')
        self._grant_portal_access_to_meeting()
        return True

    def action_end_meeting(self):
        """إنهاء الاجتماع الأونلاين"""
        self.ensure_one()

        if not self.is_meeting_active:
            raise ValidationError(_('لا يوجد اجتماع نشط لإنهائه'))

        # تحديث معلومات الاجتماع
        self.write({
            'meeting_state': 'ended',
            'meeting_end_time': fields.Datetime.now(),  # مهم: استخدم fields.Datetime.now()
            'is_meeting_active': False,
        })

        # فرض إعادة حساب مدة الاجتماع
        self._compute_meeting_duration()

        # تحديث حالة الجلسة إذا لزم الأمر
        if self.state == 'ongoing':
            self.action_complete()

        # إرسال إشعار بانتهاء الاجتماع
        self._send_meeting_notification('ended')

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('تم إنهاء الاجتماع'),
                'message': _('تم إنهاء الاجتماع بنجاح'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_join_meeting(self):
        """الانضمام للاجتماع الجاري"""
        self.ensure_one()

        if not self.can_join_meeting:
            raise ValidationError(_('لا يمكن الانضمام للاجتماع في الوقت الحالي'))

        return {
            'type': 'ir.actions.act_url',
            'url': self.meeting_url,
            'target': 'new',
        }

    def _send_meeting_notification(self, notification_type):
        """إرسال إشعارات الاجتماع"""
        if notification_type == 'started':
            subject = f'بدأ الاجتماع الأونلاين - {self.name}'
            body = f'''
                <p>تم بدء الاجتماع الأونلاين للجلسة: <strong>{self.name}</strong></p>
                <p>يمكنك الانضمام من خلال النقر على الرابط أدناه:</p>
                <p><a href="{self.meeting_url}" class="btn btn-primary">انضمام للاجتماع</a></p>
            '''
        elif notification_type == 'ended':
            subject = f'انتهى الاجتماع الأونلاين - {self.name}'
            body = f'''
                <p>تم إنهاء الاجتماع الأونلاين للجلسة: <strong>{self.name}</strong></p>
                <p>مدة الاجتماع: {self.meeting_duration:.0f} دقيقة</p>
            '''
        else:
            return

        # إرسال للطلاب المسجلين
        for student in self.enrolled_student_ids:
            if student.email:
                self.env['mail.mail'].create({
                    'subject': subject,
                    'body_html': body,
                    'email_to': student.email,
                    'email_from': self.env.company.email or 'noreply@quran-center.com',
                }).send()

    def action_meeting_settings(self):
        """فتح إعدادات الاجتماع"""
        self.ensure_one()
        return {
            'name': _('إعدادات الاجتماع'),
            'type': 'ir.actions.act_window',
            'res_model': 'quran.session',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'form_view_initial_mode': 'edit',
                'dialog_size': 'medium',
            },
            'views': [(self.env.ref('quran_center.view_session_meeting_settings_form').id, 'form')],
        }

    # ============ نهاية دوال الاجتماع الأونلاين ============

    def action_start(self):
        self.state = 'ongoing'

    def action_schedule(self):
        """تحويل الجلسة من مسودة إلى مجدولة"""
        self.ensure_one()
        if self.state != 'draft':
            raise ValidationError(_('يمكن جدولة الجلسات التي في حالة مسودة فقط'))

        # التحقق من البيانات المطلوبة
        if not self.class_id:
            raise ValidationError(_('يجب تحديد الصف'))
        if not self.session_date:
            raise ValidationError(_('يجب تحديد تاريخ الجلسة'))
        if not self.start_datetime or not self.end_datetime:
            raise ValidationError(_('يجب تحديد وقت البداية والنهاية'))

        self.state = 'scheduled'

    def action_draft(self):
        """إرجاع الجلسة إلى حالة المسودة"""
        self.ensure_one()
        if self.state not in ['scheduled', 'cancelled']:
            raise ValidationError(_('يمكن إرجاع الجلسات المجدولة أو الملغاة فقط إلى المسودة'))

        self.state = 'draft'

    def action_complete(self):
        self.state = 'completed'

    def action_cancel(self):
        self.state = 'cancelled'

    def action_mark_all_present(self):
        """Mark all students as present"""
        self.attendance_line_ids.write({'status': 'present'})

    def action_mark_all_absent(self):
        """Mark all students as absent"""
        self.attendance_line_ids.write({'status': 'absent'})

    def action_view_attendance(self):
        return {
            'name': _('تسجيل الحضور'),
            'view_mode': 'list',
            'res_model': 'quran.session.attendance',
            'type': 'ir.actions.act_window',
            'domain': [('session_id', '=', self.id)],
            'context': {
                'default_session_id': self.id,
                'create': False,
                'delete': False
            }
        }

        # في models/session.py - class QuranSession

        @api.model
        def auto_schedule_draft_sessions(self):
            """Cron job لتحويل الجلسات من مسودة إلى مجدولة قبل موعدها بيوم"""
            # الحصول على تاريخ الغد
            tomorrow = fields.Date.today() + timedelta(days=1)

            # البحث عن الجلسات في حالة مسودة والتي موعدها غداً
            draft_sessions = self.search([
                ('state', '=', 'draft'),
                ('session_date', '=', tomorrow),
                ('class_id', '!=', False),  # التأكد من وجود صف
                ('start_datetime', '!=', False),  # التأكد من وجود وقت البداية
                ('end_datetime', '!=', False),  # التأكد من وجود وقت النهاية
            ])

            scheduled_count = 0
            errors = []

            for session in draft_sessions:
                try:
                    # التحقق من صحة البيانات قبل الجدولة
                    if not session.class_id:
                        errors.append(f"الجلسة {session.name}: لا يوجد صف محدد")
                        continue

                    if not session.session_date:
                        errors.append(f"الجلسة {session.name}: لا يوجد تاريخ محدد")
                        continue

                    if not session.start_datetime or not session.end_datetime:
                        errors.append(f"الجلسة {session.name}: لا يوجد وقت بداية أو نهاية")
                        continue

                    # تحويل الجلسة إلى مجدولة
                    session.action_schedule()
                    scheduled_count += 1

                    # إرسال إشعار للمعلم
                    if session.teacher_id and session.teacher_id.user_id:
                        session.message_post(
                            body=f"تم جدولة هذه الجلسة تلقائياً. موعد الجلسة: {session.session_date}",
                            partner_ids=[session.teacher_id.user_id.partner_id.id],
                            subtype_xmlid='mail.mt_comment'
                        )

                except Exception as e:
                    errors.append(f"خطأ في جدولة {session.name}: {str(e)}")
                    _logger.error(f"Error scheduling session {session.id}: {str(e)}")

            # تسجيل النتيجة في السجل
            message = f"تم جدولة {scheduled_count} جلسة بنجاح."
            if errors:
                message += f"\n\nالأخطاء:\n" + "\n".join(errors)

            _logger.info(f"Auto scheduling sessions: {message}")

            # إرسال تقرير للمسؤول (اختياري)
            if scheduled_count > 0 or errors:
                self._send_scheduling_report(scheduled_count, errors)

            return True

        def _send_scheduling_report(self, scheduled_count, errors):
            """إرسال تقرير الجدولة التلقائية للمسؤول"""
            # يمكنك تخصيص هذا حسب الحاجة
            admin_users = self.env['res.users'].search([
                ('groups_id', 'in', [self.env.ref('base.group_system').id])
            ], limit=1)

            if admin_users:
                body = f"""
                <h3>تقرير الجدولة التلقائية للجلسات</h3>
                <p>تم تشغيل الجدولة التلقائية بتاريخ: {fields.Datetime.now()}</p>
                <p><strong>النتائج:</strong></p>
                <ul>
                    <li>عدد الجلسات المجدولة: {scheduled_count}</li>
                    <li>عدد الأخطاء: {len(errors)}</li>
                </ul>
                """

                if errors:
                    body += """
                    <p><strong>تفاصيل الأخطاء:</strong></p>
                    <ul>
                    """
                    for error in errors:
                        body += f"<li>{error}</li>"
                    body += "</ul>"

                # إنشاء رسالة في صندوق الوارد
                self.env['mail.message'].create({
                    'model': 'quran.session',
                    'body': body,
                    'subject': 'تقرير الجدولة التلقائية للجلسات',
                    'message_type': 'notification',
                    'partner_ids': [(4, admin_users[0].partner_id.id)],
                })


class SessionAttendance(models.Model):
    _name = 'quran.session.attendance'
    _description = 'Session Attendance'
    _rec_name = 'student_id'

    session_id = fields.Many2one(
        'quran.session',
        string='الجلسة',
        required=True,
        ondelete='cascade'
    )

    student_id = fields.Many2one(
        'quran.student',
        string='الطالب',
        required=True
    )

    status = fields.Selection([
        ('present', 'حاضر'),
        ('absent', 'غائب'),
        ('late', 'متأخر'),
        ('excused', 'غياب بعذر')
    ], string='الحالة', required=True, default='absent')

    # ============ حقول الحضور الأونلاين الجديدة ============

    attendance_type = fields.Selection([
        ('physical', 'حضوري'),
        ('online', 'أونلاين')
    ], string='نوع الحضور', default='physical', required=True)

    online_join_time = fields.Datetime(
        string='وقت الانضمام',
        readonly=True
    )

    online_leave_time = fields.Datetime(
        string='وقت المغادرة',
        readonly=True
    )

    online_duration = fields.Float(
        string='مدة الحضور (بالدقائق)',
        compute='_compute_online_duration',
        store=True
    )

    attendance_percentage = fields.Float(
        string='نسبة الحضور %',
        compute='_compute_attendance_percentage',
        store=True
    )

    is_online_now = fields.Boolean(
        string='متصل الآن',
        default=False,
        readonly=True
    )

    online_join_count = fields.Integer(
        string='عدد مرات الدخول',
        default=0,
        readonly=True,
        help='عدد المرات التي دخل فيها الطالب للاجتماع'
    )

    # معلومات الجهاز والاتصال
    connection_quality = fields.Selection([
        ('excellent', 'ممتاز'),
        ('good', 'جيد'),
        ('fair', 'مقبول'),
        ('poor', 'ضعيف')
    ], string='جودة الاتصال', readonly=True)

    device_type = fields.Char(
        string='نوع الجهاز',
        readonly=True,
        help='نوع الجهاز المستخدم (كمبيوتر، هاتف، تابلت)'
    )

    # ============ نهاية الحقول الجديدة ============

    # Performance fields
    behavior_score = fields.Selection([
        ('1', '1'),
        ('2', '2')
    ], string='السلوك')

    memorization_score = fields.Selection([
        ('1', '1'),
        ('2', '2')
    ], string='الحفظ')

    revision_score = fields.Selection([
        ('1', '1'),
        ('2', '2')
    ], string='المراجعة')

    # Daily memorization
    daily_memorization_surah = fields.Selection([
        ('001', 'الفاتحة'),
        ('002', 'البقرة'),
        ('003', 'آل عمران'),
        ('004', 'النساء'),
        ('005', 'المائدة'),
        ('006', 'الأنعام'),
        ('007', 'الأعراف'),
        ('008', 'الأنفال'),
        ('009', 'التوبة'),
        ('010', 'يونس'),
        ('011', 'هود'),
        ('012', 'يوسف'),
        ('013', 'الرعد'),
        ('014', 'إبراهيم'),
        ('015', 'الحجر'),
        ('016', 'النحل'),
        ('017', 'الإسراء'),
        ('018', 'الكهف'),
        ('019', 'مريم'),
        ('020', 'طه'),
        ('021', 'الأنبياء'),
        ('022', 'الحج'),
        ('023', 'المؤمنون'),
        ('024', 'النور'),
        ('025', 'الفرقان'),
        ('026', 'الشعراء'),
        ('027', 'النمل'),
        ('028', 'القصص'),
        ('029', 'العنكبوت'),
        ('030', 'الروم'),
        ('031', 'لقمان'),
        ('032', 'السجدة'),
        ('033', 'الأحزاب'),
        ('034', 'سبأ'),
        ('035', 'فاطر'),
        ('036', 'يس'),
        ('037', 'الصافات'),
        ('038', 'ص'),
        ('039', 'الزمر'),
        ('040', 'غافر'),
        ('041', 'فصلت'),
        ('042', 'الشورى'),
        ('043', 'الزخرف'),
        ('044', 'الدخان'),
        ('045', 'الجاثية'),
        ('046', 'الأحقاف'),
        ('047', 'محمد'),
        ('048', 'الفتح'),
        ('049', 'الحجرات'),
        ('050', 'ق'),
        ('051', 'الذاريات'),
        ('052', 'الطور'),
        ('053', 'النجم'),
        ('054', 'القمر'),
        ('055', 'الرحمن'),
        ('056', 'الواقعة'),
        ('057', 'الحديد'),
        ('058', 'المجادلة'),
        ('059', 'الحشر'),
        ('060', 'الممتحنة'),
        ('061', 'الصف'),
        ('062', 'الجمعة'),
        ('063', 'المنافقون'),
        ('064', 'التغابن'),
        ('065', 'الطلاق'),
        ('066', 'التحريم'),
        ('067', 'الملك'),
        ('068', 'القلم'),
        ('069', 'الحاقة'),
        ('070', 'المعارج'),
        ('071', 'نوح'),
        ('072', 'الجن'),
        ('073', 'المزمل'),
        ('074', 'المدثر'),
        ('075', 'القيامة'),
        ('076', 'الإنسان'),
        ('077', 'المرسلات'),
        ('078', 'النبأ'),
        ('079', 'النازعات'),
        ('080', 'عبس'),
        ('081', 'التكوير'),
        ('082', 'الانفطار'),
        ('083', 'المطففين'),
        ('084', 'الانشقاق'),
        ('085', 'البروج'),
        ('086', 'الطارق'),
        ('087', 'الأعلى'),
        ('088', 'الغاشية'),
        ('089', 'الفجر'),
        ('090', 'البلد'),
        ('091', 'الشمس'),
        ('092', 'الليل'),
        ('093', 'الضحى'),
        ('094', 'الشرح'),
        ('095', 'التين'),
        ('096', 'العلق'),
        ('097', 'القدر'),
        ('098', 'البينة'),
        ('099', 'الزلزلة'),
        ('100', 'العاديات'),
        ('101', 'القارعة'),
        ('102', 'التكاثر'),
        ('103', 'العصر'),
        ('104', 'الهمزة'),
        ('105', 'الفيل'),
        ('106', 'قريش'),
        ('107', 'الماعون'),
        ('108', 'الكوثر'),
        ('109', 'الكافرون'),
        ('110', 'النصر'),
        ('111', 'المسد'),
        ('112', 'الإخلاص'),
        ('113', 'الفلق'),
        ('114', 'الناس')
    ], string='الحفظ اليومي')

    verse_from = fields.Integer(string='الآيات من')
    verse_to = fields.Integer(string='إلى')

    revision_surah = fields.Selection([
        ('001', 'الفاتحة'),
        ('002', 'البقرة'),
        ('003', 'آل عمران'),
        ('004', 'النساء'),
        ('005', 'المائدة'),
        ('006', 'الأنعام'),
        ('007', 'الأعراف'),
        ('008', 'الأنفال'),
        ('009', 'التوبة'),
        ('010', 'يونس'),
        ('011', 'هود'),
        ('012', 'يوسف'),
        ('013', 'الرعد'),
        ('014', 'إبراهيم'),
        ('015', 'الحجر'),
        ('016', 'النحل'),
        ('017', 'الإسراء'),
        ('018', 'الكهف'),
        ('019', 'مريم'),
        ('020', 'طه'),
        ('021', 'الأنبياء'),
        ('022', 'الحج'),
        ('023', 'المؤمنون'),
        ('024', 'النور'),
        ('025', 'الفرقان'),
        ('026', 'الشعراء'),
        ('027', 'النمل'),
        ('028', 'القصص'),
        ('029', 'العنكبوت'),
        ('030', 'الروم'),
        ('031', 'لقمان'),
        ('032', 'السجدة'),
        ('033', 'الأحزاب'),
        ('034', 'سبأ'),
        ('035', 'فاطر'),
        ('036', 'يس'),
        ('037', 'الصافات'),
        ('038', 'ص'),
        ('039', 'الزمر'),
        ('040', 'غافر'),
        ('041', 'فصلت'),
        ('042', 'الشورى'),
        ('043', 'الزخرف'),
        ('044', 'الدخان'),
        ('045', 'الجاثية'),
        ('046', 'الأحقاف'),
        ('047', 'محمد'),
        ('048', 'الفتح'),
        ('049', 'الحجرات'),
        ('050', 'ق'),
        ('051', 'الذاريات'),
        ('052', 'الطور'),
        ('053', 'النجم'),
        ('054', 'القمر'),
        ('055', 'الرحمن'),
        ('056', 'الواقعة'),
        ('057', 'الحديد'),
        ('058', 'المجادلة'),
        ('059', 'الحشر'),
        ('060', 'الممتحنة'),
        ('061', 'الصف'),
        ('062', 'الجمعة'),
        ('063', 'المنافقون'),
        ('064', 'التغابن'),
        ('065', 'الطلاق'),
        ('066', 'التحريم'),
        ('067', 'الملك'),
        ('068', 'القلم'),
        ('069', 'الحاقة'),
        ('070', 'المعارج'),
        ('071', 'نوح'),
        ('072', 'الجن'),
        ('073', 'المزمل'),
        ('074', 'المدثر'),
        ('075', 'القيامة'),
        ('076', 'الإنسان'),
        ('077', 'المرسلات'),
        ('078', 'النبأ'),
        ('079', 'النازعات'),
        ('080', 'عبس'),
        ('081', 'التكوير'),
        ('082', 'الانفطار'),
        ('083', 'المطففين'),
        ('084', 'الانشقاق'),
        ('085', 'البروج'),
        ('086', 'الطارق'),
        ('087', 'الأعلى'),
        ('088', 'الغاشية'),
        ('089', 'الفجر'),
        ('090', 'البلد'),
        ('091', 'الشمس'),
        ('092', 'الليل'),
        ('093', 'الضحى'),
        ('094', 'الشرح'),
        ('095', 'التين'),
        ('096', 'العلق'),
        ('097', 'القدر'),
        ('098', 'البينة'),
        ('099', 'الزلزلة'),
        ('100', 'العاديات'),
        ('101', 'القارعة'),
        ('102', 'التكاثر'),
        ('103', 'العصر'),
        ('104', 'الهمزة'),
        ('105', 'الفيل'),
        ('106', 'قريش'),
        ('107', 'الماعون'),
        ('108', 'الكوثر'),
        ('109', 'الكافرون'),
        ('110', 'النصر'),
        ('111', 'المسد'),
        ('112', 'الإخلاص'),
        ('113', 'الفلق'),
        ('114', 'الناس')
    ], string='سورة المراجعة')

    revision_verse_from = fields.Integer(string='آية المراجعة من')
    revision_verse_to = fields.Integer(string='إلى آية')

    notes = fields.Text(
        string='ملاحظات'
    )

    # Related fields for reporting
    class_id = fields.Many2one(
        related='session_id.class_id',
        string='الصف',
        store=True
    )

    session_date = fields.Date(
        related='session_id.session_date',
        string='التاريخ',
        store=True
    )

    teacher_id = fields.Many2one(
        related='session_id.teacher_id',
        string='المدرس',
        store=True
    )

    session_name = fields.Char(
        related='session_id.name',
        string='اسم الجلسة',
        store=True
    )

    program_type = fields.Selection(
        related='session_id.program_type',
        string='نوع البرنامج',
        store=True
    )

    # إضافة حقل class_session_type كـ related field
    class_session_type = fields.Selection(
        related='session_id.class_session_type',
        string='نوع الصف',
        store=True,
        readonly=True
    )

    _sql_constraints = [
        ('unique_student_session', 'UNIQUE(session_id, student_id)',
         'الطالب مسجل مسبقاً في هذه الجلسة!')
    ]

    # ============ دوال الحضور الأونلاين الجديدة ============

    @api.depends('online_join_time', 'online_leave_time')
    def _compute_online_duration(self):
        for record in self:
            if record.online_join_time and record.online_leave_time:
                duration = record.online_leave_time - record.online_join_time
                record.online_duration = duration.total_seconds() / 60.0
            elif record.online_join_time and record.is_online_now:
                # إذا كان الطالب متصل الآن، احسب المدة من وقت الدخول حتى الآن
                duration = datetime.now() - record.online_join_time
                record.online_duration = duration.total_seconds() / 60.0
            else:
                record.online_duration = 0.0

    @api.depends('online_duration', 'session_id.meeting_duration', 'session_id.meeting_start_time')
    def _compute_attendance_percentage(self):
        for record in self:
            if record.attendance_type == 'online' and record.session_id.class_session_type == 'Online':
                # حساب مدة الاجتماع الفعلية
                if record.session_id.meeting_start_time:
                    if record.session_id.meeting_end_time:
                        # الاجتماع انتهى
                        meeting_duration = (
                                                       record.session_id.meeting_end_time - record.session_id.meeting_start_time).total_seconds() / 60.0
                    else:
                        # الاجتماع ما زال جاري
                        meeting_duration = (
                                                       datetime.now() - record.session_id.meeting_start_time).total_seconds() / 60.0

                    if meeting_duration > 0 and record.online_duration > 0:
                        percentage = (record.online_duration / meeting_duration) * 100
                        record.attendance_percentage = min(percentage, 100.0)  # لا تتجاوز 100%
                    else:
                        record.attendance_percentage = 0.0
                else:
                    # إذا لم يبدأ الاجتماع بعد
                    record.attendance_percentage = 0.0
            else:
                # للحضور الحضوري، النسبة 100% إذا كان حاضر
                record.attendance_percentage = 100.0 if record.status == 'present' else 0.0

    def action_join_online(self):
        """تسجيل دخول الطالب للاجتماع الأونلاين"""
        self.ensure_one()

        # التحقق من أن الجلسة أونلاين
        if self.session_id.class_session_type != 'Online':
            raise ValidationError(_('هذه الجلسة ليست جلسة أونلاين'))

        # تسجيل وقت الدخول
        self.write({
            'online_join_time': datetime.now(),
            'is_online_now': True,
            'status': 'present',
            'online_join_count': self.online_join_count + 1,
            'attendance_type': 'online'  # التأكد من نوع الحضور
        })

        # فرض إعادة حساب الحقول المحسوبة
        self._compute_online_duration()
        self._compute_attendance_percentage()

        return True

    def action_leave_online(self):
        """تسجيل خروج الطالب من الاجتماع الأونلاين"""
        self.ensure_one()

        if not self.is_online_now:
            return True

        # تسجيل وقت الخروج
        leave_time = datetime.now()
        self.write({
            'online_leave_time': leave_time,
            'is_online_now': False,
        })

        # فرض إعادة حساب الحقول المحسوبة
        self._compute_online_duration()
        self._compute_attendance_percentage()

        # تحديث الحالة بناءً على نسبة الحضور
        if self.attendance_percentage >= 80:
            self.status = 'present'
        elif self.attendance_percentage >= 50:
            self.status = 'late'
        else:
            self.status = 'absent'

        return True

    # ============ نهاية دوال الحضور الأونلاين ============

    def mark_present(self):
        self.ensure_one()
        self.status = 'present'
        return True

    def mark_absent(self):
        self.ensure_one()
        self.status = 'absent'
        return True

    @api.constrains('verse_from', 'verse_to')
    def _check_verses(self):
        for record in self:
            if record.verse_from and record.verse_to:
                if record.verse_from < 1:
                    raise ValidationError(_('رقم الآية يجب أن يكون أكبر من صفر'))
                if record.verse_to < record.verse_from:
                    raise ValidationError(_('آية النهاية يجب أن تكون بعد آية البداية'))

            if record.revision_verse_from and record.revision_verse_to:
                if record.revision_verse_from < 1:
                    raise ValidationError(_('رقم آية المراجعة يجب أن يكون أكبر من صفر'))
                if record.revision_verse_to < record.revision_verse_from:
                    raise ValidationError(_('آية نهاية المراجعة يجب أن تكون بعد آية البداية'))