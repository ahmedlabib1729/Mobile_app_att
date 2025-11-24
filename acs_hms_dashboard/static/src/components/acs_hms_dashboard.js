/** @odoo-module **/
import { registry } from "@web/core/registry";
import { getDefaultConfig } from "@web/views/view";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

import { AcsDashboardKpi } from './acs_dash_card_kpi';
import { AcsDashboardAction } from './acs_dash_card_action';

import { renderAppointmentBarChart, renderPatientLineChart, renderPatientGenderPieChart } from "./acs_dash_charts";
import { renderPatientAgeGaugeChart, renderPatientCountryPieChart, renderPatientStateBarChart} from "./acs_dash_charts";
import { renderDepartmentDonutChart, renderPatientDiseaseBarChart, renderMedicalServicesLineChart} from "./acs_dash_charts";

const { Component, useSubEnv, useState, onMounted, onWillStart, useRef } = owl;

export class AcsHmsDashboard extends Component {

    setup() {
        this.rpc = rpc;
        this.actionService = useService("action");
        this.orm = useService("orm");

        this.appointmentBarChartContainer = useRef("appointmentBarChartContainer");
        this.patientLineChartContainer = useRef("patientLineChartContainer");
        this.patientGenderPieChartContainer = useRef("patientGenderPieChartContainer");
        this.patientAgeGaugeChartContainer = useRef("patientAgeGaugeChartContainer");
        this.patientCountryPieContainer = useRef("patientCountryPieContainer");
        this.patientStateBarChartContainer = useRef("patientStateBarChartContainer");
        this.departmentDonutChartContainer = useRef("departmentDonutChartContainer");
        this.patientDiseaseBarChartContainer = useRef("patientDiseaseBarChartContainer");
        this.medicalServicesBarLineContainer = useRef("medicalServicesBarLineContainer");

        useSubEnv({
            config: {
                ...getDefaultConfig(),
                ...this.env.config,
            },
        });

        this.state = useState({
            totalPatients: { 'total_patient': 0 },
            totalMyPatients: { 'my_total_patients': 0 },
            totalEvaluations: { 'total_evaluations': 0 },
            totalProcedures: { 'total_procedures': 0 },
            totalPhysicians: { 'total_physician': 0 },
            totalReferringPhysicians: { 'total_referring_physician': 0 },
            totalAppointments: { 'total_appointments': 0 },
            totalMyAppointments: { 'my_total_appointments': 0 },
            totalTreatments: { 'total_treatments': 0 },
            totalRunningTreatments: { 'total_running_treatments': 0 },
            totalMyTreatments: { 'my_total_treatments': 0 },
            totalMyRunningTreatments: { 'my_total_running_treatments': 0 },
            totalOpenInvoice: { 'total_open_invoice': 0},
            totalOpenInvoiceAmount: { 'formatted_total_open_invoice_amount': 0},
            countPatientBirthdays: { 'count_patients_birthday': 0 },
            countEmployeeBirthdays: { 'count_employees_birthday': 0 },
            appointmentsTable: { appointment_data: [] },
            dashboardColor: { 'acs_dashboard_color': '#316EBF' },

            isPhysicianUser: null,

            isReceptionistGroupVisible: false,
            isHmsJrDoctorGrpVisible: false,
            isHmsManagerGrpVisible: false,
            isAccountInvoiceGrpVisible: false,

            period: "Week",
            domain: [],
            date_domain: [],
            invoice_domain: [],
        });

        this.cardKpi = new AcsDashboardKpi(this.orm, this.state);
        this.cardAction = new AcsDashboardAction(this.state, this.actionService);

        onWillStart(async () => {
            await Promise.all([
                this.cardKpi.getProcedures(),
                this.cardKpi.getEvaluations(),
                this.cardKpi.getTotalPatients(),
                this.cardKpi.getTotalMyPatients(),
                this.cardKpi.getTotalPhysicians(),
                this.cardKpi.getTotalReferringPhysicians(),
                this.cardKpi.getTotalAppointments(),
                this.cardKpi.getTotalMyAppointments(),
                this.cardKpi.getTotalTreatments(),
                this.cardKpi.getTotalMyTreatments(),
                this.cardKpi.getTotalOpenInvoices(),
                this.cardKpi.getCountBirthdays(),

                this.getAppointmentTable(),
                this.getDashboardColor(),

                this.checkHmsReceptionistGroup(),
                this.checkHmsNurse(),
                this.checkHmsJrDoctor(),
                this.checkHmsManager(),
                this.checkAccountInvoice(),
                this.checkIsPhysician(),
            ])
        });

        onMounted(() => {
            renderAppointmentBarChart(this.appointmentBarChartContainer.el);
            renderPatientLineChart(this.patientLineChartContainer.el);
            this.onChangePeriod();
            
        });
    }

    openPatients = () => this.cardAction.openPatients();
    openMyPatients = () => this.cardAction.openMyPatients();
    openMyAppointments = () => this.cardAction.openMyAppointments();
    openProcedures = () => this.cardAction.openProcedures();
    openEvaluations = () => this.cardAction.openEvaluations();
    openMyRunningTreatments = () => this.cardAction.openMyRunningTreatments();
    openMyTreatments = () => this.cardAction.openMyTreatments();
    openMyAppointments = () => this.cardAction.openMyAppointments();
    openAppointments = () => this.cardAction.openAppointments();
    openPhysicians = () => this.cardAction.openPhysicians();
    openReferringPhysicians = () => this.cardAction.openReferringPhysicians();
    openInvoice = () => this.cardAction.openInvoice();
    openRunningTreatments = () => this.cardAction.openRunningTreatments();
    openTreatments = () => this.cardAction.openTreatments();
    openAppointments = () => this.cardAction.openAppointments();
    openEmployeeBirthdays = () => this.cardAction.openEmployeeBirthdays();
    openPatientBirthdays = () => this.cardAction.openPatientBirthdays();

    async onChangePeriod() {
        const now = new Date();
        let startDate, endDate;
        
        if (this.state.period == 'Today') {
            startDate = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} 00:00:00`;
            endDate = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} 23:59:59`;
        } else if (this.state.period == 'Week') {
            const sixDaysAgo = new Date(now);
            sixDaysAgo.setDate(now.getDate() - 6); // changed from current day to 6 days ago
            startDate = `${sixDaysAgo.getFullYear()}-${String(sixDaysAgo.getMonth() + 1).padStart(2, '0')}-${String(sixDaysAgo.getDate()).padStart(2, '0')} 00:00:00`;
            endDate = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} 23:59:59`;
        } else if (this.state.period == 'Month') {
            const oneMonthAgo = new Date(now);
            oneMonthAgo.setMonth(now.getMonth() - 1); // changed from current day of month to last month
            startDate = `${oneMonthAgo.getFullYear()}-${String(oneMonthAgo.getMonth() + 1).padStart(2, '0')}-${String(oneMonthAgo.getDate()).padStart(2, '0')} 00:00:00`;
            endDate = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} 23:59:59`;
        } else if (this.state.period == 'Year') {
            const oneYearAgo = new Date(now);
            oneYearAgo.setFullYear(now.getFullYear() - 1); // changed from current day of year to last year
            startDate = `${oneYearAgo.getFullYear()}-${String(oneYearAgo.getMonth() + 1).padStart(2, '0')}-${String(oneYearAgo.getDate()).padStart(2, '0')} 00:00:00`;
            endDate = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} 23:59:59`;
        } else if (this.state.period == 'Till_Now') {
            const systemStartDate = new Date(0);
            startDate = `${systemStartDate.getFullYear()}-${String(systemStartDate.getMonth() + 1).padStart(2, '0')}-${String(systemStartDate.getDate()).padStart(2, '0')} 00:00:00`;
            endDate = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
        }
        
        const baseDomain = [['create_date', '>=', startDate], ['create_date', '<=', endDate]];
        const dateDomain = [['date', '>=', startDate], ['date', '<=', endDate]];
        const invoiceDomain = [['invoice_date', '>=', startDate], ['invoice_date', '<=', endDate]];
        
        this.state.domain = baseDomain;
        this.state.date_domain = dateDomain;
        this.state.invoice_domain = invoiceDomain;
        
        // Make sure domain is set before proceeding
        if (!this.state.domain) {
            console.warn(_t("Domain is still undefined after update. Setting fallback."));
            this.state.domain = [];
        }
    
        await Promise.all([
            this.cardKpi.getTotalPatients(),
            this.cardKpi.getProcedures(),
            this.cardKpi.getEvaluations(),
            this.cardKpi.getTotalMyPatients(),
            this.cardKpi.getTotalPhysicians(),
            this.cardKpi.getTotalReferringPhysicians(),
            this.cardKpi.getTotalAppointments(),
            this.cardKpi.getTotalMyAppointments(),
            this.cardKpi.getTotalTreatments(),
            this.cardKpi.getTotalMyTreatments(),
            this.cardKpi.getTotalOpenInvoices(),
            this.cardKpi.getCountBirthdays(),

            this.getAppointmentTable(),

            renderPatientGenderPieChart(this.patientGenderPieChartContainer.el, this.state.domain),
            renderPatientAgeGaugeChart(this.patientAgeGaugeChartContainer.el, this.state.domain),
            renderPatientCountryPieChart(this.patientCountryPieContainer.el, this.state.domain),
            renderDepartmentDonutChart(this.departmentDonutChartContainer.el, this.state.domain),
            renderPatientDiseaseBarChart(this.patientDiseaseBarChartContainer.el, this.state.domain),
        ]);
        if (this.patientStateBarChartContainer?.el) {
            await renderPatientStateBarChart(this.patientStateBarChartContainer.el, this.state.domain);
        } else {
            console.warn("patientStateBarChartContainer.el is not available yet");
        }
        if (this.medicalServicesBarLineContainer?.el) {
            await renderMedicalServicesLineChart(this.medicalServicesBarLineContainer.el, this.state.domain);
        } else {
            console.warn("medicalServicesBarLineContainer.el is not available yet");
        }
    }

    /**
     * Fetches the dashboard color for the current user by calling the 'acs_get_dashboard_color' method
     * on the 'acs.hms.dashboard' model. Updates the state with the fetched dashboard color or defaults
     * to black ('#000000') if no color is returned or an error occurs.
     */
    async getDashboardColor() {
        try {
            const dashColorData = await this.orm.call('acs.hms.dashboard', 'acs_get_dashboard_color', []);
            if (dashColorData && dashColorData.acs_dashboard_color) {
                this.state.dashboardColor = dashColorData.acs_dashboard_color;
            } else {
                console.warn(_t("No dashboard color returned, defaulting to black."));
                this.state.dashboardColor = '#000000';
            }
        } catch (error) {
            console.error(_t("Error fetching dashboard color:"), error);
            this.state.dashboardColor = '#000000';
        }
    }

    async getAppointmentTable(offset = 0, limit = 20) {
        try {
            var appointmentTableData = await this.orm.call('acs.hms.dashboard', 'acs_get_appointment_table_data', [this.state.date_domain, offset, limit]);
            if (appointmentTableData) {
                this.state.appointmentsTable = appointmentTableData;
                console.log("\n this.state.appointmentsTable -------------------", this.state.appointmentsTable)
            }
        } catch (error) {
            console.error(_t("Error fetching Appointments Table:"), error);
        }
    }

    openAppointment(appointmentId) {
        this.orm.call('hms.appointment', 'read', [[appointmentId], ['id']]).then((result) => {
            if (result && result.length) {
                this.actionService.doAction({
                    type: 'ir.actions.act_window',
                    name: _t('Appointment'),
                    res_model: 'hms.appointment',
                    res_id: appointmentId,
                    views: [[false, 'form']],
                    target: 'current',
                });
            } else {
                console.error("No appointment found with this ID.");
            }
        }).catch((error) => {
            console.error("Error opening Appointment record:", error);
        });
    }  
    async checkIsPhysician() {
        try {
            const isPhysicianData = await this.orm.call('acs.hms.dashboard', 'acs_get_user_role', []);
            if (isPhysicianData)
                this.state.isPhysicianUser = isPhysicianData; // Store the full object
        } catch (error) {
            console.error(_t("Error checking physician role:"), error);
        }
    }

    async checkHmsReceptionistGroup() {
        try {
            const isHmsReceptionist = await this.orm.call('acs.hms.dashboard', 'check_hms_receptionist_grp', []);
            if (isHmsReceptionist) {
                this.state.isHmsReceptionistGrp = isHmsReceptionist;
            }
        } catch (error) {
            console.error(_t("Error checking receptionist group:"), error);
        }
    }

    async checkHmsNurse() {
        try {
            const isHmsNurse = await this.orm.call('acs.hms.dashboard', 'check_hms_nurse_grp', []);
            if (isHmsNurse) {
                this.state.isHmsNurseGrp = isHmsNurse;
            }
        } catch (error) {
            console.error(_t("Error checking nurse group:"), error);
        }
    }

    async checkHmsJrDoctor() {
        try {
            const isHmsJrDoctor = await this.orm.call('acs.hms.dashboard', 'check_hms_js_doctor_grp', []);
            if (isHmsJrDoctor) {
                this.state.isHmsJrDoctorGrp = isHmsJrDoctor;
            }
        } catch (error) {
            console.error(_t("Error checking jr doctor group:"), error);
        }
    }

    async checkHmsManager() {
        try {
            const isHmsManager = await this.orm.call('acs.hms.dashboard', 'check_hms_manager_grp', []);
            if (isHmsManager) {
                this.state.isHmsManagerGrp = isHmsManager;
            }
        } catch (error) {
            console.error(_t("Error checking manager group:"), error);
        }
    }

    async checkAccountInvoice() {
        try {
            const isAccountInvoice = await this.orm.call('acs.hms.dashboard', 'check_account_invoice_grp', []);
            if (isAccountInvoice) {
                this.state.isAccountInvoiceGrp = isAccountInvoice;
            }
        } catch (error) {
            console.error(_t("Error checking account invoice group:"), error);
        }
    }

}

AcsHmsDashboard.template = "acs_hms_dashboard.AcsHmsDashboard";
registry.category("actions").add("AlmightyHmsDashboard", AcsHmsDashboard);