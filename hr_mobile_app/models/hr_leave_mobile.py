# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    # إضافة حقول التطبيق المحمول مع migration آمن
    mobile_visible = fields.Boolean(
        string="مرئي في التطبيق المحمول",
        default=True,
        help="يحدد ما إذا كان نوع الإجازة مرئياً في التطبيق المحمول"
    )

    mobile_icon = fields.Char(
        string="أيقونة التطبيق",
        default="📅",
        help="أيقونة تظهر في التطبيق المحمول"
    )

    mobile_description = fields.Text(
        string="وصف للتطبيق المحمول",
        help="وصف مختصر يظهر في التطبيق المحمول"
    )

    max_days_mobile = fields.Integer(
        string="الحد الأقصى للأيام (التطبيق)",
        default=30,
        help="الحد الأقصى لعدد الأيام التي يمكن طلبها من التطبيق المحمول"
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


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    # إضافة حقول جديدة لدعم التطبيق المحمول
    mobile_created = fields.Boolean(
        string="تم الإنشاء من التطبيق",
        default=False,
        help="يشير إلى ما إذا كان طلب الإجازة قد تم إنشاؤه من التطبيق المحمول"
    )

    mobile_request_date = fields.Datetime(
        string="تاريخ الطلب من التطبيق",
        help="تاريخ ووقت إنشاء الطلب من التطبيق المحمول"
    )

    mobile_location = fields.Char(
        string="موقع الطلب",
        help="الموقع الجغرافي عند إنشاء الطلب من التطبيق"
    )

    rejection_reason = fields.Text(
        string="سبب الرفض",
        help="سبب رفض طلب الإجازة من قبل المدير"
    )

    approval_notes = fields.Text(
        string="ملاحظات الموافقة",
        help="ملاحظات إضافية من المدير عند الموافقة"
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