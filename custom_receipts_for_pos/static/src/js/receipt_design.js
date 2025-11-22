/** @odoo-module */
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { patch } from "@web/core/utils/patch";
import { useState, Component, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

patch(OrderReceipt.prototype, {
    setup(){
        super.setup();
        this.state = useState({
            template: true,
        })
        this.pos = useState(useService("pos"));
    },

    get templateProps() {
        return {
            data: this.props.data,
            order: this.pos.get_order(),
            receipt: this.pos.get_order().export_for_printing(),
            orderlines: this.props.data.orderlines,
            paymentlines: this.pos.get_order().export_for_printing().paymentlines
        };
    },

    get templateComponent() {
        var mainRef = this;
        return class extends Component {
            setup() {}
            // ✅ تأكد إن الـ template صحيح
            static template = xml`
                <div class="pos-receipt">
                    ${mainRef.pos.config.design_receipt || '<div>No design selected</div>'}
                </div>
            `;
        };
    },

    get isTrue() {
        // ✅ تحقق من وجود config وتفعيل custom receipt
        if (!this.env.services.pos.config ||
            this.env.services.pos.config.is_custom_receipt == false ||
            !this.pos.config.design_receipt) {
            return false;
        }
        return true;
    }
});