/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onMounted } from "@odoo/owl";

export class ShipmentDashboard extends Component {
    static template = "shipping_management_system.ShipmentDashboard";
    static props = ["*"];

    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.state = useState({
            dashboardData: {},
            isLoading: true,
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });

        onMounted(() => {
            this.refreshInterval = setInterval(() => {
                this.loadDashboardData();
            }, 30000); // Refresh every 30 seconds
        });
    }

    async loadDashboardData() {
        try {
            const data = await this.rpc("/web/dataset/call_kw/shipment.dashboard/get_dashboard_data", {
                model: "shipment.dashboard",
                method: "get_dashboard_data",
                args: [],
                kwargs: {},
            });
            this.state.dashboardData = data;
            this.state.isLoading = false;
            this.updateUI(data);
        } catch (error) {
            console.error("Error loading dashboard data:", error);
            this.state.isLoading = false;
        }
    }

    updateUI(data) {
        // سنستخدم الـ template بدلاً من DOM manipulation مباشرة
        // البيانات موجودة في this.state.dashboardData
    }

    onRefreshClick() {
        this.state.isLoading = true;
        this.loadDashboardData();
    }

    willUnmount() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
    }
}

// تسجيل الـ component في الـ action registry
registry.category("actions").add("shipment_dashboard", ShipmentDashboard);