/** @odoo-module **/

export class AcsDashboardKpi {
    constructor(orm, state) {
        this.orm = orm;
        this.state = state;
    }

    // This helper function is used to identify which cards have only one KPI value
    async handleSingleKpiData(model, method, domain=[], stateVal, errorMessage) {
        try {
            const data = await this.orm.call(model, method, domain);
            this.state[stateVal] = data || 0;
        } catch (error) {
            console.error(`${errorMessage}:`, error.message || error);
        }
    }

    async getTotalPatients() {
        await this.handleSingleKpiData(
            'acs.hms.dashboard', // Model Name
            'acs_get_dashboard_data', // Method Name
            [this.state.domain], // Domain
            'totalPatients', // State Variable
            'Error Fetching Total Patients' // Error Key
        );
    }

    async getProcedures() {
        await this.handleSingleKpiData(
            'acs.hms.dashboard',
            'acs_get_dashboard_data',
            [this.state.domain],
            'totalProcedures',
            'Error Fetching Procedures'
        );
    }

    async getEvaluations() {
        await this.handleSingleKpiData(
            'acs.hms.dashboard',
            'acs_get_dashboard_data',
            [this.state.domain],
            'totalEvaluations',
            'Error Fetching Evaluations'
        );
    }


    async getTotalMyPatients() {
        await this.handleSingleKpiData(
            'acs.hms.dashboard',
            'acs_get_dashboard_data',
            [this.state.domain],
            'totalMyPatients',
            'Error Fetching My Total Patients'
        );
    }
    
    async getTotalPhysicians() {
        await this.handleSingleKpiData(
            'acs.hms.dashboard',
            'acs_get_dashboard_data',
            [this.state.domain],
            'totalPhysicians',
            'Error fetching Total Physicians'
        );
    }
    
    async getTotalReferringPhysicians() {
        await this.handleSingleKpiData(
            'acs.hms.dashboard',
            'acs_get_dashboard_data',
            [this.state.domain],
            'totalReferringPhysicians',
            'Error fetching Total Referring Physicians'
        );
    }
    
    async getTotalAppointments() {
        await this.handleSingleKpiData(
            'acs.hms.dashboard',
            'acs_get_appointment_data',
            [this.state.date_domain],
            'totalAppointments',
            'Error fetching Total Appointments'
        )
    }
    
    async getTotalMyAppointments() {
        await this.handleSingleKpiData(
            'acs.hms.dashboard',
            'acs_get_appointment_data',
            [this.state.date_domain],
            'totalMyAppointments',
            'Error fetching Total My Appointments'
        )
    }

    // This helper function is used to identify which cards have two KPI values
    async handleDoubleKpiData(model, method, domain=[], stateVal1, stateVal2, errorMessage) {
        try {
            const data = await this.orm.call(model, method, domain);
            if (data) {
                this.state[stateVal1] = data;
                this.state[stateVal2] = data;
            }
        } catch (error) {
            console.error(`${errorMessage}`, error.message || error);
        }
    }
    
    async getTotalTreatments() {
        await this.handleDoubleKpiData(
            'acs.hms.dashboard', 
            'acs_get_treatment_data', 
            [this.state.date_domain],
            'totalTreatments',
            'totalRunningTreatments',
            'Error fetching Total Running Treatments'
        );
    }
    
    async getTotalMyTreatments() {
        await this.handleDoubleKpiData(
            'acs.hms.dashboard', 
            'acs_get_treatment_data', 
            [this.state.date_domain],
            'totalMyTreatments',
            'totalMyRunningTreatments',
            'Error fetching Total My Running Treatments'
        );
    }
    
    async getTotalOpenInvoices() {
        await this.handleDoubleKpiData(
            'acs.hms.dashboard', 
            'acs_get_invoice_data', 
            [this.state.invoice_domain],
            'totalOpenInvoice',
            'totalOpenInvoiceAmount',
            'Error fetching Total Open Invoices'
        );
    }
    
    async getCountBirthdays() {
        await this.handleDoubleKpiData(
            'acs.hms.dashboard', 
            'acs_get_birthday_data', [],
            'countPatientBirthdays',
            'countEmployeeBirthdays',
            'Error fetching Count Birthdays'
        );
    }
}