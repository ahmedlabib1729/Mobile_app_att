# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import qrcode
import base64
from io import BytesIO


class Membership(models.Model):
    _name = 'club.membership'
    _description = 'العضويات'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'membership_number'
    _order = 'create_date desc'

    # معلومات أساسية
    membership_number = fields.Char(
        string='رقم العضوية',
        required=True,
        copy=False,
        readonly=True,
        default='New'
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='العضو',
        required=True,
        tracking=True,
        domain=[('is_company', '=', False)]
    )

    membership_type_id = fields.Many2one(
        'club.membership.type',
        string='نوع العضوية',
        required=True,
        tracking=True
    )

    # التواريخ
    start_date = fields.Date(
        string='تاريخ البداية',
        required=True,
        default=fields.Date.today,
        tracking=True
    )

    end_date = fields.Date(
        string='تاريخ الانتهاء',
        compute='_compute_end_date',
        store=True,
        tracking=True
    )

    join_date = fields.Date(
        string='تاريخ الانضمام الأول',
        default=fields.Date.today,
        help="تاريخ أول انضمام للنادي"
    )

    # الحالة
    state = fields.Selection([
        ('draft', 'مسودة'),
        ('active', 'نشط'),
        ('expired', 'منتهي'),
        ('frozen', 'مجمد'),
        ('cancelled', 'ملغي')
    ], string='الحالة', default='draft', tracking=True)

    # التجميد
    is_frozen = fields.Boolean(
        string='مجمد',
        default=False,
        tracking=True
    )

    freeze_start_date = fields.Date(
        string='تاريخ بداية التجميد'
    )

    freeze_end_date = fields.Date(
        string='تاريخ نهاية التجميد'
    )

    freeze_reason = fields.Text(
        string='سبب التجميد'
    )

    total_freeze_days = fields.Integer(
        string='إجمالي أيام التجميد',
        compute='_compute_freeze_days',
        store=True
    )

    # المالية
    price = fields.Float(
        string='السعر',
        related='membership_type_id.price',
        store=True
    )

    discount_amount = fields.Float(
        string='مبلغ الخصم',
        default=0.0
    )

    final_price = fields.Float(
        string='السعر النهائي',
        compute='_compute_final_price',
        store=True
    )

    payment_state = fields.Selection([
        ('not_paid', 'غير مدفوع'),
        ('partial', 'مدفوع جزئياً'),
        ('paid', 'مدفوع')
    ], string='حالة الدفع', default='not_paid', tracking=True)

    # بطاقة العضوية
    card_number = fields.Char(
        string='رقم البطاقة',
        copy=False
    )

    qr_code = fields.Binary(
        string='QR Code',
        compute='_compute_qr_code'
    )

    # التجديد
    is_renewal = fields.Boolean(
        string='تجديد',
        default=False
    )

    parent_membership_id = fields.Many2one(
        'club.membership',
        string='العضوية السابقة'
    )

    renewal_count = fields.Integer(
        string='عدد مرات التجديد',
        compute='_compute_renewal_count',
        store=True
    )

    # العائلة
    family_head_id = fields.Many2one(
        'res.partner',
        string='رب الأسرة',
        domain=[('is_company', '=', False)]
    )

    is_family_member = fields.Boolean(
        string='عضو عائلة',
        default=False
    )

    # معلومات إضافية
    notes = fields.Text(
        string='ملاحظات'
    )

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        default=lambda self: self.env.company
    )

    @api.model
    def create(self, vals):
        if vals.get('membership_number', 'New') == 'New':
            vals['membership_number'] = self.env['ir.sequence'].next_by_code('club.membership') or 'New'

        # إذا كان تجديد، ربطه بالعضوية السابقة
        if vals.get('partner_id') and not vals.get('parent_membership_id'):
            last_membership = self.search([
                ('partner_id', '=', vals['partner_id']),
                ('state', 'in', ['active', 'expired'])
            ], limit=1, order='end_date desc')

            if last_membership:
                vals['is_renewal'] = True
                vals['parent_membership_id'] = last_membership.id
                vals['join_date'] = last_membership.join_date

        return super(Membership, self).create(vals)

    @api.depends('membership_type_id', 'start_date')
    def _compute_end_date(self):
        for record in self:
            if record.membership_type_id and record.start_date:
                duration_type = record.membership_type_id.duration_type
                duration_value = record.membership_type_id.duration_value

                if duration_type == 'days':
                    record.end_date = record.start_date + timedelta(days=duration_value)
                elif duration_type == 'months':
                    record.end_date = record.start_date + timedelta(days=duration_value * 30)
                elif duration_type == 'years':
                    record.end_date = record.start_date + timedelta(days=duration_value * 365)
            else:
                record.end_date = False

    @api.depends('price', 'discount_amount')
    def _compute_final_price(self):
        for record in self:
            record.final_price = record.price - record.discount_amount

    @api.depends('freeze_start_date', 'freeze_end_date')
    def _compute_freeze_days(self):
        for record in self:
            if record.freeze_start_date and record.freeze_end_date:
                delta = record.freeze_end_date - record.freeze_start_date
                record.total_freeze_days = delta.days
            else:
                record.total_freeze_days = 0

    @api.depends('parent_membership_id')
    def _compute_renewal_count(self):
        for record in self:
            count = 0
            current = record
            while current.parent_membership_id:
                count += 1
                current = current.parent_membership_id
            record.renewal_count = count

    def _compute_qr_code(self):
        for record in self:
            if record.membership_number:
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(record.membership_number)
                qr.make(fit=True)
                img = qr.make_image(fill='black', back_color='white')
                buffer = BytesIO()
                img.save(buffer, format='PNG')
                img_str = base64.b64encode(buffer.getvalue())
                record.qr_code = img_str
            else:
                record.qr_code = False

    def action_activate(self):
        """تفعيل العضوية"""
        for record in self:
            if record.payment_state != 'paid':
                raise UserError("لا يمكن تفعيل العضوية قبل اكتمال الدفع!")

            record.state = 'active'

            # إنشاء بطاقة العضوية
            if not record.card_number:
                record.card_number = self.env['ir.sequence'].next_by_code('club.card') or 'New'

    def action_freeze(self):
        """تجميد العضوية"""
        for record in self:
            if record.state != 'active':
                raise UserError("يمكن تجميد العضويات النشطة فقط!")

            # التحقق من الحد الأقصى لأيام التجميد
            max_days = record.membership_type_id.max_freeze_days
            if record.total_freeze_days >= max_days:
                raise UserError(f"تجاوزت الحد الأقصى لأيام التجميد ({max_days} يوم)")

            record.state = 'frozen'
            record.is_frozen = True

    def action_unfreeze(self):
        """إلغاء تجميد العضوية"""
        for record in self:
            if record.state != 'frozen':
                raise UserError("العضوية غير مجمدة!")

            record.state = 'active'
            record.is_frozen = False

            # تمديد تاريخ الانتهاء بعدد أيام التجميد
            if record.freeze_start_date and record.freeze_end_date:
                freeze_days = (record.freeze_end_date - record.freeze_start_date).days
                record.end_date = record.end_date + timedelta(days=freeze_days)

    def action_cancel(self):
        """إلغاء العضوية"""
        for record in self:
            if record.state == 'cancelled':
                raise UserError("العضوية ملغاة بالفعل!")
            record.state = 'cancelled'

    def action_renew(self):
        """تجديد العضوية"""
        for record in self:
            if record.state not in ['active', 'expired']:
                raise UserError("يمكن تجديد العضويات النشطة أو المنتهية فقط!")

            # إنشاء عضوية جديدة
            new_membership = record.copy({
                'start_date': record.end_date + timedelta(days=1),
                'state': 'draft',
                'is_renewal': True,
                'parent_membership_id': record.id,
                'payment_state': 'not_paid',
                'membership_number': 'New'
            })

            # تطبيق خصم التجديد المبكر
            if record.state == 'active' and record.membership_type_id.discount_percentage > 0:
                discount = record.price * (record.membership_type_id.discount_percentage / 100)
                new_membership.discount_amount = discount

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'club.membership',
                'view_mode': 'form',
                'res_id': new_membership.id,
                'target': 'current'
            }

    def action_view_history(self):
        """عرض سجل التجديدات"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'سجل العضويات',
            'res_model': 'club.membership',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.partner_id.id)],
            'context': {'search_default_partner_id': self.partner_id.id}
        }
        """وظيفة مجدولة للتحقق من انتهاء العضويات"""
        today = fields.Date.today()

        # تحديث العضويات المنتهية
        expired_memberships = self.search([
            ('state', '=', 'active'),
            ('end_date', '<', today)
        ])
        expired_memberships.write({'state': 'expired'})

        # إرسال تذكير التجديد
        for membership_type in self.env['club.membership.type'].search([]):
            reminder_date = today + timedelta(days=membership_type.renewal_reminder_days)

            memberships_to_remind = self.search([
                ('state', '=', 'active'),
                ('membership_type_id', '=', membership_type.id),
                ('end_date', '=', reminder_date)
            ])

            for membership in memberships_to_remind:
                # إرسال تذكير بالبريد الإلكتروني أو الرسائل
                pass