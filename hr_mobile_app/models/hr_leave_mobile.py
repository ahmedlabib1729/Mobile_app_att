# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    mobile_visible = fields.Boolean(
        string="Visible in Mobile App",
        default=True,
        help="Determines whether this leave type is visible in the mobile app"
    )

    mobile_icon = fields.Char(
        string="Mobile App Icon",
        default="📅",
        help="Icon displayed in the mobile app"
    )

    mobile_description = fields.Text(
        string="Mobile App Description",
        help="Short description shown in the mobile app"
    )

    max_days_mobile = fields.Integer(
        string="Max Days (Mobile App)",
        default=30,
        help="Maximum number of days that can be requested from the mobile app"
    )

    @api.model
    def _auto_init(self):
        """تهيئة تلقائية للحقول الجديدة"""
        # فحص وجود الحقول في قاعدة البيانات
        self._cr.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'hr_leave_type' 
            AND column_name IN ('mobile_visible', 'mobile_icon', 'mobile_description', 'max_days_mobile')
        """)

        existing_columns = [row[0] for row in self._cr.fetchall()]

        # إضافة الحقول المفقودة
        if 'mobile_visible' not in existing_columns:
            _logger.info("إضافة حقل mobile_visible...")
            self._cr.execute("""
                ALTER TABLE hr_leave_type 
                ADD COLUMN mobile_visible BOOLEAN DEFAULT TRUE
            """)

        if 'mobile_icon' not in existing_columns:
            _logger.info("إضافة حقل mobile_icon...")
            self._cr.execute("""
                ALTER TABLE hr_leave_type 
                ADD COLUMN mobile_icon VARCHAR DEFAULT '📅'
            """)

        if 'mobile_description' not in existing_columns:
            _logger.info("إضافة حقل mobile_description...")
            self._cr.execute("""
                ALTER TABLE hr_leave_type 
                ADD COLUMN mobile_description TEXT DEFAULT ''
            """)

        if 'max_days_mobile' not in existing_columns:
            _logger.info("إضافة حقل max_days_mobile...")
            self._cr.execute("""
                ALTER TABLE hr_leave_type 
                ADD COLUMN max_days_mobile INTEGER DEFAULT 30
            """)

        # استدعاء التهيئة الأساسية
        return super()._auto_init()

    @api.model
    def get_mobile_leave_types(self):
        """جلب أنواع الإجازات المتاحة للتطبيق المحمول"""
        leave_types = self.search([
            ('active', '=', True),
            ('mobile_visible', '=', True)
        ])

        types_data = []
        for leave_type in leave_types:
            types_data.append({
                'id': leave_type.id,
                'name': leave_type.name,
                'max_days': leave_type.max_days_mobile,
                'color': leave_type.color_name or '#2196F3',
                'icon': leave_type.mobile_icon,
                'description': leave_type.mobile_description or leave_type.name,
                'requires_approval': leave_type.leave_validation_type != 'no_validation',
            })

        return types_data

class HrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    @api.model
    def get_employee_allocations_summary(self, employee_id):
        """الحصول على ملخص تخصيصات الموظف"""
        try:
            employee = self.env['hr.employee'].browse(employee_id)
            if not employee.exists():
                return {'error': 'الموظف غير موجود'}

            # جلب جميع التخصيصات المعتمدة للموظف
            allocations = self.search([
                ('employee_id', '=', employee_id),
                ('state', '=', 'validate'),
            ])

            allocation_data = []
            for allocation in allocations:
                # حساب الأيام المستخدمة من هذا التخصيص
                used_leaves = self.env['hr.leave'].search([
                    ('employee_id', '=', employee_id),
                    ('holiday_status_id', '=', allocation.holiday_status_id.id),
                    ('state', '=', 'validate'),
                    ('date_from', '>=', allocation.date_from) if allocation.date_from else True,
                    ('date_to', '<=', allocation.date_to) if allocation.date_to else True,
                ])

                used_days = sum(used_leaves.mapped('number_of_days'))
                remaining_days = allocation.number_of_days - used_days

                allocation_data.append({
                    'id': allocation.id,
                    'leave_type_id': allocation.holiday_status_id.id,
                    'leave_type_name': allocation.holiday_status_id.name,
                    'allocated_days': allocation.number_of_days,
                    'used_days': used_days,
                    'remaining_days': max(0, remaining_days),
                    'valid_from': allocation.date_from.isoformat() if allocation.date_from else None,
                    'valid_to': allocation.date_to.isoformat() if allocation.date_to else None,
                    'color': getattr(allocation.holiday_status_id, 'color_name', '#2196F3') or '#2196F3',
                })

            return {
                'success': True,
                'allocations': allocation_data,
                'employee_name': employee.name,
            }

        except Exception as e:
            _logger.error("خطأ في جلب تخصيصات الموظف: %s", str(e))
            return {'error': str(e)}


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    mobile_created = fields.Boolean(
        string="Created from Mobile App",
        default=False,
        help="Indicates if the leave request was created from the mobile app"
    )

    mobile_request_date = fields.Datetime(
        string="Mobile Request Date",
        help="Date and time when the request was created from the mobile app"
    )

    mobile_location = fields.Char(
        string="Request Location",
        help="Geographical location when the request was created"
    )

    rejection_reason = fields.Text(
        string="Rejection Reason",
        help="Reason for rejecting the leave request by the manager"
    )

    approval_notes = fields.Text(
        string="Approval Notes",
        help="Additional notes from the manager upon approval"
    )

    @api.model
    def _auto_init(self):
        """تهيئة تلقائية للحقول الجديدة"""
        # فحص وجود الحقول في قاعدة البيانات
        self._cr.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'hr_leave' 
            AND column_name IN ('mobile_created', 'mobile_request_date', 'mobile_location', 'rejection_reason', 'approval_notes')
        """)

        existing_columns = [row[0] for row in self._cr.fetchall()]

        # إضافة الحقول المفقودة
        if 'mobile_created' not in existing_columns:
            _logger.info("إضافة حقل mobile_created...")
            self._cr.execute("""
                ALTER TABLE hr_leave 
                ADD COLUMN mobile_created BOOLEAN DEFAULT FALSE
            """)

        if 'mobile_request_date' not in existing_columns:
            _logger.info("إضافة حقل mobile_request_date...")
            self._cr.execute("""
                ALTER TABLE hr_leave 
                ADD COLUMN mobile_request_date TIMESTAMP
            """)

        if 'mobile_location' not in existing_columns:
            _logger.info("إضافة حقل mobile_location...")
            self._cr.execute("""
                ALTER TABLE hr_leave 
                ADD COLUMN mobile_location VARCHAR
            """)

        if 'rejection_reason' not in existing_columns:
            _logger.info("إضافة حقل rejection_reason...")
            self._cr.execute("""
                ALTER TABLE hr_leave 
                ADD COLUMN rejection_reason TEXT
            """)

        if 'approval_notes' not in existing_columns:
            _logger.info("إضافة حقل approval_notes...")
            self._cr.execute("""
                ALTER TABLE hr_leave 
                ADD COLUMN approval_notes TEXT
            """)

        # استدعاء التهيئة الأساسية
        return super()._auto_init()

    @api.model
    def get_employee_leave_summary(self, employee_id, year=None):
        """الحصول على ملخص إجازات الموظف للسنة المحددة"""
        try:
            if not year:
                year = fields.Date.today().year

            employee = self.env['hr.employee'].browse(employee_id)
            if not employee.exists():
                return {'error': 'الموظف غير موجود'}

            # تحديد نطاق التواريخ
            start_date = f'{year}-01-01'
            end_date = f'{year}-12-31'

            # جلب جميع الإجازات للسنة المحددة
            leaves = self.search([
                ('employee_id', '=', employee_id),
                ('date_from', '>=', start_date),
                ('date_to', '<=', end_date),
            ])

            # تجميع البيانات حسب النوع والحالة
            summary_by_type = {}
            summary_by_state = {
                'draft': 0,
                'confirm': 0,
                'validate': 0,
                'refuse': 0,
                'cancel': 0,
            }

            total_days_requested = 0
            total_days_approved = 0

            for leave in leaves:
                leave_type = leave.holiday_status_id.name

                # تجميع حسب النوع
                if leave_type not in summary_by_type:
                    summary_by_type[leave_type] = {
                        'type_id': leave.holiday_status_id.id,
                        'total_days': 0,
                        'approved_days': 0,
                        'pending_days': 0,
                        'rejected_days': 0,
                        'requests_count': 0,
                        'color': getattr(leave.holiday_status_id, 'color_name', '#2196F3') or '#2196F3',
                    }

                summary_by_type[leave_type]['total_days'] += leave.number_of_days
                summary_by_type[leave_type]['requests_count'] += 1

                if leave.state == 'validate':
                    summary_by_type[leave_type]['approved_days'] += leave.number_of_days
                    total_days_approved += leave.number_of_days
                elif leave.state in ['draft', 'confirm']:
                    summary_by_type[leave_type]['pending_days'] += leave.number_of_days
                elif leave.state == 'refuse':
                    summary_by_type[leave_type]['rejected_days'] += leave.number_of_days

                # تجميع حسب الحالة
                summary_by_state[leave.state] += leave.number_of_days
                total_days_requested += leave.number_of_days

            return {
                'success': True,
                'employee_id': employee_id,
                'employee_name': employee.name,
                'year': year,
                'total_requests': len(leaves),
                'total_days_requested': total_days_requested,
                'total_days_approved': total_days_approved,
                'summary_by_type': summary_by_type,
                'summary_by_state': summary_by_state,
            }

        except Exception as e:
            _logger.error("خطأ في جلب ملخص إجازات الموظف: %s", str(e))
            return {'error': str(e)}

    @api.model
    def check_leave_eligibility(self, employee_id, leave_type_id, date_from, date_to):
        """فحص أهلية الموظف لطلب الإجازة"""
        try:
            employee = self.env['hr.employee'].browse(employee_id)
            leave_type = self.env['hr.leave.type'].browse(leave_type_id)

            if not employee.exists() or not leave_type.exists():
                return {'eligible': False, 'reason': 'الموظف أو نوع الإجازة غير موجود'}

            # تحويل التواريخ
            date_from = fields.Date.from_string(date_from)
            date_to = fields.Date.from_string(date_to)

            if date_from >= date_to:
                return {'eligible': False, 'reason': 'تاريخ البداية يجب أن يكون قبل تاريخ النهاية'}

            # حساب عدد الأيام
            days_requested = (date_to - date_from).days + 1

            # فحص التداخل مع إجازات موجودة
            overlapping = self.search([
                ('employee_id', '=', employee_id),
                ('state', 'in', ['confirm', 'validate']),
                '|', '|',
                '&', ('date_from', '<=', date_from), ('date_to', '>=', date_from),
                '&', ('date_from', '<=', date_to), ('date_to', '>=', date_to),
                '&', ('date_from', '>=', date_from), ('date_to', '<=', date_to),
            ])

            if overlapping:
                return {'eligible': False, 'reason': 'يتداخل مع إجازة موجودة'}

            # فحص الرصيد المتاح إذا كان نوع الإجازة يتطلب تخصيص
            if leave_type.requires_allocation == 'yes':
                allocation = self.env['hr.leave.allocation'].search([
                    ('employee_id', '=', employee_id),
                    ('holiday_status_id', '=', leave_type_id),
                    ('state', '=', 'validate'),
                ], limit=1)

                if not allocation:
                    return {'eligible': False, 'reason': 'لا يوجد رصيد مخصص لهذا النوع من الإجازات'}

                # حساب الأيام المستخدمة
                used_days = sum(self.search([
                    ('employee_id', '=', employee_id),
                    ('holiday_status_id', '=', leave_type_id),
                    ('state', '=', 'validate'),
                ]).mapped('number_of_days'))

                remaining_days = allocation.number_of_days - used_days

                if remaining_days < days_requested:
                    return {
                        'eligible': False,
                        'reason': f'الرصيد المتاح ({remaining_days} يوم) أقل من المطلوب ({days_requested} يوم)'
                    }

            return {
                'eligible': True,
                'days_requested': days_requested,
                'message': 'يمكن تقديم طلب الإجازة'
            }

        except Exception as e:
            _logger.error("خطأ في فحص أهلية الإجازة: %s", str(e))
            return {'eligible': False, 'reason': str(e)}