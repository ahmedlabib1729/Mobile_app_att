/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import "@payment/js/payment_form";

// Patch the payment form to handle COD
patch(odoo.__DEBUG__.services["payment.payment_form"], {
    _processRedirectFlow: async function (providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        // If COD, skip redirect processing
        if (paymentMethodCode === 'cod' || providerCode === 'cod') {
            window.location.href = '/payment/status';
            return;
        }

        // Check if redirectForm exists before trying to use it
        const redirectForm = document.getElementById('payment_redirect_form');
        if (!redirectForm && paymentMethodCode !== 'cod') {
            console.warn('Redirect form not found, redirecting to status page');
            window.location.href = '/payment/status';
            return;
        }

        // Call parent for other payment methods
        return this._super(...arguments);
    }
});