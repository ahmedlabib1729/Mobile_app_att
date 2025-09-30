odoo.define('payment_cod.fee_calculator', [], function (require) {
    'use strict';

    document.addEventListener('DOMContentLoaded', function() {
        if (!window.location.pathname.includes('/shop/payment')) return;

        // Calculate and display COD fee
        function calculateCODFee() {
            var codCards = document.querySelectorAll('[data-provider-code="cod"]');

            codCards.forEach(function(card) {
                // Call backend to get fee
                fetch('/payment/cod/calculate_fee', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        jsonrpc: '2.0',
                        method: 'call',
                        params: {
                            provider_id: 1,
                            amount: getOrderAmount(),
                            currency_id: 128,
                            country_id: null
                        },
                        id: 1
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.result && data.result.fee > 0) {
                        displayFee(card, data.result.fee_formatted);
                    }
                });
            });
        }

        function getOrderAmount() {
            var total = 0;
            document.querySelectorAll('.monetary_field').forEach(function(elem) {
                var val = parseFloat(elem.textContent.replace(/[^\d.]/g, ''));
                if (val > total) total = val;
            });
            return total || 100;
        }

        function displayFee(card, feeText) {
            var existing = card.querySelector('.cod-fee-badge');
            if (!existing) {
                var badge = document.createElement('div');
                badge.className = 'cod-fee-badge text-warning mt-2';
                badge.innerHTML = '<strong>رسوم إضافية: ' + feeText + '</strong>';
                card.appendChild(badge);
            }
        }

        // Run calculation
        setTimeout(calculateCODFee, 2000);
    });

    return {};
});