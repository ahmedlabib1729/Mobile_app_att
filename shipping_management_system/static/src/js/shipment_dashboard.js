/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onMounted, onWillUnmount, useRef } from "@odoo/owl";

export class ShipmentDashboard extends Component {
    static template = "shipping_management_system.ShipmentDashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        // Search input reference
        this.searchInput = useRef("searchInput");

        this.state = useState({
            dashboardData: {},
            isLoading: true,
            searchTerm: '',
            dateFilter: 'today',
            startDate: this.getTodayDate(),
            endDate: this.getTodayDate(),
        });

        this.refreshInterval = null;
        this.searchTimeout = null;

        // Bind methods
        this.onRefreshClick = this.onRefreshClick.bind(this);
        this.onSearchInput = this.onSearchInput.bind(this);
        this.onDateFilterChange = this.onDateFilterChange.bind(this);
        this.onCustomDateChange = this.onCustomDateChange.bind(this);
        this.applyFilters = this.applyFilters.bind(this);
        this.viewShipmentsByStatus = this.viewShipmentsByStatus.bind(this);
        this.viewTodayShipments = this.viewTodayShipments.bind(this);
        this.viewDeliveredToday = this.viewDeliveredToday.bind(this);
        this.viewShipment = this.viewShipment.bind(this);
        this.viewAllShipments = this.viewAllShipments.bind(this);

        onWillStart(async () => {
            await this.loadDashboardData();
        });

        onMounted(() => {
            this.refreshInterval = setInterval(() => {
                this.loadDashboardData();
            }, 60000);
        });

        onWillUnmount(() => {
            if (this.refreshInterval) {
                clearInterval(this.refreshInterval);
            }
            if (this.searchTimeout) {
                clearTimeout(this.searchTimeout);
            }
        });
    }

    getTodayDate() {
        const today = new Date();
        return today.toISOString().split('T')[0];
    }

    async loadDashboardData() {
        try {
            const dateRange = this.getDateRange();

            const data = await this.orm.call(
                "shipment.dashboard",
                "get_dashboard_data",
                [],
                {
                    date_from: dateRange.from,
                    date_to: dateRange.to,
                    search_term: this.state.searchTerm
                }
            );

            this.state.dashboardData = data || {};
            this.state.isLoading = false;

        } catch (error) {
            console.error("Error loading dashboard data:", error);
            // Fallback - load without filters
            try {
                const data = await this.orm.call(
                    "shipment.dashboard",
                    "get_dashboard_data",
                    []
                );
                this.state.dashboardData = data || {};
            } catch (fallbackError) {
                console.error("Fallback also failed:", fallbackError);
                this.state.dashboardData = {};
            }
            this.state.isLoading = false;
        }
    }

    getDateRange() {
        const today = new Date();
        let from, to;

        switch(this.state.dateFilter) {
            case 'today':
                from = new Date(today);
                from.setHours(0,0,0,0);
                to = new Date(today);
                to.setHours(23,59,59,999);
                break;
            case 'week':
                from = new Date(today);
                from.setDate(today.getDate() - today.getDay());
                from.setHours(0,0,0,0);
                to = new Date();
                to.setHours(23,59,59,999);
                break;
            case 'month':
                from = new Date(today.getFullYear(), today.getMonth(), 1);
                to = new Date(today.getFullYear(), today.getMonth() + 1, 0);
                to.setHours(23,59,59,999);
                break;
            case 'year':
                from = new Date(today.getFullYear(), 0, 1);
                to = new Date(today.getFullYear(), 11, 31);
                to.setHours(23,59,59,999);
                break;
            case 'custom':
                from = this.state.startDate ? new Date(this.state.startDate + 'T00:00:00') : new Date();
                to = this.state.endDate ? new Date(this.state.endDate + 'T23:59:59') : new Date();
                break;
            default:
                from = new Date(today);
                from.setHours(0,0,0,0);
                to = new Date(today);
                to.setHours(23,59,59,999);
        }

        return {
            from: from.toISOString(),
            to: to.toISOString()
        };
    }

    // Search handler with debouncing
    onSearchInput(event) {
        const searchValue = event.target.value;
        this.state.searchTerm = searchValue;

        // Clear previous timeout
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }

        // Set new timeout for search
        this.searchTimeout = setTimeout(() => {
            this.applyFilters();
        }, 500); // Wait 500ms after user stops typing
    }

    async onDateFilterChange(event) {
        this.state.dateFilter = event.target.value;

        // Update date inputs when switching to custom
        if (this.state.dateFilter === 'custom') {
            const today = this.getTodayDate();
            this.state.startDate = today;
            this.state.endDate = today;
        }

        if (this.state.dateFilter !== 'custom') {
            await this.applyFilters();
        }
    }

    async onCustomDateChange() {
        if (this.state.dateFilter === 'custom') {
            await this.applyFilters();
        }
    }

    async applyFilters() {
        this.state.isLoading = true;
        await this.loadDashboardData();
    }

    // Helper Functions
    getInTransitCount() {
        const states = this.state.dashboardData.states || [];
        const inTransit = states.find(s => s.state === 'in_transit');
        return inTransit ? inTransit.count : 0;
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('en-EG', {
            style: 'currency',
            currency: 'EGP',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(amount || 0);
    }

    formatDate(date) {
        if (!date) return '';
        return new Date(date).toLocaleDateString('en-GB');
    }

    getStatusColor(status) {
        const colorMap = {
            'draft': 'secondary',
            'confirmed': 'primary',
            'picked': 'warning',
            'in_transit': 'info',
            'out_for_delivery': 'warning',
            'delivered': 'success',
            'returned': 'danger',
            'cancelled': 'dark'
        };
        return colorMap[status] || 'secondary';
    }

    // Action Methods
    async onRefreshClick() {
        this.state.isLoading = true;
        await this.loadDashboardData();
        this.notification.add("Dashboard refreshed", {
            type: "success",
        });
    }

    async viewShipmentsByStatus(status) {
        try {
            await this.action.doAction({
                type: 'ir.actions.act_window',
                name: `Shipments - ${status}`,
                res_model: 'shipment.order',
                views: [[false, 'list'], [false, 'form']],
                domain: [['state', '=', status]],
                target: 'current',
            });
        } catch (error) {
            console.error('Error:', error);
        }
    }

    async viewTodayShipments() {
        try {
            const dateRange = this.getDateRange();
            await this.action.doAction({
                type: 'ir.actions.act_window',
                name: "Period Shipments",
                res_model: 'shipment.order',
                views: [[false, 'list'], [false, 'form']],
                domain: [
                    ['create_date', '>=', dateRange.from],
                    ['create_date', '<=', dateRange.to]
                ],
                target: 'current',
            });
        } catch (error) {
            console.error('Error:', error);
        }
    }

    async viewDeliveredToday() {
        try {
            const dateRange = this.getDateRange();
            await this.action.doAction({
                type: 'ir.actions.act_window',
                name: "Delivered in Period",
                res_model: 'shipment.order',
                views: [[false, 'list'], [false, 'form']],
                domain: [
                    ['state', '=', 'delivered'],
                    ['create_date', '>=', dateRange.from],
                    ['create_date', '<=', dateRange.to]
                ],
                target: 'current',
            });
        } catch (error) {
            console.error('Error:', error);
        }
    }

    async viewShipment(shipmentId) {
        try {
            await this.action.doAction({
                type: 'ir.actions.act_window',
                res_model: 'shipment.order',
                res_id: parseInt(shipmentId),
                views: [[false, 'form']],
                target: 'current',
            });
        } catch (error) {
            console.error('Error:', error);
        }
    }

    async viewAllShipments() {
        try {
            await this.action.doAction({
                type: 'ir.actions.act_window',
                name: 'All Shipments',
                res_model: 'shipment.order',
                views: [[false, 'list'], [false, 'form']],
                target: 'current',
            });
        } catch (error) {
            console.error('Error:', error);
        }
    }
}

registry.category("actions").add("shipment_dashboard_client", ShipmentDashboard);
