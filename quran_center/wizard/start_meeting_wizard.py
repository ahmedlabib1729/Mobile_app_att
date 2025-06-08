# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class StartMeetingWizard(models.TransientModel):
    _name = 'quran.session.start.meeting.wizard'
    _description = 'Start Online Meeting Wizard'

    session_id = fields.Many2one(
        'quran.session',
        string='الجلسة',
        required=True,
        readonly=True
    )

    # معلومات الجلسة
    session_name = fields.Char(
        related='session_id.name',
        string='اسم الجلسة',
        readonly=True
    )

    class_name = fields.Char(
        related='session_id.class_id.name',
        string='الصف',
        readonly=True
    )

    scheduled_time = fields.Datetime(
        related='session_id.start_datetime',
        string='الموعد المحدد',
        readonly=True
    )

    student_count = fields.Integer(
        string='عدد الطلاب',
        compute='_compute_counts'
    )

    # إعدادات الاجتماع
    meeting_name = fields.Char(
        string='اسم الاجتماع',
        required=True,
        default=lambda self: self._default_meeting_name()
    )

    meeting_description = fields.Text(
        string='وصف الاجتماع',
        help='وصف اختياري للاجتماع'
    )

    # إعدادات الصوت والفيديو
    allow_student_camera = fields.Boolean(
        string='السماح بكاميرا الطلاب',
        default=True
    )

    allow_student_mic = fields.Boolean(
        string='السماح بمايك الطلاب',
        default=True
    )

    mute_on_join = fields.Boolean(
        string='كتم الصوت عند الدخول',
        default=True,
        help='كتم صوت الطلاب تلقائياً عند دخولهم الاجتماع'
    )

    # إعدادات التسجيل
    auto_record_meeting = fields.Boolean(
        string='تسجيل الجلسة',
        default=False
    )

    record_type = fields.Selection([
        ('audio', 'صوت فقط'),
        ('video', 'صوت وفيديو'),
        ('screen', 'شاشة وصوت')
    ], string='نوع التسجيل', default='video')

    # إعدادات الأمان
    require_permission = fields.Boolean(
        string='طلب إذن للدخول',
        default=False,
        help='يحتاج الطلاب لموافقة المعلم للدخول'
    )

    enable_waiting_room = fields.Boolean(
        string='تفعيل غرفة الانتظار',
        default=False
    )

    # إعدادات المشاركة
    allow_screen_share = fields.Boolean(
        string='السماح بمشاركة الشاشة للطلاب',
        default=False
    )

    allow_chat = fields.Boolean(
        string='السماح بالدردشة النصية',
        default=True
    )

    allow_reactions = fields.Boolean(
        string='السماح بالتفاعلات (رفع اليد، إيموجي)',
        default=True
    )

    # إشعارات
    send_email_invitation = fields.Boolean(
        string='إرسال دعوات بالبريد الإلكتروني',
        default=True
    )

    send_sms_reminder = fields.Boolean(
        string='إرسال تذكير SMS',
        default=False
    )

    # معلومات إضافية
    special_instructions = fields.Text(
        string='تعليمات خاصة',
        placeholder='مثال: يرجى تحضير المصحف، سيكون هناك اختبار قصير، إلخ...'
    )

    @api.model
    def _default_meeting_name(self):
        if self._context.get('default_session_id'):
            session = self.env['quran.session'].browse(self._context['default_session_id'])
            return f"{session.name} - اجتماع أونلاين"
        return "اجتماع أونلاين"

    @api.depends('session_id')
    def _compute_counts(self):
        for wizard in self:
            wizard.student_count = len(wizard.session_id.enrolled_student_ids)

    @api.onchange('session_id')
    def _onchange_session_id(self):
        if self.session_id:
            # استخدم الإعدادات الافتراضية من الجلسة
            self.allow_student_camera = self.session_id.allow_student_camera
            self.allow_student_mic = self.session_id.allow_student_mic
            self.auto_record_meeting = self.session_id.auto_record_meeting

    def action_start_meeting(self):
        """بدء الاجتماع مع الإعدادات المحددة"""
        self.ensure_one()

        if not self.session_id.can_start_meeting:
            raise ValidationError(_('لا يمكن بدء الاجتماع في الوقت الحالي'))

        # تحديث إعدادات الجلسة
        self.session_id.write({
            'allow_student_camera': self.allow_student_camera,
            'allow_student_mic': self.allow_student_mic,
            'auto_record_meeting': self.auto_record_meeting,
        })

        # إنشاء القناة مع الإعدادات المتقدمة
        channel = self._create_meeting_channel()

        # إرسال الإشعارات إذا لزم الأمر
        if self.send_email_invitation:
            self._send_email_invitations(channel)

        if self.send_sms_reminder:
            self._send_sms_reminders(channel)

        # بدء الاجتماع
        self.session_id.action_start_meeting_direct()

        # فتح نافذة الاجتماع
        return {
            'type': 'ir.actions.act_url',
            'url': self.session_id.meeting_url,
            'target': 'new',
        }

    def _create_meeting_channel(self):
        """إنشاء قناة الاجتماع مع الإعدادات المتقدمة"""
        # إنشاء معرف فريد للاجتماع
        meeting_id = self.env['ir.sequence'].next_by_code('quran.session.meeting') or \
                     f"QRN-{self.session_id.id}-{fields.Datetime.now().strftime('%Y%m%d%H%M')}"

        # تحضير بيانات القناة - تم إزالة حقل public
        channel_vals = {
            'name': self.meeting_name,
            'channel_type': 'channel',
            'description': self.meeting_description or f'اجتماع أونلاين للجلسة: {self.session_name}',
        }

        # إنشاء القناة
        channel = self.env['discuss.channel'].create(channel_vals)

        # إضافة المعلمين كمشرفين
        moderator_partners = []
        if self.session_id.teacher_id and self.session_id.teacher_id.user_id:
            moderator_partners.append(self.session_id.teacher_id.user_id.partner_id.id)
        if self.session_id.teacher_id2 and self.session_id.teacher_id2.user_id:
            moderator_partners.append(self.session_id.teacher_id2.user_id.partner_id.id)

        # إضافة الطلاب
        student_partners = []
        for student in self.session_id.enrolled_student_ids:
            if student.user_id:
                student_partners.append(student.user_id.partner_id.id)

        # إضافة الأعضاء للقناة
        all_partners = moderator_partners + student_partners
        if all_partners:
            channel.write({
                'channel_partner_ids': [(4, partner_id) for partner_id in all_partners]
            })

        # تحديث معلومات الاجتماع في الجلسة
        self.session_id.write({
            'meeting_channel_id': channel.id,
            'meeting_id': meeting_id,
            'meeting_url': f'/discuss/channel/{channel.id}',
        })

        # إضافة رسالة ترحيب مع التعليمات
        welcome_message = self._prepare_welcome_message()
        channel.message_post(
            body=welcome_message,
            message_type='comment',
            subtype_xmlid='mail.mt_comment'
        )

        return channel

    def _prepare_welcome_message(self):
        """إعداد رسالة الترحيب في الاجتماع"""
        message = f"""
        <div style="direction: rtl; text-align: right;">
            <h3>🌟 أهلاً وسهلاً في {self.meeting_name}</h3>
            <p><strong>الصف:</strong> {self.class_name}</p>
            <p><strong>المعلم:</strong> {self.session_id.teacher_id.name}</p>
        """

        if self.session_id.teacher_id2:
            message += f"<p><strong>المعلم المساعد:</strong> {self.session_id.teacher_id2.name}</p>"

        message += "<hr/><h4>📋 قواعد الاجتماع:</h4><ul>"

        if not self.allow_student_camera:
            message += "<li>❌ الكاميرا مغلقة للطلاب</li>"
        else:
            message += "<li>✅ يمكن للطلاب تشغيل الكاميرا</li>"

        if not self.allow_student_mic:
            message += "<li>❌ المايك مغلق للطلاب</li>"
        elif self.mute_on_join:
            message += "<li>🔇 المايك مكتوم عند الدخول (يمكن فتحه بإذن المعلم)</li>"
        else:
            message += "<li>✅ يمكن للطلاب استخدام المايك</li>"

        if self.allow_chat:
            message += "<li>💬 الدردشة النصية متاحة</li>"

        if self.allow_reactions:
            message += "<li>👋 يمكن رفع اليد واستخدام التفاعلات</li>"

        if self.auto_record_meeting:
            message += "<li>🔴 يتم تسجيل هذه الجلسة</li>"

        message += "</ul>"

        if self.special_instructions:
            message += f"""
            <hr/>
            <h4>📌 تعليمات خاصة:</h4>
            <p>{self.special_instructions}</p>
            """

        message += """
            <hr/>
            <p><em>بالتوفيق للجميع، أعانكم الله على حفظ كتابه الكريم 🤲</em></p>
        </div>
        """

        return message

    def _send_email_invitations(self, channel):
        """إرسال دعوات البريد الإلكتروني"""
        template = self.env.ref('quran_center.email_template_meeting_invitation', raise_if_not_found=False)

        if not template:
            # إنشاء رسالة بسيطة إذا لم يوجد قالب
            for student in self.session_id.enrolled_student_ids.filtered('email'):
                mail_values = {
                    'subject': f'دعوة لحضور {self.meeting_name}',
                    'body_html': f"""
                        <p>عزيزي الطالب {student.name_ar}،</p>
                        <p>ندعوك لحضور الاجتماع الأونلاين:</p>
                        <ul>
                            <li><strong>الجلسة:</strong> {self.session_name}</li>
                            <li><strong>الموعد:</strong> {self.scheduled_time}</li>
                            <li><strong>الرابط:</strong> <a href="{self.env['ir.config_parameter'].sudo().get_param('web.base.url')}{self.session_id.meeting_url}">انقر هنا للدخول</a></li>
                        </ul>
                        <p>وفقك الله</p>
                    """,
                    'email_to': student.email,
                    'email_from': self.env.company.email or 'noreply@quran-center.com',
                }
                self.env['mail.mail'].create(mail_values).send()
        else:
            # استخدام القالب إذا وجد
            for student in self.session_id.enrolled_student_ids.filtered('email'):
                template.send_mail(self.session_id.id, force_send=True, email_values={
                    'email_to': student.email
                })

    def _send_sms_reminders(self, channel):
        """إرسال تذكيرات SMS"""
        # يمكن تطبيق هذا لاحقاً حسب خدمة SMS المتاحة
        pass