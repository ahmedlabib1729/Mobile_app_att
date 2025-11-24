/** @odoo-module **/

export class AcsDashChartData {

    async acsHandleRequest(model, method, args=[], kwargs={}) {
        const response = await fetch("/web/dataset/call_kw", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: {
                    model: model,
                    method: method,
                    args: args,
                    kwargs: kwargs,
                },
                id: Math.random(), // A unique ID for the RPC request
            }),
        });
        return response
    }

    async acsHandleResponse(response, errorMessage) {
        if (!response.ok) {
            console.error(errorMessage, response.statusText);
            throw new Error(response.statusText);
        } else {
            const result = await response.json();
            return result.result;
        }
    }

    async acsFetchAppointmentData() {
        const response = await this.acsHandleRequest("acs.hms.dashboard", "acs_get_appointment_bar_graph")
        const errorResponse = await this.acsHandleResponse(response, "Failed to fetch appointment data")
        return errorResponse
    }

    async acsFetchPatientData() {
        const response = await this.acsHandleRequest("acs.hms.dashboard", "acs_get_new_patient_line_graph")
        const errorResponse = await this.acsHandleResponse(response, "Failed to fetch patient data") 
        return errorResponse
    }

    async acsFetchPatientGenderData(domain=[]) {
        const response = await this.acsHandleRequest("acs.hms.dashboard", "acs_get_patient_gender_data", [domain])
        console.log("\n response --------------------", response)
        const errorResponse = await this.acsHandleResponse(response, "Failed to fetch appointment data")
        return errorResponse
    }

    async acsFetchPatientAgeGrpData(domain = []) {
        const response = await this.acsHandleRequest("acs.hms.dashboard", "acs_get_patient_age_data", [domain]);
        const data = (typeof response.json === 'function') ? await response.json() : response;
        const actualData = data?.result ?? data;
        if (!Array.isArray(actualData)) {
            console.warn("Response is not an array:", actualData);
            return [];
        }
        return actualData;
    }

    async acsFetchPatientCountryData(domain = []) {
        const response = await this.acsHandleRequest("acs.hms.dashboard", "acs_get_patient_country_data", [domain]);
        return await this.acsHandleResponse(response, "Failed to fetch country data");
    }

    async acsFetchAllCountriesData() {
        const response = await this.acsHandleRequest("acs.hms.dashboard", "acs_get_all_countries");
        return await this.acsHandleResponse(response, "Failed to fetch country list");
    }

    async acsFetchPatientStateByCountryData(countryId = null,domain = []) {
        const response = await this.acsHandleRequest("acs.hms.dashboard", "acs_get_patient_state_data", [countryId,domain]);
        return await this.acsHandleResponse(response, "Failed to fetch patient state data");
    }

    async acsFetchPatientDepartmentData(domain = []) {
        const response = await this.acsHandleRequest("acs.hms.dashboard", "acs_get_patient_department_data",[domain])
        const errorResponse = await this.acsHandleResponse(response, "Failed to fetch appointment data")
        return errorResponse
    }

    async acsFetchPatientDiseaseData(domain = []) {
        const response = await this.acsHandleRequest("acs.hms.dashboard", "acs_get_appointment_disease_chart_data", [domain]);
        const result = await this.acsHandleResponse(response, "Failed to fetch appointment data");
        return result || { labels: [], data: [], tooltiptext: [] };
    }

    async acsFetchMedicalServicesData(domain = []) {
        const response = await this.acsHandleRequest("acs.hms.dashboard", "acs_get_invoice_services_data",[domain]);
        const chartData = await this.acsHandleResponse(response, "Failed to fetch medical services data");
        return chartData;
    }
}