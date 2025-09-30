odoo.define('payment_cod.fee_display', [], function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var PaymentForm = require('payment.payment_form');

    // Override the payment form to handle COD
    PaymentForm.include({
        /**
         * Override to handle COD payment processing
         */
        _processTokenFlow: function (providerCode, tokenId, flowType) {
            if (providerCode === 'cod') {
                console.log('Processing COD payment flow');
                return this._processCODPayment();
            }
            return this._super.apply(this, arguments);
        },

        /**
         * Process COD payment
         */
        _processCODPayment: function() {
            var self = this;
            console.log('Starting COD payment process');

            // Get the transaction route from the selected option
            var $selectedOption = this.$('input[name="o_payment_radio"]:checked').closest('[data-payment-option-id]');
            var transactionRoute = $selectedOption.data('payment-option-id');

            if (!transactionRoute) {
                console.error('No transaction route found for COD');
                return Promise.reject('No transaction route');
            }

            // Call the transaction route to create/get the transaction
            return this._rpc({
                route: transactionRoute,
                params: {},
            }).then(function(result) {
                console.log('COD transaction created:', result);

                // Handle the inline form if present
                if (result.inline_form_html) {
                    // Create a temporary container for the form
                    var $tempDiv = $('<div>').html(result.inline_form_html);

                    // Find the form in the HTML
                    var $form = $tempDiv.find('form');

                    if ($form.length) {
                        // Append form to body temporarily
                        $form.hide().appendTo('body');

                        // Submit the form
                        console.log('Submitting COD feedback form');
                        $form.submit();

                        return new Promise(function(resolve) {
                            // Give it time to submit
                            setTimeout(resolve, 100);
                        });
                    }
                }

                // If no inline form, redirect directly
                if (result.redirect_url) {
                    window.location.href = result.redirect_url;
                }

                return result;
            }).catch(function(error) {
                console.error('Error processing COD payment:', error);
                throw error;
            });
        },

        /**
         * Override to check for COD provider
         */
        _prepareTransactionRouteParams: function() {
            var params = this._super.apply(this, arguments);

            var $selectedOption = this.$('input[name="o_payment_radio"]:checked').closest('.o_payment_option_card');
            var providerCode = $selectedOption.data('provider-code');

            if (providerCode === 'cod') {
                console.log('Preparing COD transaction params:', params);
            }

            return params;
        }
    });

    // Widget for COD inline forms
    publicWidget.registry.CODInlineForm = publicWidget.Widget.extend({
        selector: '#cod_payment_form',

        start: function() {
            var self = this;
            return this._super.apply(this, arguments).then(function() {
                console.log('COD inline form widget started');
                self._autoSubmit();
            });
        },

        _autoSubmit: function() {
            var self = this;

            // Check form has all required data
            var hasData = true;
            this.$('input[type="hidden"]').each(function() {
                var $input = $(this);
                if ($input.attr('name') !== 'csrf_token' && !$input.val()) {
                    console.warn('Missing value for:', $input.attr('name'));
                    hasData = false;
                }
            });

            if (hasData) {
                console.log('Auto-submitting COD form with data:', {
                    reference: this.$('[name="reference"]').val(),
                    amount: this.$('[name="amount"]').val(),
                    transaction_id: this.$('[name="transaction_id"]').val()
                });

                setTimeout(function() {
                    self.el.submit();
                }, 500);
            } else {
                console.error('Cannot submit COD form - missing data');
            }
        }
    });

    return {
        PaymentForm: PaymentForm,
        CODInlineForm: publicWidget.registry.CODInlineForm
    };
});