# -*- coding: utf-8 -*-
# Part of AlmightyCS. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF, DEFAULT_SERVER_DATETIME_FORMAT as DTF, format_datetime as tool_format_datetime
from collections import defaultdict
from odoo.tools.misc import formatLang
from dateutil.relativedelta import relativedelta

import logging
_logger = logging.getLogger(__name__)

class AcsHmsDashboard(models.Model):
    _name = "acs.hms.dashboard"
    _description = "Almighty HMS DASHBOARD"

    @api.model
    def acs_get_user_role(self):
        acs_is_physician = True if self.env.user.physician_count > 0 else False
        data = { 'acs_is_physician':acs_is_physician}
        return data
    
    def acs_get_company_domain(self):
        company = self.env.companies.ids
        company_domain = []
        if company:
            company.append(False)
            company_domain = [('company_id', 'in', company)]
        return company_domain
    
    @api.model
    def acs_get_dashboard_data(self, domain=[]):
        company_domain = self.acs_get_company_domain()
        base_domain = company_domain + domain
        Patient =  self.env['hms.patient']

        # Total Patient
        total_patient = Patient.search_count(base_domain)

        # My Total Patients
        patient_domain = base_domain + ['|',('primary_physician_id.user_id','=',self.env.uid), ('assignee_ids','in',self.env.user.partner_id.id)]
        my_total_patients = Patient.search_count(patient_domain)

        # Total Physician
        Physician = self.env['hms.physician']
        total_physician = Physician.search_count(base_domain)

        # Total Referring Physician
        Partner = self.env['res.partner']
        is_referring_physician_domain = base_domain + [('is_referring_doctor','=', True)]
        total_referring_physician = Partner.search_count(is_referring_physician_domain)

        # Total Procedures
        total_procedures = self.env['acs.patient.procedure'].search_count(base_domain)

        # Total Evaluations
        total_evaluations = self.env['acs.patient.evaluation'].search_count(base_domain)

        data = {
            "total_patient": total_patient,
            "my_total_patients": my_total_patients,
            "total_physician": total_physician,
            "total_referring_physician": total_referring_physician,
            "total_procedures": total_procedures,
            "total_evaluations": total_evaluations,
        }

        return data
    
    @api.model
    def acs_get_appointment_data(self, domain=[]):
        company_domain =  self.acs_get_company_domain()
        base_domain = company_domain + domain

        # Total Appointments
        Appointment = self.env['hms.appointment']
        total_appointments = Appointment.search_count(base_domain)

        # My Total Appointments
        my_total_appointment_domain = base_domain + [('physician_id.user_id','=',self.env.uid)]
        my_total_appointments =  Appointment.search_count(my_total_appointment_domain)

        data = {
            "total_appointments": total_appointments,
            "my_total_appointments": my_total_appointments,
        }
        return data
    
    @api.model
    def acs_get_treatment_data(self, domain=[]):
        company_domain = self.acs_get_company_domain()

        # Total Treatments
        Treatment = self.env['hms.treatment']
        treatment_domain = company_domain + domain
        total_treatments = Treatment.search_count(treatment_domain)

        running_treatment_domain = treatment_domain + [('state','=','running')]
        total_running_treatments = Treatment.search_count(running_treatment_domain)

        my_treatment_domain = treatment_domain + [('physician_id.user_id','=',self.env.uid)]
        my_total_treatments = Treatment.search_count(my_treatment_domain)

        my_running_treatment_domain = treatment_domain + [('state','=','running'), ('physician_id.user_id','=',self.env.uid)]
        my_total_running_treatments = Treatment.search_count(my_running_treatment_domain)

        data = {
            "total_treatments": total_treatments,
            "total_running_treatments": total_running_treatments,
            "my_total_treatments": my_total_treatments,
            "my_total_running_treatments": my_total_running_treatments,
        }
        return data

    @api.model
    def acs_get_invoice_data(self, domain=[]):
        company_domain = self.acs_get_company_domain()

        Invoice = self.env['account.move']
        open_invoice_domain = company_domain + domain
        open_invoice_domain += [('move_type','=','out_invoice'),('state','=','posted')]
        open_invoice = Invoice.search(open_invoice_domain)
        total_open_invoice = len(open_invoice)

        total_amount = 0
        for inv in open_invoice:
            total_amount += inv.amount_residual
        total_open_invoice_amount = round(total_amount, 2)

        currency = self.env.company.currency_id
        formatted_total_open_invoice_amount = formatLang(
            self.env, total_open_invoice_amount, currency_obj=currency
        )

        data = {
            "total_open_invoice": total_open_invoice,
            "formatted_total_open_invoice_amount": formatted_total_open_invoice_amount,
        }
        return data
    
    @api.model
    def acs_get_birthday_data(self):
        company_domain = self.acs_get_company_domain()
        today = datetime.now()
        today_month_day = '%-' + today.strftime('%m') + '-' + today.strftime('%d')

        Patient = self.env['hms.patient']
        patient_birthday_domain = company_domain + [('birthday', 'like', today_month_day)]
        count_patients_birthday = Patient.search_count(patient_birthday_domain)

        employee_birthday_domain = company_domain + [('birthday', 'like', today_month_day)]
        Employee = self.env['hr.employee']
        count_employees_birthday = Employee.search_count(employee_birthday_domain)

        data = {
            "count_patients_birthday": count_patients_birthday,
            "count_employees_birthday": count_employees_birthday
        }
        return data
    
    @api.model
    def acs_get_appointment_table_data(self, domain=[], offset=0, limit=20):
        user_role = self.acs_get_user_role()

        is_physician = user_role.get('acs_is_physician', False)

        company_domain = self.acs_get_company_domain()
        Appointment = self.env['hms.appointment']
        appointment_domain = company_domain + domain

        appointment_data = []
        if is_physician:
            appointment_list = Appointment.search(appointment_domain + [('physician_id.user_id', '=', self.env.uid)], offset=offset, limit=limit)
        else:
            appointment_list = Appointment.search(appointment_domain, offset=offset, limit=limit)

        for appointment in appointment_list:
            appointment = appointment.sudo()
            app_date = tool_format_datetime(self.env, appointment.date, dt_format=False)
            appointment_data.append({
                'id': appointment.id,
                'name': appointment.name,
                'patient': appointment.patient_id.name,
                'image': appointment.patient_id.image_1920,
                'date': app_date or '',
                'physician': appointment.physician_id.name,
                'purpose': appointment.purpose_id.name or '',
                'planned_duration': '{0:02.0f}:{1:02.0f}'.format(*divmod(appointment.planned_duration * 60, 60)),
                'waiting_duration': '{0:02.0f}:{1:02.0f}'.format(*divmod(appointment.waiting_duration * 60, 60)),
                'appointment_duration': '{0:02.0f}:{1:02.0f}'.format(*divmod(appointment.appointment_duration * 60, 60)),
                'state': dict(appointment._fields['state']._description_selection(self.env)).get(appointment.state),
            })

        data = {
            "appointment_data": appointment_data,
            "total_count": Appointment.search_count(appointment_domain)
        }
        return data
    
    def acs_get_domain(self, domain=[]):
        return domain
    
    def acs_open_patients(self, domain=[]):
        domain = self.acs_get_domain(domain)
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_base.action_patient")
        action['domain'] = domain
        return action
    
    def open_my_patients(self, domain=[]):
        domain = self.acs_get_domain(domain)
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_base.action_patient")
        action['domain'] = domain + ['|',('primary_physician_id.user_id','=',self.env.uid), ('assignee_ids','in',self.env.user.partner_id.id)]
        return action

    def open_referring_physicians(self, domain=[]):
        domain = self.acs_get_domain(domain)
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms.action_referring_doctors")
        action['domain'] = domain + [('is_referring_doctor','=',True)]
        return action

    def open_physicians(self, domain=[]):
        domain = self.acs_get_domain(domain)
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_base.action_physician")
        action['domain'] = domain
        return action

    def open_appointments(self, domain=[]):
        domain = self.acs_get_domain(domain)
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms.action_appointment")
        action['domain'] = domain
        action['context'] = {}
        return action

    def open_treatments(self, domain=[]):
        domain = self.acs_get_domain(domain)
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms.acs_action_form_hospital_treatment")
        action['domain'] = domain
        action['context'] = {}
        return action

    def open_my_appointments(self, domain=[]):
        domain = self.acs_get_domain(domain)
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms.action_appointment")
        action['domain'] = domain + [('physician_id.user_id','=',self.env.uid)]
        action['context'] = {}
        return action

    def open_running_treatments(self, domain=[]):
        domain = self.acs_get_domain(domain)
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms.acs_action_form_hospital_treatment")
        action['domain'] = domain + [('state','=','running')]
        return action

    def open_my_running_treatments(self, domain=[]):
        domain = self.acs_get_domain(domain)
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms.acs_action_form_hospital_treatment")
        action['domain'] = domain + [('state','=','running'),('physician_id.user_id','=',self.env.uid)]
        return action

    def open_my_treatments(self, domain=[]):
        domain = self.acs_get_domain(domain)
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms.acs_action_form_hospital_treatment")
        action['domain'] = domain + [('physician_id.user_id','=',self.env.uid)]
        action['context'] = {}
        return action
    
    def open_invoices(self, domain=[]):
        domain = self.acs_get_domain(domain)
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
        action['domain'] = domain + [('move_type','=','out_invoice'),('state', 'in', ['posted'])]
        return action

    def open_schedules(self):
        action = self.env["ir.actions.actions"]._for_xml_id("resource.action_resource_calendar_form")
        return action
    
    @api.model
    def acs_get_appointment_bar_graph(self):
        today = fields.Date.today()
        current_month = today.replace(day=1)
        last_month_30_days = current_month - timedelta(days=31)
        next_30_days = today + timedelta(days=30)

        record = self.env['hms.appointment'].read_group(
            domain=[('date', '>=', last_month_30_days),('date', '<=', next_30_days)],
            fields=['date'],
            groupby=['date:day'],
            lazy=False
        )
        daily_counts = defaultdict(int)
        for rec in record:
            appointment_create_date = rec.get('date:day')
            if appointment_create_date:
                try:
                    date_obj = datetime.strptime(appointment_create_date, '%d %b %Y')
                except ValueError:
                    continue

                date_str = date_obj.strftime('%d %b %Y')
                daily_counts[date_str] = rec.get('__count', 0)

        sorted_daily_counts = sorted(daily_counts.items(), key=lambda x: datetime.strptime(x[0], '%d %b %Y'))
        tooltiptext = [item[0] for item in sorted_daily_counts]
        labels = [datetime.strptime(item[0], '%d %b %Y').strftime('%d %b') for item in sorted_daily_counts]
        data = [item[1] for item in sorted_daily_counts]

        return {'labels': labels, 'data': data, 'tooltiptext': tooltiptext}
        
    @api.model
    def acs_get_new_patient_line_graph(self):
        # Get today's date and the start date (30 days ago)
        today = fields.Date.today()
        start_date = today - timedelta(days=365)

        # Group records by day
        records = self.env['hms.patient'].read_group(
            domain=[('create_date', '>=', start_date.strftime('%Y-%m-%d'))],
            fields=['create_date'],
            groupby=['create_date:day'],
            lazy=False
        )

        daily_counts = defaultdict(int)
        for record in records:
            create_date = record.get('create_date:day')
            if create_date:
                try:
                    date_obj = datetime.strptime(create_date, '%d %b %Y')
                except ValueError:
                    continue
                
                date_str = date_obj.strftime('%d %b %Y') # Format the date to '01 Jan' style for the labels
                daily_counts[date_str] = record.get('__count', 0) # Use the count directly from the record (no cumulative sum)
        
        # Sort the daily counts by date (to ensure the chart displays sequentially)
        sorted_daily_counts = sorted(daily_counts.items(), key=lambda x: datetime.strptime(x[0], '%d %b %Y')) 
        labels = [item[0] for item in sorted_daily_counts]
        data = [item[1] for item in sorted_daily_counts]

        return {'labels': labels, 'data': data}

    @api.model
    def acs_get_patient_age_data(self, domain=[]):
        company_domain = self.acs_get_company_domain()
        base_domain = domain + company_domain

        AGE_GROUPS = [
            {'label': '0-12 Years', 'min': 0, 'max': 12},
            {'label': '13-17 Years', 'min': 13, 'max': 17},
            {'label': '18-35 Years', 'min': 18, 'max': 35},
            {'label': '36-60 Years', 'min': 36, 'max': 60},
            {'label': '61+ Years', 'min': 61, 'max': 200},
        ]

        today = fields.Date.today()
        patient_ids = self.env['hms.patient'].search([('birthday', '!=', False)] + base_domain).ids
        _logger.info("\n\n Patient IDs for age grouping ---- %s", patient_ids)

        if not patient_ids:
            return [{'age_group': group['label'], 'count': 0} for group in AGE_GROUPS]

        query = f"""
            WITH ages AS (
                SELECT EXTRACT(YEAR FROM AGE(%s, rp.birthday))::int AS age
                FROM hms_patient hp
                JOIN res_partner rp ON hp.partner_id = rp.id
                WHERE hp.id = ANY(%s)
            )
            SELECT
                CASE
                    WHEN age BETWEEN 0 AND 12 THEN '0-12 Years'
                    WHEN age BETWEEN 13 AND 17 THEN '13-17 Years'
                    WHEN age BETWEEN 18 AND 35 THEN '18-35 Years'
                    WHEN age BETWEEN 36 AND 60 THEN '36-60 Years'
                    WHEN age >= 61 THEN '61+ Years'
                END AS age_group,
                COUNT(*) AS count
            FROM ages
            GROUP BY age_group
        """
        self.env.cr.execute(query, (today, patient_ids,))
        results = dict(self.env.cr.fetchall())
        _logger.info("\n\n Age distribution results ---- %s", results)

        return [{
            'age_group': agrp['label'],    
            'count': results.get(agrp['label'], 0)
        } for agrp in AGE_GROUPS]
    
    @api.model
    def acs_get_patient_gender_data(self, domain=[]):
        company_domain = self.acs_get_company_domain()
        base_domain = domain + company_domain

        patient_ids = self.env['hms.patient'].search(base_domain).ids
        if not patient_ids:
            return []

        query = """
            SELECT rp.gender, COUNT(*) 
            FROM hms_patient hp
            JOIN res_partner rp ON hp.partner_id = rp.id
            WHERE hp.id = ANY(%s)
            GROUP BY rp.gender
        """
        self.env.cr.execute(query, (patient_ids,))
        results = self.env.cr.fetchall()

        gender_dict = dict(self.env['res.partner']._fields['gender'].selection)
        valid_data = []
        for gender,count in results:
            gender_label = gender_dict.get(gender) if gender else 'Undefined'
            valid_data.append({'gender':gender_label, 'count':count})
        return valid_data

    @api.model
    def acs_get_all_countries(self, domain=[]):
        country_ids = self.env['res.partner'].search([
            ('is_patient', '=', True),
            ('country_id', '!=', False)
        ] + domain).mapped('country_id.id')
        country_domain = [('id', 'in', list(set(country_ids)))]
        countries = self.env['res.country'].search_read(
            country_domain,
            ['id', 'name']
        )
        return countries
    
    @api.model
    def acs_get_patient_country_data(self, domain=[]):
        company_domain = self.acs_get_company_domain()
        base_domain = domain + company_domain
        country_groups = self.env['hms.patient'].read_group(
            domain=base_domain,
            fields=['country_id'], groupby=['country_id'], orderby='country_id',
            lazy=False
        )
        data = []
        for group in country_groups:
            country = group['country_id']
            count = group['__count']
            if country:
                data.append({'category': country[1], 'value': count, 'id': country[0]})
            else:
                data.append({'category': 'Unknown', 'value': count, 'id': None})
        return data
    
    @api.model
    def acs_get_patient_state_data(self, country_id=None, domain=[]):
        company_domain = self.acs_get_company_domain()
        base_domain = domain + company_domain
        if country_id:
            base_domain.append(('country_id', '=', country_id))
        
        patient_state_groups = self.env['hms.patient'].read_group(
            domain=base_domain,
            fields=['state_id'],
            groupby=['state_id'],
            orderby='state_id',
            lazy=False
        )
        data = []
        for state_group in patient_state_groups:
            state_count = state_group.get('__count', 0)
            if state_group['state_id']:
                state_name = state_group['state_id'][1]
            else:
                state_name = "Undefined (No State)"
            data.append({
                'category': state_name,
                'value': state_count
            })
        return data

    @api.model
    def acs_get_patient_department_data(self, domain=[]):
        company_domain = self.acs_get_company_domain()
        base_domain = company_domain + domain

        result = []
        domain = [('department_id', '!=', False)] + base_domain
        appointments = self.env['hms.appointment'].search_read(domain, fields=['department_id', 'patient_id'])
        patient_department = {}

        for appointment in appointments:
            department_id = appointment['department_id'][0] if appointment['department_id'] else None
            patient_id = appointment['patient_id'][0] if appointment['patient_id'] else None
            if department_id and patient_id:
                patient_department.setdefault(department_id, set()).add(patient_id)

        departments = self.env['hr.department'].browse(patient_department.keys())
        for department in departments:
            result.append({
                'department': department.name,
                'count': len(patient_department[department.id])
            })
        return result

    @api.model
    def acs_get_appointment_disease_chart_data(self, domain=[]):
        company_domain = self.acs_get_company_domain()
        base_domain = domain + company_domain

        appointments = self.env['hms.appointment'].search([('diseases_ids', '!=', False)] + base_domain)
        disease_count = defaultdict(int)
        for appointment in appointments:
            for disease in appointment.diseases_ids:
                disease_count[disease.name] += 1

        diseases_sorted = sorted(disease_count.items(), key=lambda d: d[1], reverse=True)[:10]
        labels = [name for name, _ in diseases_sorted]
        count = [val for _, val in diseases_sorted]
        tooltip = [f"{name}: {val}" for name, val in diseases_sorted]

        data = {
            'labels': labels, 
            'data': count, 
            'tooltiptext': tooltip
        }
        return data

    @api.model
    def acs_get_invoice_services_data(self, domain=[]):
        company_domain = self.acs_get_company_domain()
        base_domain = domain + company_domain

        move_lines = self.env['account.move.line'].search([
            ('move_id.move_type', '=', 'out_invoice'),
            ('product_id.hospital_product_type', '!=', False)] + base_domain)
        
        totals = defaultdict(lambda: {"amount": 0.0, "quantity": 0.0})
        for line in move_lines:
            category = line.product_id.name
            totals[category]["amount"] += line.price_unit
            totals[category]["quantity"] += line.quantity

        categories = list(totals.keys())
        price_series = {
            "name": "Total Amount",
            "data": [totals[cat]["amount"] for cat in categories]
        }
        quantity_series = {
            "name": "Total Quantity",
            "data": [totals[cat]["quantity"] for cat in categories]
        }
        data = {
            "series": [price_series, quantity_series],
            "categories": categories
        }
        return data
    
    @api.model
    def acs_get_dashboard_color(self):
        return {"acs_dashboard_color": self.env.user.acs_dashboard_color or '#316EBF'}
    
    @api.model
    def check_hms_receptionist_grp(self):
        return self.env.user.has_group('acs_hms.group_hms_receptionist')
    
    @api.model
    def check_hms_js_doctor_grp(self):
        return self.env.user.has_group('acs_hms.group_hms_jr_doctor')
    
    @api.model
    def check_hms_nurse_grp(self):
        return self.env.user.has_group('acs_hms.group_hms_nurse')
        
    @api.model
    def check_hms_manager_grp(self):
        return self.env.user.has_group('acs_hms_base.group_hms_manager')
    
    @api.model
    def check_account_invoice_grp(self):
        return self.env.user.has_group('account.group_account_invoice')