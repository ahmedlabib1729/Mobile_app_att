from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import io
from datetime import datetime

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class ShipmentOrder(models.Model):
    _inherit = 'shipment.order'

    def action_export_to_excel(self):
        """Export selected records directly to Excel - الـ 16 عمود المطلوبين فقط"""

        if not xlsxwriter:
            raise UserError(_('Please install xlsxwriter library: pip install xlsxwriter'))

        if not self:
            raise UserError(_('Please select at least one shipment order to export!'))

        # إنشاء ملف Excel في الذاكرة
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Sheet1')

        # تنسيقات Excel
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#D3D3D3',
            'border': 1
        })

        cell_format = workbook.add_format({
            'align': 'left',
            'valign': 'vcenter',
            'border': 1
        })

        number_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })

        # الـ 16 عمود المطلوبين بالضبط
        headers = [
            'S.O.',  # 0
            'Goods type',  # 1
            'Goods name',  # 2
            'Quantity',  # 3
            'Weight',  # 4
            'COD',  # 5
            'Insure price',  # 6
            'Whether to allow the package to be opened',  # 7
            'Remark',  # 8
            'Name',  # 9 - اسم المستلم
            'Telephone',  # 10
            'City',  # 11
            'Area',  # 12
            'Receivers address',  # 13
            'Receiver Email',  # 14
            'Delivery Type'  # 15
        ]

        # كتابة الهيدر
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        # تحديد عرض الأعمدة
        worksheet.set_column('A:A', 15)  # S.O.
        worksheet.set_column('B:B', 15)  # Goods type
        worksheet.set_column('C:C', 25)  # Goods name
        worksheet.set_column('D:D', 10)  # Quantity
        worksheet.set_column('E:E', 10)  # Weight
        worksheet.set_column('F:F', 12)  # COD
        worksheet.set_column('G:G', 12)  # Insure price
        worksheet.set_column('H:H', 30)  # Whether to allow...
        worksheet.set_column('I:I', 30)  # Remark
        worksheet.set_column('J:J', 20)  # Name
        worksheet.set_column('K:K', 15)  # Telephone
        worksheet.set_column('L:L', 15)  # City
        worksheet.set_column('M:M', 15)  # Area
        worksheet.set_column('N:N', 35)  # Receivers address
        worksheet.set_column('O:O', 25)  # Receiver Email
        worksheet.set_column('P:P', 15)  # Delivery Type

        # كتابة البيانات
        row = 1
        for shipment in self:
            # S.O. - رقم الطلب
            worksheet.write(row, 0, shipment.order_number or '', cell_format)

            # Goods type - نوع البضاعة
            goods_type = 'Package'  # افتراضي
            if shipment.shipment_type == 'document':
                goods_type = 'Document'
            elif shipment.shipment_type == 'package':
                goods_type = 'Package'
            worksheet.write(row, 1, goods_type, cell_format)

            # Goods name - اسم البضاعة
            goods_names = []
            total_qty = 0
            for line in shipment.shipment_line_ids:
                goods_names.append(line.product_name)
                total_qty += line.quantity
            worksheet.write(row, 2, ', '.join(goods_names) if goods_names else '', cell_format)

            # Quantity - الكمية
            worksheet.write(row, 3, total_qty or 1, number_format)

            # Weight - الوزن
            worksheet.write(row, 4, shipment.total_weight or 0, number_format)

            # COD - الدفع عند الاستلام
            cod_amount = 0
            if shipment.payment_method == 'cod':
                cod_amount = shipment.cod_amount or 0
            worksheet.write(row, 5, cod_amount, number_format)

            # Insure price - قيمة التأمين
            insure_price = 0
            if shipment.insurance_required:
                insure_price = shipment.insurance_value or shipment.total_value or 0
            worksheet.write(row, 6, insure_price, number_format)

            # Whether to allow the package to be opened
            allow_open = 'No'  # افتراضي لا
            worksheet.write(row, 7, allow_open, cell_format)

            # Remark - ملاحظات
            remark = shipment.notes or ''
            worksheet.write(row, 8, remark, cell_format)

            # Name - اسم المستلم
            worksheet.write(row, 9, shipment.recipient_name or '', cell_format)

            # Telephone - تليفون المستلم
            phone = shipment.recipient_mobile or shipment.recipient_phone or ''
            worksheet.write(row, 10, phone, cell_format)

            # City - المدينة
            city = shipment.recipient_governorate_id.name if shipment.recipient_governorate_id else ''
            worksheet.write(row, 11, city, cell_format)

            # Area - المنطقة
            area = shipment.recipient_city or ''
            worksheet.write(row, 12, area, cell_format)

            # Receivers address - عنوان المستلم
            worksheet.write(row, 13, shipment.recipient_address or '', cell_format)

            # Receiver Email - إيميل المستلم
            worksheet.write(row, 14, shipment.recipient_email or '', cell_format)

            # Delivery Type - نوع التوصيل
            delivery_type = 'Standard'
            if shipment.state == 'out_for_delivery':
                delivery_type = 'Express'
            worksheet.write(row, 15, delivery_type, cell_format)

            row += 1

        # إغلاق الملف
        workbook.close()
        output.seek(0)

        # إنشاء attachment
        attachment = self.env['ir.attachment'].create({
            'name': f'shipment_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': self._name,
            'res_id': self[0].id if len(self) == 1 else False,
        })

        # إرجاع action لتحميل الملف
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }