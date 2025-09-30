odoo.define('payment_cod.payment_form', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var core = require('web.core');
    var ajax = require('web.ajax');
    var _t = core._t;

    publicWidget.registry.PaymentFormCOD = publicWidget.Widget.extend({
        selector: '.o_payment_form',
        events: {
            'change input[name="o_payment_radio"]': '_onPaymentMethodChange',
            'click button[name="o_payment_submit_button"]': '_onPaymentSubmit',
        },

        /**
         * @override
         */
        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                console.log('COD Payment Form Widget initialized');
                self._setupCODForm();
            });
        },

        /**
         * Setup COD form handling
         */
        _setupCODForm: function() {
            // Check if we have a COD inline form
            var codForm = document.getElementById('cod_payment_form');
            if (codForm) {
                console.log('COD inline form found, preparing submission');
                // The form will auto-submit via the template script
            }
        },

        /**
         * Handle payment method change
         */
        _onPaymentMethodChange: function (ev) {
            var $radio = $(ev.currentTarget);
            var $option = $radio.closest('.o_payment_option_card');
            var providerCode = $option.data('provider-code');

            console.log('Payment method changed to:', providerCode);

            if (providerCode === 'cod') {
                console.log('COD payment method selected');

                // Add visual indicator
                $('.o_payment_option_card').removeClass('border-success');
                $option.addClass('border-success');
            }
        },

        /**
         * Handle payment submission
         */
        _onPaymentSubmit: function(ev) {
            var $checkedRadio = this.$('input[name="o_payment_radio"]:checked');
            var $option = $checkedRadio.closest('.o_payment_option_card');
            var providerCode = $option.data('provider-code');

            if (providerCode === 'cod') {
                console.log('Processing COD payment submission');

                // Check if we have the transaction ID
                var transactionRoute = $option.data('payment-option-id');
                if (transactionRoute) {
                    // Extract transaction ID from route
                    var match = transactionRoute.match(/\/(\d+)$/);
                    if (match && match[1]) {
                        var transactionId = match[1];
                        console.log('COD Transaction ID:', transactionId);

                        // Store transaction ID for feedback
                        sessionStorage.setItem('cod_transaction_id', transactionId);
                    }
                }
            }
        },
    });

    // Additional handler for COD form submission
    $(document).ready(function() {
        // Monitor for COD forms
        var checkCODForm = function() {
            var codForm = document.getElementById('cod_payment_form');
            if (codForm && !codForm.dataset.processed) {
                codForm.dataset.processed = 'true';

                // Ensure all fields have values
                var inputs = codForm.querySelectorAll('input[type="hidden"]');
                inputs.forEach(function(input) {
                    if (!input.value && input.name !== 'csrf_token') {
                        console.warn('Empty value for', input.name);
                    }
                });

                // Log submission details
                console.log('COD Form ready for submission:', {
                    reference: codForm.querySelector('[name="reference"]')?.value,
                    amount: codForm.querySelector('[name="amount"]')?.value,
                    transaction_id: codForm.querySelector('[name="transaction_id"]')?.value,
                });
            }
        };

        // Check periodically for dynamically loaded forms
        setInterval(checkCODForm, 1000);
    });

    return publicWidget.registry.PaymentFormCOD;
});