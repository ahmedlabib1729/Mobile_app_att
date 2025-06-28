# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import hashlib
import secrets
import base64
import re
import logging

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Mobile app fields
    mobile_username = fields.Char(
        string="Mobile App Username",
        help="This employee's username for mobile app login",
        copy=False,
    )
    mobile_pin = fields.Char(
        string="Mobile App PIN",
        help="PIN code for employee verification in the mobile app (4-6 digits)",
        copy=False,
        groups="hr.group_hr_user",
    )
    mobile_pin_hash = fields.Char(
        string="Encrypted PIN",
        help="Store the PIN in encrypted format",
        copy=False,
        groups="hr.group_hr_user",
    )
    mobile_salt = fields.Char(
        string="Encryption Salt",
        help="Random value used for PIN encryption",
        copy=False,
        groups="hr.group_hr_user",
    )
    allow_mobile_access = fields.Boolean(
        string="Allow Mobile Access",
        default=False,
        help="Enable this employee's access from the mobile app",
    )
    mobile_last_login = fields.Datetime(
        string="Last Mobile Login",
        readonly=True,
        copy=False,
    )
    mobile_login_count = fields.Integer(
        string="Mobile Login Count",
        default=0,
        readonly=True,
        copy=False,
    )

    office_location_id = fields.Many2one(
        'hr.office.location',
        string='موقع المكتب',
        help="الموقع الجغرافي المخصص لهذا الموظف",
        tracking=True
    )

    allow_remote_attendance = fields.Boolean(
        string='السماح بالحضور عن بُعد',
        default=False,
        help="السماح لهذا الموظف بتسجيل الحضور من أي مكان",
        tracking=True
    )

    temporary_location_ids = fields.One2many(
        'hr.employee.temp.location',
        'employee_id',
        string='المواقع المؤقتة',
        help="مواقع مؤقتة مسموح للموظف بالحضور منها"
    )
    _sql_constraints = [
        ('mobile_username_unique', 'UNIQUE(mobile_username)', 'Mobile app username must be unique!')
    ]

    @api.constrains('mobile_pin')
    def _check_mobile_pin(self):
        """Check the validity of the PIN"""
        for record in self:
            if record.mobile_pin and record.mobile_pin != '******':
                # Check PIN is digits only and length between 4-6
                if not re.match(r'^\d{4,6}$', record.mobile_pin):
                    raise ValidationError(_('PIN must be 4-6 digits only'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('mobile_pin') and vals['mobile_pin'] != '******':
                # Temporarily store original PIN
                original_pin = vals['mobile_pin']

                # Generate random salt and encrypt PIN
                salt = secrets.token_hex(8)
                vals['mobile_salt'] = salt
                vals['mobile_pin_hash'] = self._hash_pin(original_pin, salt)
        return super(HrEmployee, self).create(vals_list)

    def write(self, vals):
        """Update employee record and encrypt PIN if changed"""
        if vals.get('mobile_pin') and vals['mobile_pin'] != '******':
            # Temporarily store original PIN
            original_pin = vals['mobile_pin']

            # Generate new salt and encrypt PIN
            salt = secrets.token_hex(8)
            vals['mobile_salt'] = salt
            vals['mobile_pin_hash'] = self._hash_pin(original_pin, salt)

        return super(HrEmployee, self).write(vals)

    def _hash_pin(self, pin, salt):
        """Encrypt PIN using PBKDF2 with SHA-256"""
        # Use many iterations for better security
        iterations = 100000

        # Use PBKDF2 to hash the password with salt
        dk = hashlib.pbkdf2_hmac('sha256', pin.encode(), salt.encode(), iterations)

        # Convert result to base64 string for storage
        return base64.b64encode(dk).decode()

    def verify_pin(self, pin):
        """Verify the entered PIN"""
        self.ensure_one()

        # Log for debugging
        _logger.info("Verifying PIN for employee: %s (ID: %s)", self.name, self.id)
        _logger.info("Mobile access allowed: %s", self.allow_mobile_access)
        _logger.info("PIN hash exists: %s", bool(self.mobile_pin_hash))
        _logger.info("Salt exists: %s", bool(self.mobile_salt))

        if not self.mobile_pin_hash or not self.mobile_salt:
            _logger.warning("Missing PIN hash or salt for employee: %s", self.name)
            return False

        # Compute hash to compare with stored value
        hashed_pin = self._hash_pin(pin, self.mobile_salt)

        # Compare calculated and stored value
        result = (self.mobile_pin_hash == hashed_pin)

        _logger.info("PIN verification result: %s", result)

        # Log successful login
        if result:
            self.write({
                'mobile_last_login': fields.Datetime.now(),
                'mobile_login_count': self.mobile_login_count + 1,
            })

        return result

    def reset_mobile_pin(self):
        """Reset PIN from the field value"""
        # Check if PIN is entered in the field
        if not self.mobile_pin or self.mobile_pin == '******':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Please enter the PIN in the "Mobile App PIN" field first'),
                    'sticky': False,
                    'type': 'danger',
                }
            }

        # Use PIN from the field
        new_pin = self.mobile_pin

        # Generate salt and hash
        salt = secrets.token_hex(8)
        pin_hash = self._hash_pin(new_pin, salt)

        # Update database directly
        self.env.cr.execute("""
            UPDATE hr_employee 
            SET mobile_salt = %s, mobile_pin_hash = %s 
            WHERE id = %s
        """, (salt, pin_hash, self.id))

        # Update memory values
        self.mobile_salt = salt
        self.mobile_pin_hash = pin_hash

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('PIN Reset'),
                'message': _('PIN has been set successfully'),
                'sticky': False,
                'type': 'success',
            }
        }

    def toggle_mobile_access(self):
        """Enable/Disable mobile app access for employee"""
        for record in self:
            record.allow_mobile_access = not record.allow_mobile_access

        return True

    def generate_demo_credentials(self):
        """Generate credentials based on entered data"""
        if not self.mobile_username:
            # Generate username from email or name
            if self.work_email:
                username = self.work_email.split('@')[0]
            else:
                username = self.name.lower().replace(' ', '.')

            # Ensure username is unique
            base_username = username
            counter = 1
            while self.env['hr.employee'].search_count([('mobile_username', '=', username)]) > 0:
                username = f"{base_username}{counter}"
                counter += 1

            self.mobile_username = username

        # Check if PIN is entered in the field
        if not self.mobile_pin or self.mobile_pin == '******':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Please enter the PIN in the "Mobile App PIN" field first'),
                    'sticky': False,
                    'type': 'danger',
                }
            }

        # Use PIN from the field
        new_pin = self.mobile_pin

        # Generate salt and hash PIN directly
        salt = secrets.token_hex(8)
        pin_hash = self._hash_pin(new_pin, salt)

        # Save data directly
        self.env.cr.execute("""
            UPDATE hr_employee 
            SET mobile_salt = %s, mobile_pin_hash = %s, allow_mobile_access = TRUE 
            WHERE id = %s
        """, (salt, pin_hash, self.id))

        # Update memory
        self.mobile_salt = salt
        self.mobile_pin_hash = pin_hash
        self.allow_mobile_access = True

        # Verify encryption and storage
        verification_result = self.verify_pin(new_pin)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Credentials Generated'),
                'message': _('''
                Username: %s
                PIN set successfully
                PIN verification result: %s
                ''') % (self.mobile_username, verification_result),
                'sticky': True,
                'type': 'success',
            }
        }

    @api.model
    def get_employee_by_username(self, username):
        """Find employee by username"""
        employee = self.search([
            ('mobile_username', '=', username),
            ('allow_mobile_access', '=', True),
        ], limit=1)

        return employee if employee else False

    def set_test_pin(self):
        """Set PIN from the field"""
        # Check if PIN is entered in the field
        if not self.mobile_pin or self.mobile_pin == '******':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Please enter the PIN in the "Mobile App PIN" field first'),
                    'sticky': False,
                    'type': 'danger',
                }
            }

        test_pin = self.mobile_pin  # Use PIN from the field

        # Generate new salt
        salt = secrets.token_hex(8)

        # Store real values
        self.write({
            'mobile_salt': salt,
            'mobile_pin_hash': self._hash_pin(test_pin, salt),
            'allow_mobile_access': True,
        })

        # Display values for verification
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('PIN Set'),
                'message': _('''
                Username: %s
                PIN set successfully
                ''') % (self.mobile_username),
                'sticky': True,
                'type': 'success',
            }
        }

    # في ملف hr_mobile_app/models/hr_employee.py
    # استبدل دالة verify_employee_credentials بهذه النسخة المحدثة:

    @api.model
    def verify_employee_credentials(self, username, pin):
        """Verify employee credentials"""
        # Log for debugging
        _logger.info("Verifying credentials for user: %s", username)

        # Log all employees for debugging
        all_employees = self.search_read([], ['name', 'mobile_username', 'allow_mobile_access'])
        _logger.info("All employees in system: %s", all_employees)

        # Find employee by username
        employee = self.search([
            ('mobile_username', '=', username),
            ('allow_mobile_access', '=', True),
        ], limit=1)

        if not employee:
            _logger.warning("No employee found with username: %s", username)
            return {'success': False, 'error': 'Employee not found or access denied'}

        _logger.info("Employee found: %s (ID: %s), More info: %s",
                     employee.name, employee.id,
                     employee.read(['mobile_username', 'allow_mobile_access', 'mobile_pin_hash', 'mobile_salt']))

        # Verify PIN
        _logger.info("Attempting to verify PIN for employee: %s", employee.name)
        verification_result = employee.verify_pin(pin)
        _logger.info("PIN verification result: %s", verification_result)

        if verification_result:
            _logger.info("PIN verified successfully for employee: %s", employee.name)

            # جلب صورة الموظف
            avatar_128 = None
            image_1920 = None

            # قراءة الصورة بشكل صحيح من Odoo
            if employee.avatar_128:
                avatar_128 = employee.avatar_128.decode('utf-8') if isinstance(employee.avatar_128,
                                                                               bytes) else employee.avatar_128
            if employee.image_1920:
                image_1920 = employee.image_1920.decode('utf-8') if isinstance(employee.image_1920,
                                                                               bytes) else employee.image_1920

            return {
                'success': True,
                'employee': {
                    'id': employee.id,
                    'name': employee.name,
                    'job_title': employee.job_title or False,
                    'department': employee.department_id.name if employee.department_id else False,
                    'work_email': employee.work_email or False,
                    'work_phone': employee.work_phone or False,
                    # إضافة بيانات الصورة
                    'avatar_128': avatar_128,
                    'image_1920': image_1920,
                }
            }
        else:
            _logger.warning("PIN verification failed for employee: %s", employee.name)
            return {'success': False, 'error': 'Invalid PIN'}