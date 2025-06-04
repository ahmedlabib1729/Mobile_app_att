# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import io

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None
from datetime import datetime


class WithdrawalReport(models.TransientModel):
    _name = 'withdrawal.report'
    _description = 'Apartment Withdrawal Report'

    # Report Filters
    date_from = fields.Date(
        string='From Date',
        default=fields.Date.today().replace(day=1)  # First day of current month
    )

    date_to = fields.Date(
        string='To Date',
        default=fields.Date.today()
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        help="Filter by specific partner"
    )

    building_id = fields.Many2one(
        'building',
        string='Building',
        help="Filter by specific building"
    )

    status = fields.Selection([
        ('all', 'All'),
        ('withdrawn', 'Withdrawn'),
        ('restored', 'Restored')
    ], string='Status', default='all')

    report_type = fields.Selection([
        ('summary', 'Summary Report'),
        ('detailed', 'Detailed Report'),
        ('statistics', 'Statistics Report'),
        ('excel', 'Excel Export - All Data')
    ], string='Report Type', default='summary', required=True)

    # Report Results - for Excel export
    report_data = fields.Binary('Report File')
    report_name = fields.Char('Report Name')

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from and record.date_to and record.date_from > record.date_to:
                raise UserError(_("From Date must be before To Date."))

    def action_generate_report(self):
        """Generate the withdrawal report"""
        self.ensure_one()

        # Build domain for search
        domain = self._build_domain()

        # Get withdrawal monitor records
        withdrawal_records = self.env['withdrawal.monitor'].search(domain)

        # Generate different report types
        if self.report_type == 'summary':
            return self._generate_summary_report(withdrawal_records)
        elif self.report_type == 'detailed':
            return self._generate_detailed_report(withdrawal_records)
        elif self.report_type == 'statistics':
            return self._generate_statistics_report(withdrawal_records)
        elif self.report_type == 'excel':
            return self._generate_excel_report(withdrawal_records)

    def _build_domain(self):
        """Build domain for search based on filters"""
        domain = []

        # Date filters - سهلناها علشان تشتغل صح
        if self.date_from:
            domain.append('|')
            domain.append(('withdrawal_date', '>=', self.date_from))
            domain.append(('create_date', '>=', str(self.date_from) + ' 00:00:00'))

        if self.date_to:
            domain.append('|')
            domain.append(('withdrawal_date', '<=', self.date_to))
            domain.append(('create_date', '<=', str(self.date_to) + ' 23:59:59'))

        # Partner filter
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))

        # Building filter
        if self.building_id:
            domain.append(('building_id', '=', self.building_id.id))

        # Status filter
        if self.status != 'all':
            domain.append(('status', '=', self.status))

        return domain

    def _generate_summary_report(self, records):
        """Generate summary report - Direct tree view"""
        return {
            'name': _('Withdrawal Summary Report'),
            'type': 'ir.actions.act_window',
            'res_model': 'withdrawal.monitor',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', records.ids)],
            'context': {'search_default_group_by_status': 1},
            'target': 'current',
        }

    def _generate_detailed_report(self, records):
        """Generate detailed report"""
        return {
            'name': _('Withdrawal Detailed Report'),
            'type': 'ir.actions.act_window',
            'res_model': 'withdrawal.monitor',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', records.ids)],
            'context': {'detailed_view': True},
            'target': 'current',
        }

    def _generate_statistics_report(self, records):
        """Generate statistics report with modern dashboard view"""
        total_records = len(records)

        if total_records == 0:
            # إذا مفيش data، ارجع notification
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Data'),
                    'message': _('No records found for the selected criteria.'),
                    'type': 'warning',
                }
            }

        stats = {
            'total_withdrawals': len(records.filtered(lambda r: r.status == 'withdrawn')),
            'total_restorations': len(records.filtered(lambda r: r.status == 'restored')),
            'total_overdue_amount': sum(records.mapped('overdue_amount')),
            'average_overdue_months': sum(records.mapped('overdue_months')) / total_records if total_records else 0,
        }

        # Calculate restoration rate
        withdrawn_count = stats['total_withdrawals'] + stats['total_restorations']
        stats['restoration_rate'] = (stats['total_restorations'] / withdrawn_count * 100) if withdrawn_count else 0

        return {
            'name': _('📊 Withdrawal Statistics Dashboard'),
            'type': 'ir.actions.act_window',
            'res_model': 'withdrawal.report.statistics',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_statistics_data': str(stats),
                'default_date_from': self.date_from,
                'default_date_to': self.date_to,
                'default_total_withdrawals': stats['total_withdrawals'],
                'default_total_restorations': stats['total_restorations'],
                'default_total_overdue_amount': stats['total_overdue_amount'],
                'default_average_overdue_months': stats['average_overdue_months'],
                'default_restoration_rate': stats['restoration_rate'],
            }
        }

    def _generate_excel_report(self, records):
        """Generate Excel report with ALL data like tree view"""
        if not xlsxwriter:
            raise UserError(_("xlsxwriter library is not installed. Please install it to use Excel export."))

        if not records:
            raise UserError(_("No records found for Excel export."))

        # Create Excel file in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)

        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'font_size': 12,
            'bg_color': '#4CAF50',  # Green header
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })

        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'align': 'center',
            'bg_color': '#2E7D32',
            'font_color': 'white'
        })

        data_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 10
        })

        date_format = workbook.add_format({
            'border': 1,
            'num_format': 'dd/mm/yyyy',
            'align': 'center',
            'font_size': 10
        })

        currency_format = workbook.add_format({
            'border': 1,
            'num_format': '#,##0.00',
            'align': 'right',
            'font_size': 10
        })

        # Status formats (colored like tree view)
        status_formats = {
            'withdrawn': workbook.add_format({'border': 1, 'bg_color': '#FFCDD2', 'align': 'center'}),  # Light red
            'restored': workbook.add_format({'border': 1, 'bg_color': '#C8E6C9', 'align': 'center'}),  # Light green
        }

        # Create main worksheet - ALL DATA
        main_sheet = workbook.add_worksheet('All Withdrawal Data')
        self._create_all_data_sheet(main_sheet, records, title_format, header_format, data_format,
                                    date_format, currency_format, status_formats)

        workbook.close()
        output.seek(0)

        # Generate file name
        file_name = f"withdrawal_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        # Save file data
        file_data = base64.b64encode(output.read())
        output.close()

        # Update wizard with file data
        self.write({
            'report_data': file_data,
            'report_name': file_name
        })

        # Return to same form with download option
        return {
            'name': _('Excel Report Generated'),
            'type': 'ir.actions.act_window',
            'res_model': 'withdrawal.report',
            'view_mode': 'form',
            'view_id': self.env.ref('apartment_withdrawal_management.withdrawal_report_form_view').id,
            'res_id': self.id,
            'target': 'new',
        }

    def action_download_excel(self):
        """Download the generated Excel file"""
        self.ensure_one()
        if not self.report_data:
            raise UserError(_("No Excel file has been generated yet. Please generate the report first."))

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/?model=withdrawal.report&id={self.id}&filename_field=report_name&field=report_data&download=true&filename={self.report_name}',
            'target': 'self',
        }

    def _create_all_data_sheet(self, sheet, records, title_format, header_format, data_format,
                               date_format, currency_format, status_formats):
        """Create sheet with ALL withdrawal data exactly like tree view"""

        # Title
        sheet.merge_range(0, 0, 0, 11, 'Withdrawal Monitor Data', title_format)
        sheet.write(1, 0, f'Generated on: {datetime.now().strftime("%d/%m/%Y %H:%M")}', data_format)
        sheet.write(2, 0, f'Total Records: {len(records)}', data_format)

        # Headers - exactly like tree view columns
        headers = [
            'Contract',  # contract_id
            'Partner',  # partner_id
            'Building',  # building_id
            'Building Unit',  # building_unit_id
            'Overdue Installment',  # installment_id
            'Installment Number',  # installment_number
            'Original Due Date',  # due_date
            'Months Overdue',  # overdue_months
            'Overdue Amount',  # overdue_amount
            'Status',  # status
            'Withdrawal Date',  # withdrawal_date
            'Restoration Date'  # restoration_date
        ]

        # Write headers
        row = 4
        for col, header in enumerate(headers):
            sheet.write(row, col, header, header_format)

        # Write all data
        for record in records:
            row += 1
            col = 0

            # Contract
            sheet.write(row, col, record.contract_id.name or '', data_format)
            col += 1

            # Partner
            sheet.write(row, col, record.partner_id.name or '', data_format)
            col += 1

            # Building
            sheet.write(row, col, record.building_id.name or '', data_format)
            col += 1

            # Building Unit
            sheet.write(row, col, record.building_unit_id.name or '', data_format)
            col += 1

            # Overdue Installment
            sheet.write(row, col, record.installment_id.name or '', data_format)
            col += 1

            # Installment Number
            sheet.write(row, col, record.installment_number or '', data_format)
            col += 1

            # Original Due Date
            if record.due_date:
                sheet.write_datetime(row, col, datetime.combine(record.due_date, datetime.min.time()), date_format)
            else:
                sheet.write(row, col, '', data_format)
            col += 1

            # Months Overdue
            sheet.write(row, col, record.overdue_months or 0, data_format)
            col += 1

            # Overdue Amount
            sheet.write(row, col, record.overdue_amount or 0, currency_format)
            col += 1

            # Status (with color)
            status_text = record.status.replace('_', ' ').title() if record.status else ''
            status_format = status_formats.get(record.status, data_format)
            sheet.write(row, col, status_text, status_format)
            col += 1

            # Withdrawal Date
            if record.withdrawal_date:
                sheet.write_datetime(row, col, datetime.combine(record.withdrawal_date, datetime.min.time()),
                                     date_format)
            else:
                sheet.write(row, col, '', data_format)
            col += 1

            # Restoration Date
            if record.restoration_date:
                sheet.write_datetime(row, col, datetime.combine(record.restoration_date, datetime.min.time()),
                                     date_format)
            else:
                sheet.write(row, col, '', data_format)

        # Auto-fit columns
        column_widths = [15, 20, 15, 15, 20, 12, 15, 12, 15, 12, 15, 15]
        for i, width in enumerate(column_widths):
            sheet.set_column(i, i, width)

        # Add totals row
        total_row = row + 2
        sheet.write(total_row, 0, 'TOTALS:', header_format)
        sheet.write(total_row, 7, len(records), header_format)  # Total count

        # Total overdue amount
        total_amount = sum(records.mapped('overdue_amount'))
        sheet.write(total_row, 8, total_amount, currency_format)

        # Status summary
        summary_row = total_row + 2
        sheet.write(summary_row, 0, 'STATUS SUMMARY:', header_format)

        status_counts = {}
        for status in ['withdrawn', 'restored']:
            count = len(records.filtered(lambda r: r.status == status))
            if count > 0:
                status_counts[status] = count

        summary_col = 1
        for status, count in status_counts.items():
            sheet.write(summary_row, summary_col, f'{status.replace("_", " ").title()}: {count}', data_format)
            summary_col += 1


class WithdrawalReportStatistics(models.TransientModel):
    _name = 'withdrawal.report.statistics'
    _description = 'Withdrawal Statistics Display'

    date_from = fields.Date('From Date', readonly=True)
    date_to = fields.Date('To Date', readonly=True)

    total_withdrawals = fields.Integer('Total Withdrawals', readonly=True)
    total_restorations = fields.Integer('Total Restorations', readonly=True)

    total_overdue_amount = fields.Float('Total Overdue Amount', readonly=True, digits='Product Price')
    average_overdue_months = fields.Float('Average Overdue Months', readonly=True, digits=(12, 1))
    restoration_rate = fields.Float('Restoration Rate (%)', readonly=True, digits=(12, 1))

    statistics_data = fields.Text('Statistics Data', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        # Parse statistics data from context
        stats_str = self._context.get('default_statistics_data', '{}')
        try:
            stats = eval(stats_str)  # Safe since we control the data
            res.update({
                'total_withdrawals': stats.get('total_withdrawals', 0),
                'total_restorations': stats.get('total_restorations', 0),
                'total_overdue_amount': stats.get('total_overdue_amount', 0),
                'average_overdue_months': stats.get('average_overdue_months', 0),
                'restoration_rate': stats.get('restoration_rate', 0),
            })
        except:
            pass

        return res