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
        this.viewOverdueShipments = this.viewOverdueShipments.bind(this);
        // Search input reference
        this.searchInput = useRef("searchInput");

        this.viewWebsiteOrders = this.viewWebsiteOrders.bind(this);

        // استرجاع الفلاتر المحفوظة من sessionStorage
        const savedFilters = this.loadSavedFilters();

        this.state = useState({
            dashboardData: {},
            isLoading: true,
            searchTerm: savedFilters.searchTerm || '',
            dateFilter: savedFilters.dateFilter || 'today',
            startDate: savedFilters.startDate || this.getTodayDate(),
            endDate: savedFilters.endDate || this.getTodayDate(),
            currentFilters: {}, // حفظ الفلاتر الحالية
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
        this.viewInTransit = this.viewInTransit.bind(this);
        this.viewShipment = this.viewShipment.bind(this);
        this.viewAllShipments = this.viewAllShipments.bind(this);

        onWillStart(async () => {
            await this.loadDashboardData();
        });

        onMounted(() => {
            // تحديث كل 60 ثانية
            this.refreshInterval = setInterval(() => {
                this.loadDashboardData();
            }, 60000);

            // إذا كان هناك فلتر محفوظ، قم بتطبيقه
            if (savedFilters.hasFilters) {

            }
        });

        onWillUnmount(() => {
            if (this.refreshInterval) {
                clearInterval(this.refreshInterval);
            }
            if (this.searchTimeout) {
                clearTimeout(this.searchTimeout);
            }
            // حفظ الفلاتر عند مغادرة الصفحة
            this.saveFilters();
        });
    }

    // حفظ الفلاتر في sessionStorage
    saveFilters() {
        const filters = {
            searchTerm: this.state.searchTerm,
            dateFilter: this.state.dateFilter,
            startDate: this.state.startDate,
            endDate: this.state.endDate,
            hasFilters: true,
            timestamp: new Date().getTime()
        };

        try {
            sessionStorage.setItem('shipment_dashboard_filters', JSON.stringify(filters));
            console.log("Filters saved:", filters);
        } catch (e) {
            console.error("Could not save filters:", e);
        }
    }

    // استرجاع الفلاتر المحفوظة
    loadSavedFilters() {
        try {
            const saved = sessionStorage.getItem('shipment_dashboard_filters');
            if (saved) {
                const filters = JSON.parse(saved);

                // التحقق من أن الفلاتر ليست قديمة جداً (أكثر من 30 دقيقة)
                const now = new Date().getTime();
                const age = now - filters.timestamp;
                const thirtyMinutes = 30 * 60 * 1000;

                if (age < thirtyMinutes) {
                    console.log("Loading saved filters:", filters);
                    return filters;
                } else {
                    // إذا كانت قديمة، احذفها
                    sessionStorage.removeItem('shipment_dashboard_filters');
                    console.log("Filters expired, using defaults");
                }
            }
        } catch (e) {
            console.error("Could not load saved filters:", e);
        }

        return {
            searchTerm: '',
            dateFilter: 'today',
            startDate: this.getTodayDate(),
            endDate: this.getTodayDate(),
            hasFilters: false
        };
    }

    // مسح الفلاتر المحفوظة
    clearSavedFilters() {
        try {
            sessionStorage.removeItem('shipment_dashboard_filters');
            console.log("Saved filters cleared");
        } catch (e) {
            console.error("Could not clear saved filters:", e);
        }
    }

    // زر لإعادة تعيين الفلاتر
    resetFilters() {
        this.state.searchTerm = '';
        this.state.dateFilter = 'today';
        this.state.startDate = this.getTodayDate();
        this.state.endDate = this.getTodayDate();

        this.clearSavedFilters();
        this.applyFilters();

        this.notification.add("Filters reset to defaults", {
            type: "success",
        });
    }

    getTodayDate() {
        const today = new Date();
        return today.toISOString().split('T')[0];
    }

    async loadDashboardData() {
        try {
            const dateRange = this.getDateRange();

            // حفظ الفلاتر الحالية
            this.state.currentFilters = {
                date_from: dateRange.from,
                date_to: dateRange.to,
                search_term: this.state.searchTerm
            };

            // حفظ الفلاتر قبل كل تحميل
            this.saveFilters();

            console.log("Loading dashboard with filters:", this.state.currentFilters);

            const data = await this.orm.call(
                "shipment.dashboard",
                "get_dashboard_data",
                [],
                this.state.currentFilters
            );

            console.log("Dashboard data received:", data);

            this.state.dashboardData = data || {};
            this.state.isLoading = false;

        } catch (error) {
            console.error("Error loading dashboard data:", error);
            this.notification.add("Error loading dashboard data", {
                type: "danger",
            });
            this.state.dashboardData = {};
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

        // تحويل إلى تنسيق بسيط للتوافق مع Odoo
        const formatDate = (date) => {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            const hours = String(date.getHours()).padStart(2, '0');
            const minutes = String(date.getMinutes()).padStart(2, '0');
            const seconds = String(date.getSeconds()).padStart(2, '0');
            return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
        };

        return {
            from: formatDate(from),
            to: formatDate(to)
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
        this.saveFilters(); // حفظ الفلاتر قبل التطبيق
        await this.loadDashboardData();
    }

    // Action Methods
    async onRefreshClick() {
        console.log("=== Manual Refresh Triggered ===");
        this.state.isLoading = true;

        // فرض إعادة التحميل
        this.state.dashboardData = {};
        this.render();

        await this.loadDashboardData();

        this.notification.add("Dashboard refreshed successfully!", {
            type: "success",
        });
    }

    // عرض الشحنات حسب الحالة مع نفس الفلاتر المطبقة
    async viewShipmentsByStatus(status) {
        try {
            // حفظ الفلاتر قبل الانتقال
            this.saveFilters();

            const dateRange = this.getDateRange();
            let domain = [
                ['state', '=', status],
                ['create_date', '>=', dateRange.from],
                ['create_date', '<=', dateRange.to]
            ];

            // إضافة فلتر البحث إذا وجد
            if (this.state.searchTerm) {
                const searchDomain = [
                    '|', '|', '|',
                    ['order_number', 'ilike', this.state.searchTerm],
                    ['tracking_number', 'ilike', this.state.searchTerm],
                    ['sender_id.name', 'ilike', this.state.searchTerm],
                    ['recipient_id.name', 'ilike', this.state.searchTerm]
                ];
                domain = ['&', ...domain, ...searchDomain];
            }

            await this.action.doAction({
                type: 'ir.actions.act_window',
                name: `Shipments - ${status} (Filtered)`,
                res_model: 'shipment.order',
                views: [[false, 'list'], [false, 'form']],
                domain: domain,
                target: 'current',
                context: {
                    search_default_group_state: false,
                    create: false,
                    // إضافة معلومات للعودة
                    dashboard_return: true,
                }
            });
        } catch (error) {
            console.error('Error:', error);
        }
    }

    // باقي الدوال كما هي...
    // Helper Functions
    getInTransitCount() {
        return this.state.dashboardData.kpi?.in_transit || this.state.dashboardData.today?.in_transit || 0;
    }

    getTotalOrdersCount() {
        return this.state.dashboardData.kpi?.created || this.state.dashboardData.today?.created || 0;
    }

    getDeliveredCount() {
        return this.state.dashboardData.kpi?.delivered || this.state.dashboardData.today?.delivered || 0;
    }

    getConfirmedCount() {
        return this.state.dashboardData.kpi?.confirmed || this.state.dashboardData.today?.confirmed || 0;
    }

    getOverdueCount() {
    // استخدم overdue_count المنفصل بدلاً من kpi.overdue
    return this.state.dashboardData.overdue_count || 0;
}

getWebsiteOrdersCount() {
    // استخدم website_orders_count المنفصل
    return this.state.dashboardData.website_orders_count || 0;
}

async viewWebsiteOrders() {
    try {
        // Domain للطلبات من الموقع فقط - بدون فلترات التاريخ أو البحث
        let domain = [
            ['source', '=', 'website']
        ];

        await this.action.doAction({
            type: 'ir.actions.act_window',
            name: '🌐 All Website Orders',
            res_model: 'shipment.order',
            views: [[false, 'list'], [false, 'form']],
            domain: domain,
            target: 'current',
            context: {
                create: false,
            }
        });
    } catch (error) {
        console.error('Error viewing website orders:', error);
        this.notification.add("Error loading website orders", {
            type: "danger",
        });
    }
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
        'torood_hub': 'info',  // جديد
        'in_transit': 'info',
        'shipping_company_hub': 'primary',  // جديد
        'out_for_delivery': 'warning',
        'delivered': 'success',
        'returned': 'danger',
        'cancelled': 'dark'
    };
    return colorMap[status] || 'secondary';
}

    // الدوال الأخرى تبقى كما هي
    async viewTodayShipments() {
        try {
            this.saveFilters();
            const dateRange = this.getDateRange();
            let domain = [
                ['create_date', '>=', dateRange.from],
                ['create_date', '<=', dateRange.to]
            ];

            if (this.state.searchTerm) {
                const searchDomain = [
                    '|', '|', '|',
                    ['order_number', 'ilike', this.state.searchTerm],
                    ['tracking_number', 'ilike', this.state.searchTerm],
                    ['sender_id.name', 'ilike', this.state.searchTerm],
                    ['recipient_id.name', 'ilike', this.state.searchTerm]
                ];
                domain = ['&', ...domain, ...searchDomain];
            }

            await this.action.doAction({
                type: 'ir.actions.act_window',
                name: `Orders in Period (${this.state.dateFilter})`,
                res_model: 'shipment.order',
                views: [[false, 'list'], [false, 'form']],
                domain: domain,
                target: 'current',
            });
        } catch (error) {
            console.error('Error:', error);
        }
    }

    async viewDeliveredToday() {
        try {
            this.saveFilters();
            const dateRange = this.getDateRange();
            let domain = [
                ['state', '=', 'delivered'],
                ['create_date', '>=', dateRange.from],
                ['create_date', '<=', dateRange.to]
            ];

            if (this.state.searchTerm) {
                const searchDomain = [
                    '|', '|', '|',
                    ['order_number', 'ilike', this.state.searchTerm],
                    ['tracking_number', 'ilike', this.state.searchTerm],
                    ['sender_id.name', 'ilike', this.state.searchTerm],
                    ['recipient_id.name', 'ilike', this.state.searchTerm]
                ];
                domain = ['&', ...domain, ...searchDomain];
            }

            await this.action.doAction({
                type: 'ir.actions.act_window',
                name: "Delivered in Period (Filtered)",
                res_model: 'shipment.order',
                views: [[false, 'list'], [false, 'form']],
                domain: domain,
                target: 'current',
            });
        } catch (error) {
            console.error('Error:', error);
        }
    }

    async viewInTransit() {
    try {
        this.saveFilters();
        const dateRange = this.getDateRange();
        let domain = [
            ['state', 'in', ['torood_hub', 'in_transit', 'shipping_company_hub', 'out_for_delivery']],
            ['create_date', '>=', dateRange.from],
            ['create_date', '<=', dateRange.to]
        ];

        if (this.state.searchTerm) {
            const searchDomain = [
                '|', '|', '|',
                ['order_number', 'ilike', this.state.searchTerm],
                ['tracking_number', 'ilike', this.state.searchTerm],
                ['sender_id.name', 'ilike', this.state.searchTerm],
                ['recipient_id.name', 'ilike', this.state.searchTerm]
            ];
            domain = ['&', ...domain, ...searchDomain];
        }

        await this.action.doAction({
            type: 'ir.actions.act_window',
            name: "In Transit (All Stages)",
            res_model: 'shipment.order',
            views: [[false, 'list'], [false, 'form']],
            domain: domain,
            target: 'current',
        });
    } catch (error) {
        console.error('Error:', error);
    }
}

    async viewShipment(shipmentId) {
        try {
            this.saveFilters();
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

    async viewOverdueShipments() {
    try {
        const current_time = new Date();

        // Domain للطلبات المتأخرة بدون فلترات التاريخ أو البحث
        let domain = [
            ['expected_delivery', '!=', false],
            ['expected_delivery', '<', current_time.toISOString()],
            ['state', 'not in', ['delivered', 'cancelled', 'returned']]
        ];

        // لا نضيف فلترات التاريخ أو البحث هنا

        await this.action.doAction({
            type: 'ir.actions.act_window',
            name: '⚠️ All Overdue Deliveries',
            res_model: 'shipment.order',
            views: [[false, 'list'], [false, 'form']],
            domain: domain,
            target: 'current',
            context: {
                search_default_sort_by_expected_delivery: 1,
                create: false,
                default_highlight_overdue: true,
            }
        });
    } catch (error) {
        console.error('Error viewing overdue shipments:', error);
        this.notification.add("Error loading overdue shipments", {
            type: "danger",
        });
    }
}

    async viewAllShipments() {
        try {
            this.saveFilters();
            const dateRange = this.getDateRange();
            let domain = [
                ['create_date', '>=', dateRange.from],
                ['create_date', '<=', dateRange.to]
            ];

            if (this.state.searchTerm) {
                const searchDomain = [
                    '|', '|', '|',
                    ['order_number', 'ilike', this.state.searchTerm],
                    ['tracking_number', 'ilike', this.state.searchTerm],
                    ['sender_id.name', 'ilike', this.state.searchTerm],
                    ['recipient_id.name', 'ilike', this.state.searchTerm]
                ];
                domain = ['&', ...domain, ...searchDomain];
            }

            await this.action.doAction({
                type: 'ir.actions.act_window',
                name: 'All Filtered Shipments',
                res_model: 'shipment.order',
                views: [[false, 'list'], [false, 'form']],
                domain: domain,
                target: 'current',
            });
        } catch (error) {
            console.error('Error:', error);
        }
    }
}

registry.category("actions").add("shipment_dashboard_client", ShipmentDashboard);