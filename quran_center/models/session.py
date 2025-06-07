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


    class_session_type = fields.Selection([
        ('offline', 'حضورى'),
        ('Online', 'أون لاين')
    ], string='نوع الصف', required=True , related='class_id.class_session_type', store=True)

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
        ('scheduled', 'مجدولة'),
        ('ongoing', 'جارية'),
        ('completed', 'منتهية'),
        ('cancelled', 'ملغاة')
    ], string='الحالة', default='scheduled', tracking=True)

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

    @api.depends('attendance_line_ids.status')
    def _compute_attendance_stats(self):
        for record in self:
            attendance_lines = record.attendance_line_ids
            record.present_count = len(attendance_lines.filtered(lambda a: a.status == 'present'))
            record.absent_count = len(attendance_lines.filtered(lambda a: a.status == 'absent'))
            total = len(attendance_lines)
            record.attendance_rate = (record.present_count / total * 100) if total > 0 else 0

    @api.constrains('start_datetime', 'end_datetime')
    def _check_datetime_validity(self):
        for record in self:
            if record.end_datetime <= record.start_datetime:
                raise ValidationError(_('وقت النهاية يجب أن يكون بعد وقت البداية'))

    @api.model
    def create(self, vals):
        session = super().create(vals)
        # Create attendance lines for all enrolled students
        session._create_attendance_lines()
        return session

    def _create_attendance_lines(self):
        """Create attendance lines for all enrolled students"""
        for session in self:
            existing_students = session.attendance_line_ids.mapped('student_id')
            for student in session.enrolled_student_ids:
                if student not in existing_students:
                    self.env['quran.session.attendance'].create({
                        'session_id': session.id,
                        'student_id': student.id,
                        'status': 'absent'  # Default to absent
                    })

    def action_start(self):
        self.state = 'ongoing'

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

    _sql_constraints = [
        ('unique_student_session', 'UNIQUE(session_id, student_id)',
         'الطالب مسجل مسبقاً في هذه الجلسة!')
    ]

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