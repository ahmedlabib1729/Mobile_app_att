# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
import base64
import io
import logging

_logger = logging.getLogger(__name__)


class EgyptGovernorate(models.Model):
    """نموذج المحافظات المصرية"""
    _name = 'egypt.governorate'
    _description = 'Egypt Governorate'
    _order = 'sequence, name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Governorate Name',
        required=True,
        tracking=True
    )

    name_en = fields.Char(
        string='English Name',
        tracking=True
    )

    name_ar = fields.Char(
        string='Arabic Name',
        tracking=True
    )

    code = fields.Char(
        string='Code',
        required=True,
        size=10,
        tracking=True
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True
    )

    zone = fields.Selection([
        ('cairo_giza', 'Cairo & Giza'),
        ('alexandria', 'Alexandria'),
        ('delta', 'Delta'),
        ('upper_egypt', 'Upper Egypt'),
        ('canal', 'Suez Canal'),
        ('red_sea_sinai', 'Red Sea & Sinai'),
        ('remote', 'Remote Areas')
    ], string='Zone',
        required=True,
        tracking=True)

    state_id = fields.Many2one(
        'res.country.state',
        string='System State',
        domain=[('country_id.code', '=', 'EG')]
    )

    area_ids = fields.One2many(
        'egypt.governorate.area',
        'governorate_id',
        string='Areas'
    )

    area_count = fields.Integer(
        string='Areas Count',
        compute='_compute_counts',
        store=True
    )

    city_count = fields.Integer(
        string='Cities Count',
        compute='_compute_counts',
        store=True
    )

    @api.depends('area_ids', 'area_ids.city_ids')
    def _compute_counts(self):
        for record in self:
            record.area_count = len(record.area_ids)
            record.city_count = sum(len(area.city_ids) for area in record.area_ids)

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Governorate code must be unique!'),
    ]

    @api.constrains('code')
    def _check_code(self):
        for record in self:
            if record.code and not re.match(r'^[A-Z0-9]{2,10}$', record.code):
                raise ValidationError(_('Code must be 2-10 uppercase letters or numbers!'))

    def name_get(self):
        result = []
        for record in self:
            name = f"[{record.code}] {record.name}"
            result.append((record.id, name))
        return result

    @api.model
    def get_zone_for_name(self, name):
        """Helper method to determine zone from governorate name"""
        zones_mapping = {
            'cairo_giza': ['القاهرة', 'Cairo', 'الجيزة', 'Giza'],
            'alexandria': ['الإسكندرية', 'Alexandria', 'الاسكندرية'],
            'delta': [
                'الدقهلية', 'الغربية', 'المنوفية', 'القليوبية',
                'كفر الشيخ', 'دمياط', 'الشرقية', 'البحيرة'
            ],
            'upper_egypt': [
                'أسيوط', 'أسوان', 'الأقصر', 'قنا', 'سوهاج',
                'المنيا', 'بني سويف', 'الفيوم'
            ],
            'canal': [
                'بورسعيد', 'الإسماعيلية', 'السويس'
            ],
            'red_sea_sinai': [
                'البحر الأحمر', 'جنوب سيناء', 'شمال سيناء'
            ],
            'remote': [
                'الوادي الجديد', 'مطروح'
            ]
        }

        for zone, governorates in zones_mapping.items():
            if any(gov in name for gov in governorates):
                return zone

        return 'delta'


class EgyptGovernorateArea(models.Model):
    """نموذج المناطق داخل المحافظات"""
    _name = 'egypt.governorate.area'
    _description = 'Egypt Governorate Area'
    _order = 'governorate_id, sequence, name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Area Name',
        required=True,
        tracking=True
    )

    name_en = fields.Char(
        string='English Name',
        tracking=True
    )

    name_ar = fields.Char(
        string='Arabic Name',
        tracking=True
    )

    code = fields.Char(
        string='Area Code'
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True
    )

    governorate_id = fields.Many2one(
        'egypt.governorate',
        string='Governorate',
        required=True,
        ondelete='cascade',
        tracking=True
    )

    zone = fields.Selection(
        related='governorate_id.zone',
        string='Zone',
        store=True,
        readonly=True
    )

    city_ids = fields.One2many(
        'egypt.governorate.city',
        'area_id',
        string='Cities/Districts'
    )

    city_count = fields.Integer(
        string='Cities Count',
        compute='_compute_city_count',
        store=True
    )

    @api.depends('city_ids')
    def _compute_city_count(self):
        for record in self:
            record.city_count = len(record.city_ids)

    _sql_constraints = [
        ('unique_area_per_governorate',
         'UNIQUE(name, governorate_id)',
         'Area name must be unique within the governorate!'),
    ]

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.name} ({record.governorate_id.name})"
            result.append((record.id, name))
        return result


class EgyptGovernorateCity(models.Model):
    """نموذج المدن/الأحياء داخل المناطق"""
    _name = 'egypt.governorate.city'
    _description = 'Egypt Governorate City/District'
    _order = 'area_id, sequence, name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='City/District Name',
        required=True,
        tracking=True
    )

    name_en = fields.Char(
        string='English Name',
        tracking=True
    )

    name_ar = fields.Char(
        string='Arabic Name',
        tracking=True
    )

    code = fields.Char(
        string='City Code'
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True
    )

    area_id = fields.Many2one(
        'egypt.governorate.area',
        string='Area',
        required=True,
        ondelete='cascade',
        tracking=True
    )

    governorate_id = fields.Many2one(
        related='area_id.governorate_id',
        string='Governorate',
        store=True,
        readonly=True
    )

    zone = fields.Selection(
        related='governorate_id.zone',
        string='Zone',
        store=True,
        readonly=True
    )

    zip_code = fields.Char(
        string='ZIP/Postal Code'
    )

    _sql_constraints = [
        ('unique_city_per_area',
         'UNIQUE(name, area_id)',
         'City name must be unique within the area!'),
    ]

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.name} - {record.area_id.name} ({record.governorate_id.name})"
            result.append((record.id, name))
        return result


class ImportEgyptLocations(models.TransientModel):
    """Wizard لاستيراد المواقع من Excel"""
    _name = 'import.egypt.locations'
    _description = 'Import Egypt Locations from Excel'

    excel_file = fields.Binary(
        string='Excel File',
        required=True,
        help='Upload Excel file with columns: Governorate | Area | City'
    )

    file_name = fields.Char(string='File Name')

    import_mode = fields.Selection([
        ('create', 'Create New Only'),
        ('update', 'Update Existing'),
        ('create_update', 'Create and Update')
    ], string='Import Mode',
        default='create',
        required=True,
        help='Choose how to handle existing records')

    skip_errors = fields.Boolean(
        string='Skip Errors',
        default=True,
        help='Continue importing even if some rows have errors'
    )

    clear_existing = fields.Boolean(
        string='Clear Existing Data',
        default=False,
        help='WARNING: This will delete all existing locations before importing'
    )

    import_summary = fields.Html(
        string='Import Summary',
        readonly=True
    )

    def action_import(self):
        """Main import action"""
        self.ensure_one()

        # Check for required libraries
        try:
            import openpyxl
            use_openpyxl = True
        except ImportError:
            try:
                import xlrd
                use_openpyxl = False
            except ImportError:
                raise ValidationError(_(
                    'Please install openpyxl:\n'
                    'pip install openpyxl'
                ))

        if not self.excel_file:
            raise ValidationError(_('Please upload an Excel file!'))

        # Clear existing if requested
        if self.clear_existing:
            self._clear_existing_data()

        # Decode file
        file_data = base64.b64decode(self.excel_file)
        file_io = io.BytesIO(file_data)

        # Process file
        if use_openpyxl:
            result = self._process_with_openpyxl(file_io)
        else:
            result = self._process_with_xlrd(file_io)

        # Show result
        return self._show_result(result)

    def _clear_existing_data(self):
        """Clear all existing location data"""
        self.env['egypt.governorate.city'].search([]).unlink()
        self.env['egypt.governorate.area'].search([]).unlink()
        self.env['egypt.governorate'].search([]).unlink()
        _logger.info("Cleared all existing location data")

    def _process_with_openpyxl(self, file_io):
        """Process Excel file using openpyxl"""
        import openpyxl

        wb = openpyxl.load_workbook(file_io, read_only=True, data_only=True)
        sheet = wb.active

        result = {
            'governorates': {'created': 0, 'updated': 0, 'skipped': 0},
            'areas': {'created': 0, 'updated': 0, 'skipped': 0},
            'cities': {'created': 0, 'updated': 0, 'skipped': 0},
            'errors': [],
            'total_rows': 0
        }

        # Cache for performance
        governorate_cache = {}
        area_cache = {}

        # Skip header row
        rows = list(sheet.iter_rows(min_row=2, values_only=True))
        result['total_rows'] = len(rows)

        for row_idx, row in enumerate(rows, start=2):
            try:
                # Extract data
                if not row or len(row) < 1:
                    continue

                gov_name = str(row[0]).strip() if row[0] else None
                area_name = str(row[1]).strip() if len(row) > 1 and row[1] else None
                city_name = str(row[2]).strip() if len(row) > 2 and row[2] else None

                if not gov_name:
                    continue

                # Process Governorate
                governorate = self._process_governorate(
                    gov_name, governorate_cache, result
                )

                # Process Area
                if area_name and governorate:
                    area = self._process_area(
                        area_name, governorate, area_cache, result
                    )

                    # Process City
                    if city_name and area:
                        self._process_city(city_name, area, result)

            except Exception as e:
                error_msg = f"Row {row_idx}: {str(e)}"
                result['errors'].append(error_msg)
                _logger.error(error_msg)
                if not self.skip_errors:
                    raise ValidationError(error_msg)

        return result

    def _process_with_xlrd(self, file_io):
        """Process Excel file using xlrd"""
        import xlrd

        wb = xlrd.open_workbook(file_contents=file_io.read())
        sheet = wb.sheet_by_index(0)

        result = {
            'governorates': {'created': 0, 'updated': 0, 'skipped': 0},
            'areas': {'created': 0, 'updated': 0, 'skipped': 0},
            'cities': {'created': 0, 'updated': 0, 'skipped': 0},
            'errors': [],
            'total_rows': sheet.nrows - 1
        }

        governorate_cache = {}
        area_cache = {}

        for row_idx in range(1, sheet.nrows):  # Skip header
            try:
                gov_name = str(sheet.cell_value(row_idx, 0)).strip() if sheet.ncols > 0 else None
                area_name = str(sheet.cell_value(row_idx, 1)).strip() if sheet.ncols > 1 else None
                city_name = str(sheet.cell_value(row_idx, 2)).strip() if sheet.ncols > 2 else None

                if not gov_name:
                    continue

                # Same processing logic
                governorate = self._process_governorate(gov_name, governorate_cache, result)

                if area_name and governorate:
                    area = self._process_area(area_name, governorate, area_cache, result)

                    if city_name and area:
                        self._process_city(city_name, area, result)

            except Exception as e:
                error_msg = f"Row {row_idx + 1}: {str(e)}"
                result['errors'].append(error_msg)
                if not self.skip_errors:
                    raise ValidationError(error_msg)

        return result

    def _process_governorate(self, name, cache, result):
        """Process a governorate"""
        if name in cache:
            return cache[name]

        Governorate = self.env['egypt.governorate']
        governorate = Governorate.search([('name', '=', name)], limit=1)

        if not governorate:
            if self.import_mode in ['create', 'create_update']:
                zone = Governorate.get_zone_for_name(name)
                code = self._generate_code(name)

                state = self.env['res.country.state'].search([
                    '|', ('name', 'ilike', name),
                    ('name', 'ilike', name.replace('ال', '')),
                    ('country_id.code', '=', 'EG')
                ], limit=1)

                governorate = Governorate.create({
                    'name': name,
                    'code': code,
                    'zone': zone,
                    'state_id': state.id if state else False,
                    'name_ar': name if self._is_arabic(name) else '',
                    'name_en': name if not self._is_arabic(name) else ''
                })
                result['governorates']['created'] += 1
                _logger.info(f"Created governorate: {name}")
            else:
                result['governorates']['skipped'] += 1
                return None
        else:
            result['governorates']['skipped'] += 1

        cache[name] = governorate
        return governorate

    def _process_area(self, name, governorate, cache, result):
        """Process an area"""
        cache_key = f"{governorate.id}_{name}"
        if cache_key in cache:
            return cache[cache_key]

        Area = self.env['egypt.governorate.area']
        area = Area.search([
            ('name', '=', name),
            ('governorate_id', '=', governorate.id)
        ], limit=1)

        if not area:
            if self.import_mode in ['create', 'create_update']:
                area = Area.create({
                    'name': name,
                    'governorate_id': governorate.id,
                    'name_ar': name if self._is_arabic(name) else '',
                    'name_en': name if not self._is_arabic(name) else ''
                })
                result['areas']['created'] += 1
                _logger.info(f"Created area: {name} in {governorate.name}")
            else:
                result['areas']['skipped'] += 1
                return None
        else:
            result['areas']['skipped'] += 1

        cache[cache_key] = area
        return area

    def _process_city(self, name, area, result):
        """Process a city"""
        City = self.env['egypt.governorate.city']
        city = City.search([
            ('name', '=', name),
            ('area_id', '=', area.id)
        ], limit=1)

        if not city:
            if self.import_mode in ['create', 'create_update']:
                city = City.create({
                    'name': name,
                    'area_id': area.id,
                    'name_ar': name if self._is_arabic(name) else '',
                    'name_en': name if not self._is_arabic(name) else ''
                })
                result['cities']['created'] += 1
                _logger.info(f"Created city: {name} in {area.name}")
            else:
                result['cities']['skipped'] += 1
        else:
            result['cities']['skipped'] += 1

        return city

    def _generate_code(self, name):
        """Generate a code from name"""
        # Remove Arabic AL
        name = name.replace('ال', '').replace('Al-', '').replace('El-', '')

        words = name.split()
        if len(words) == 1:
            code = name[:3].upper()
        else:
            code = ''.join([w[0].upper() for w in words[:3]])

        # Ensure uniqueness
        existing = self.env['egypt.governorate'].search([('code', '=', code)])
        if existing:
            code = code + str(len(existing) + 1)

        return code[:10]

    def _is_arabic(self, text):
        """Check if text contains Arabic characters"""
        arabic_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+')
        return bool(arabic_pattern.search(text))

    def _show_result(self, result):
        """Show import result"""
        summary = f"""
        <div style="padding: 10px;">
            <h3>Import Summary</h3>
            <p><strong>Total Rows Processed:</strong> {result['total_rows']}</p>

            <h4>Governorates:</h4>
            <ul>
                <li>Created: {result['governorates']['created']}</li>
                <li>Updated: {result['governorates']['updated']}</li>
                <li>Skipped: {result['governorates']['skipped']}</li>
            </ul>

            <h4>Areas:</h4>
            <ul>
                <li>Created: {result['areas']['created']}</li>
                <li>Updated: {result['areas']['updated']}</li>
                <li>Skipped: {result['areas']['skipped']}</li>
            </ul>

            <h4>Cities:</h4>
            <ul>
                <li>Created: {result['cities']['created']}</li>
                <li>Updated: {result['cities']['updated']}</li>
                <li>Skipped: {result['cities']['skipped']}</li>
            </ul>
        """

        if result['errors']:
            summary += f"""
            <h4 style="color: red;">Errors ({len(result['errors'])}):</h4>
            <ul style="color: red;">
            """
            for error in result['errors'][:10]:
                summary += f"<li>{error}</li>"

            if len(result['errors']) > 10:
                summary += f"<li>... and {len(result['errors']) - 10} more errors</li>"

            summary += "</ul>"

        summary += "</div>"

        self.import_summary = summary

        return {
            'name': _('Import Complete'),
            'type': 'ir.actions.act_window',
            'res_model': 'import.egypt.locations',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': {'show_summary': True}
        }