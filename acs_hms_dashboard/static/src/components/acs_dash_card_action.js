import { user } from "@web/core/user";
import { _t } from "@web/core/l10n/translation";

export class AcsDashboardAction {
    constructor(state, actionService) {
        this.state = state;
        this.actionService = actionService;
    }

    async initializeDomain() {
        if (!this.state.domain) {
            console.warn(_t("Domain is undefined. Setting default value."));
            this.state.domain = [];
        }
    }

    async handleAction(name, model, domain, views, context={}) {
        await this.actionService.doAction({
            type: "ir.actions.act_window",
            name: _t(name),
            res_model: model,
            domain: domain,
            views: views,
            context: context
        });
    }

    async openPatients() {
        await this.initializeDomain();
        await this.handleAction(
            "Patients", // Name
            "hms.patient", // Model
            this.state.domain, // Domain
            [
                [false, "kanban"],  // Kanban View
                [false, "list"],    // List View
                [false, "form"]     // Form View
            ]
        );
    }

    async openMyPatients() {
        await this.initializeDomain();
        await this.handleAction(
            "My Patients",
            "hms.patient",
            [['primary_physician_id.user_id','=',user.userId]],
            [
                [false, "kanban"],
                [false, "list"],
                [false, "form"]
            ]
        );
    }

    async openPhysicians() {
        await this.initializeDomain();
        await this.handleAction(
            "Physicians",
            "hms.physician",
            this.state.domain,
            [
                [false, "kanban"],
                [false, "list"],
                [false, "form"]
            ]
        );
    }

    async openReferringPhysicians() {
        await this.initializeDomain();
        await this.handleAction(
            "Referring Doctors",
            "res.partner",
            [['is_referring_doctor', '=', true], ...this.state.domain],
            [
                [false, "kanban"],
                [false, "list"],
                [false, "form"]
            ]
        );
    }

    async openAppointments() {
        await this.initializeDomain();
        await this.handleAction(
            "Appointments",
            "hms.appointment",
            this.state.domain,
            [
                [false, "list"],
                [false, "kanban"],
                [false, "form"]
            ]
        );
    }

    async openMyAppointments() {
        await this.initializeDomain();
        await this.handleAction(
            "My Appointments",
            "hms.appointment",
            [['physician_id.user_id','=',user.userId],...this.state.date_domain],
            [
                [false, "list"],
                [false, "kanban"],
                [false, "form"],
            ]
        );
    }

    async openTreatments() {
        await this.initializeDomain();
        await this.handleAction(
            "Treatments",
            "hms.treatment",
            this.state.domain,
            [
                [false, "list"],
                [false, "form"]
            ]
        );
    }

    async openRunningTreatments() {
        await this.initializeDomain();
        await this.handleAction(
            "Running Treatments",
            "hms.treatment",
            [['state','=','running'],...this.state.date_domain],
            [
                [false, "list"],
                [false, "form"]
            ]
        );
    }

    async openMyRunningTreatments() {
        await this.initializeDomain();
        await this.handleAction(
            "My Running Treatments",
            "hms.treatment",
            [['state','=','running'],['physician_id.user_id','=',user.userId],...this.state.date_domain],
            [
                [false, "list"],
                [false, "form"]
            ]
        );
    }
    
    async openMyTreatments() {
        await this.initializeDomain();
        await this.handleAction(
            "My Treatments",
            "hms.treatment",
            [['physician_id.user_id','=',user.userId],...this.state.date_domain],
            [
                [false, "list"],
                [false, "form"]
            ]
        );
    }

    async openProcedures() {
        await this.initializeDomain();
        await this.handleAction(
            "My Procedures",
            "acs.patient.procedure",
            this.state.domain,
            [
                [false, "list"],
                [false, "form"]
            ]
        );
    }

    async openEvaluations() {
        await this.initializeDomain();
        await this.handleAction(
            "My Evaluations",
            "acs.patient.evaluation",
            this.state.domain,
            [
                [false, "list"],
                [false, "form"]
            ]
        );
    }

    async openInvoice() {
        await this.initializeDomain();
        await this.handleAction(
            "Invoices",
            "account.move",
            [['move_type','=','out_invoice'],['state','=','posted'],...this.state.invoice_domain],
            [
                [false, "list"],
                [false, "form"]
            ],
            {'default_move_type': 'out_invoice'},
        );
    }

    // This helper function finds the people whose birthday is today
    handleBirthday() {
        const today = new Date();
        const month = String(today.getMonth() + 1).padStart(2, '0');
        const day = String(today.getDate()).padStart(2, '0');
        const todayMonthDay = `%-${month}-${day}`;
        return todayMonthDay
    }

    async openPatientBirthdays() {
        const todayMonthDay = this.handleBirthday()
        await this.handleAction(
            "Today's Birthday Patients",
            "hms.patient",
            [['birthday', 'like', todayMonthDay]],
            [
                [false, 'kanban'],
                [false, "list"],
                [false, "form"],
            ],
        );
    }

    async openEmployeeBirthdays() {
        const todayMonthDay = this.handleBirthday()
        await this.handleAction(
            "Employees",
            "hr.employee.public",
            [['birthday', 'like', todayMonthDay]],
            [
                [false, 'kanban'],
                [false, "list"],
                [false, "form"],
            ]
        );
    }
}