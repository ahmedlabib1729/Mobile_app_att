/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";

const CODPaymentForm = publicWidget.Widget.extend({
    selector: '.o_payment_form',
    events: {
        'change input[name="o_payment_radio"]': '_onPaymentMethodChange',
    },

    /**
     * @override
     */
    start() {
        this._super(...arguments);
        return Promise.resolve();
    },

    /**
     * Handle payment method selection
     */
    _onPaymentMethodChange(ev) {
        const selectedRadio = ev.currentTarget;
        const paymentOptionCode = selectedRadio.dataset.paymentOptionCode;

        if (paymentOptionCode === 'cod') {
            this._displayCODInfo();
        } else {
            this._hideCODInfo();
        }
    },

    /**
     * Display COD information
     */
    _displayCODInfo() {
        // Remove existing info
        this._hideCODInfo();

        // Create info element
        const infoDiv = document.createElement('div');
        infoDiv.className = 'alert alert-info mt-2 cod-payment-info';
        infoDiv.innerHTML = `
            <i class="fa fa-info-circle"></i>
            ${_t('Payment will be collected upon delivery. Please have the exact amount ready.')}
        `;

        // Find selected payment option and insert info after it
        const selectedOption = this.el.querySelector('input[name="o_payment_radio"]:checked');
        if (selectedOption) {
            const optionContainer = selectedOption.closest('.o_payment_option_card');
            if (optionContainer) {
                optionContainer.parentNode.insertBefore(infoDiv, optionContainer.nextSibling);
            }
        }
    },

    /**
     * Hide COD information
     */
    _hideCODInfo() {
        const infoDiv = this.el.querySelector('.cod-payment-info');
        if (infoDiv) {
            infoDiv.remove();
        }
    }
});

publicWidget.registry.CODPaymentForm = CODPaymentForm;

export default CODPaymentForm;