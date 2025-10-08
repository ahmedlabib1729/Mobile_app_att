odoo.define('dynamic_sales_report.ReportAction', function (require) {
    "use strict";

    const AbstractAction = require('web.AbstractAction');
    const core = require('web.core');
    const QWeb = core.qweb;

    const SalesReportAction = AbstractAction.extend({
        template: 'SalesReportFullscreen',

        init: function(parent, action) {
            this._super.apply(this, arguments);
            this.report_data = action.params.report_data || {};
        },

        start: function () {
            this.$el.html(this.report_data.html || '<p>Loading...</p>');
            return this._super.apply(this, arguments);
        },
    });

    core.action_registry.add('sales_report_action', SalesReportAction);
    return SalesReportAction;
});