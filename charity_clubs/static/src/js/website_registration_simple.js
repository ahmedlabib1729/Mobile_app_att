/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

// Widget للسيدات
publicWidget.registry.CharityLadiesRegistration = publicWidget.Widget.extend({
    selector: '#ladiesRegistrationForm',
    events: {
        'submit': '_onSubmit',
        'change .file-upload': '_onFileChange',
        'click .remove-file': '_onRemoveFile',
    },

    start() {
        this._super(...arguments);
        console.log('Ladies registration widget initialized');

        // التحقق من وجود حقل lady_type
        this._validateLadyTypeField();
    },

    _validateLadyTypeField() {
        const ladyTypeField = this.$('select[name="lady_type"]');
        if (ladyTypeField.length === 0) {
            console.warn('Lady type field not found in form');
        } else {
            console.log('Lady type field found and ready');
            // إضافة تحقق عند تغيير القيمة
            ladyTypeField.on('change', (ev) => {
                const value = $(ev.currentTarget).val();
                if (!value) {
                    $(ev.currentTarget).addClass('is-invalid');
                } else {
                    $(ev.currentTarget).removeClass('is-invalid');
                }
            });
        }
    },

    _showLoading(show = true) {
        if (show) {
            const loadingDiv = $('<div>', {
                id: 'loadingOverlay',
                class: 'position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center',
                style: 'background: rgba(0,0,0,0.5); z-index: 9999;',
                html: `
                    <div class="bg-white rounded p-4 text-center">
                        <div class="spinner-border text-primary mb-3" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <div>جاري الإرسال...</div>
                    </div>
                `
            });
            $('body').append(loadingDiv);
        } else {
            $('#loadingOverlay').remove();
        }
    },

    _showMessage(type, title, text) {
        this._showLoading(false);

        const alertClass = type === 'error' ? 'alert-danger' : type === 'success' ? 'alert-success' : 'alert-info';
        const alertDiv = $('<div>', {
            class: `alert ${alertClass} alert-dismissible fade show position-fixed top-50 start-50 translate-middle`,
            style: 'z-index: 9999; min-width: 300px;',
            html: `
                <h5 class="alert-heading">${title}</h5>
                <p>${text}</p>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `
        });

        $('body').append(alertDiv);
        setTimeout(() => alertDiv.remove(), 5000);
    },

    _onFileChange(ev) {
        const input = ev.currentTarget;
        const fileId = input.id;
        const previewDiv = this.$(`#${fileId.replace('_file', '_preview')}`);

        if (input.files && input.files[0]) {
            const file = input.files[0];
            const fileName = file.name;
            const fileSize = (file.size / 1024 / 1024).toFixed(2);

            if (parseFloat(fileSize) > 5) {
                this._showMessage('error', 'خطأ', 'حجم الملف يجب أن يكون أقل من 5MB');
                input.value = '';
                return;
            }

            previewDiv.find('.file-name').text(`${fileName} (${fileSize} MB)`);
            previewDiv.show();
            this.$(input).parent().find('.file-upload-info').hide();
        }
    },

    _onRemoveFile(ev) {
        const targetId = this.$(ev.currentTarget).data('target');
        this.$(`#${targetId}`).val('');
        this.$(`#${targetId.replace('_file', '_preview')}`).hide();
        this.$(`#${targetId}`).parent().find('.file-upload-info').show();
    },

    _fileToBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = () => resolve(reader.result);
            reader.onerror = error => reject(error);
        });
    },

    _validateRequiredFields() {
        let isValid = true;
        const requiredFields = [
            'full_name', 'birth_date', 'mobile', 'whatsapp',
            'email', 'lady_type', 'id_card_file', 'passport_file', 'residence_file'
        ];

        requiredFields.forEach(fieldName => {
            const field = this.$(`[name="${fieldName}"]`);
            if (field.length > 0) {
                const value = field.val();
                if (!value || value.trim() === '') {
                    field.addClass('is-invalid');
                    isValid = false;

                    // إضافة رسالة خطأ مخصصة لحقل صفة السيدة
                    if (fieldName === 'lady_type') {
                        if (!field.next('.invalid-feedback').length) {
                            field.after('<div class="invalid-feedback">يجب اختيار صفة السيدة</div>');
                        }
                    }
                } else {
                    field.removeClass('is-invalid');
                    field.next('.invalid-feedback').remove();
                }
            }
        });

        return isValid;
    },

    async _onSubmit(ev) {
        ev.preventDefault();
        console.log('Form submission started');

        try {
            // التحقق من الحقول المطلوبة
            if (!this._validateRequiredFields()) {
                this._showMessage('error', 'خطأ', 'يرجى ملء جميع الحقول المطلوبة');
                return;
            }

            const formData = new FormData(this.el);
            const data = {};
            const programIds = [];

            // جمع البيانات
            for (let [key, value] of formData.entries()) {
                if (key === 'program_ids') {
                    programIds.push(parseInt(value));
                } else if (!key.endsWith('_file')) {
                    data[key] = value;
                }
            }

            // التحقق الخاص من lady_type
            if (!data.lady_type || data.lady_type === '') {
                this._showMessage('error', 'خطأ', 'يجب اختيار صفة السيدة');
                return;
            }

            // التحقق من القيم المسموحة لـ lady_type
            const allowedLadyTypes = ['pioneer', 'volunteer', 'member'];
            if (!allowedLadyTypes.includes(data.lady_type)) {
                this._showMessage('error', 'خطأ', 'قيمة غير صحيحة لصفة السيدة');
                return;
            }

            if (programIds.length > 0) {
                data['program_ids'] = JSON.stringify(programIds);
            }

            // إظهار رسالة التحميل
            this._showLoading(true);

            // معالجة الملفات
            const fileFields = ['id_card_file', 'passport_file', 'residence_file'];

            for (const fieldName of fileFields) {
                const fileInput = document.getElementById(fieldName);
                if (fileInput && fileInput.files[0]) {
                    const base64 = await this._fileToBase64(fileInput.files[0]);
                    data[fieldName] = base64.split(',')[1];
                    data[fieldName + '_name'] = fileInput.files[0].name;
                }
            }

            console.log('Sending data to server with lady_type:', data.lady_type);

            // إعداد البيانات بصيغة JSON-RPC لـ Odoo
            const jsonRpcData = {
                jsonrpc: "2.0",
                method: "call",
                params: data,
                id: Math.floor(Math.random() * 1000000000)
            };

            // إرسال البيانات
            $.ajax({
                url: '/registration/submit/ladies',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify(jsonRpcData),
                dataType: 'json',
                success: (response) => {
                    console.log('Response received:', response);

                    if (response.error) {
                        console.error('Server error:', response.error);
                        this._showMessage('error', 'خطأ', response.error.message || response.error.data?.message || 'حدث خطأ في الخادم');
                        return;
                    }

                    const result = response.result;
                    this._handleRegistrationResponse(result);
                },
                error: (xhr, status, error) => {
                    console.error('AJAX Error:', error);
                    console.error('Response:', xhr.responseText);

                    let errorMessage = 'حدث خطأ في الاتصال';
                    try {
                        const errorResponse = JSON.parse(xhr.responseText);
                        if (errorResponse.error) {
                            errorMessage = errorResponse.error.message || errorResponse.error.data?.message || errorMessage;
                        }
                    } catch (e) {
                        // ignore JSON parse errors
                    }

                    this._showMessage('error', 'خطأ', errorMessage);
                }
            });

        } catch (error) {
            console.error('Error:', error);
            this._showMessage('error', 'خطأ', error.message || 'حدث خطأ في المعالجة');
        }
    },

    _handleRegistrationResponse(response) {
        this._showLoading(false);

        if (!response.success) {
            this._showMessage('error', 'خطأ', response.error || 'حدث خطأ في الحجز');
            return;
        }

        console.log('Registration response:', response);

        // التحقق من وجود رابط الدفع
        if (response.payment_url) {
            this._showMessage('success', 'تم التسجيل بنجاح', 'سيتم توجيهك لصفحة الدفع...');

            // حفظ معلومات الحجز في localStorage
            localStorage.setItem('charity_booking_id', response.booking_id);
            if (response.invoice_id) {
                localStorage.setItem('charity_invoice_id', response.invoice_id);
                localStorage.setItem('charity_invoice_name', response.invoice_name);
                localStorage.setItem('charity_amount', response.amount);
            }

            // التوجيه لصفحة دفع Odoo الافتراضية
            setTimeout(() => {
                console.log('Redirecting to:', response.payment_url);
                window.location.href = response.payment_url;
            }, 1500);
        }
        // التحقق من وجود فاتورة بطريقة أخرى
        else if (response.invoice_id && response.invoice) {
            // بناء رابط الدفع يدوياً
            const paymentUrl = `/my/invoices/${response.invoice.invoice_id}?access_token=${response.invoice.access_token}`;

            this._showMessage('success', 'تم التسجيل بنجاح', 'سيتم توجيهك لصفحة الدفع...');

            setTimeout(() => {
                console.log('Redirecting to invoice:', paymentUrl);
                window.location.href = paymentUrl;
            }, 1500);
        }
        // التحقق من has_invoice القديم
        else if (response.has_invoice && response.invoice) {
            // متوافق مع الكود القديم
            const paymentUrl = `/my/invoices/${response.invoice.invoice_id}?access_token=${response.invoice.access_token}`;

            this._showMessage('success', 'تم التسجيل بنجاح', 'سيتم توجيهك لصفحة الدفع...');

            setTimeout(() => {
                console.log('Redirecting to invoice (legacy):', paymentUrl);
                window.location.href = paymentUrl;
            }, 1500);
        }
        else {
            // لا توجد فاتورة - التوجيه مباشرة لصفحة النجاح
            console.log('No invoice found, redirecting to success page');
            this._showMessage('success', 'تم التسجيل بنجاح', 'سيتم توجيهك الآن...');
            setTimeout(() => {
                window.location.href = `/registration/success/ladies/${response.booking_id}`;
            }, 1500);
        }
    }
});

// Widget للنوادي مع معالجة رفع الملفات والمراجعة
publicWidget.registry.CharityClubRegistration = publicWidget.Widget.extend({
    selector: '#clubRegistrationForm',
    events: {
        'submit': '_onSubmit',
        'change #hasHealth': '_onHealthChange',
        'change .file-upload': '_onFileChange',
        'click .remove-file': '_onRemoveFile',
    },

    start() {
        this._super(...arguments);
        console.log('Club registration widget initialized');
    },

    _onHealthChange(ev) {
        const $checkbox = this.$(ev.currentTarget);
        const $healthDetails = this.$('#healthDetails');

        if ($checkbox.is(':checked')) {
            $healthDetails.slideDown();
        } else {
            $healthDetails.slideUp();
        }
    },

    _onFileChange(ev) {
        const input = ev.currentTarget;
        const fileId = input.id;
        const previewDiv = this.$(`#${fileId.replace('_file', '_preview')}`);

        if (input.files && input.files[0]) {
            const file = input.files[0];
            const fileName = file.name;
            const fileSize = (file.size / 1024 / 1024).toFixed(2);

            if (parseFloat(fileSize) > 5) {
                this._showMessage('error', 'خطأ', 'حجم الملف يجب أن يكون أقل من 5MB');
                input.value = '';
                return;
            }

            previewDiv.find('.file-name').text(`${fileName} (${fileSize} MB)`);
            previewDiv.show();
            this.$(input).parent().find('.file-upload-info').hide();
        }
    },

    _onRemoveFile(ev) {
        const targetId = this.$(ev.currentTarget).data('target');
        this.$(`#${targetId}`).val('');
        this.$(`#${targetId.replace('_file', '_preview')}`).hide();
        this.$(`#${targetId}`).parent().find('.file-upload-info').show();
    },

    _fileToBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = () => resolve(reader.result);
            reader.onerror = error => reject(error);
        });
    },

    _showLoading(show = true) {
        if (show) {
            const loadingDiv = $('<div>', {
                id: 'loadingOverlay',
                class: 'position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center',
                style: 'background: rgba(0,0,0,0.5); z-index: 9999;',
                html: `
                    <div class="bg-white rounded p-4 text-center">
                        <div class="spinner-border text-primary mb-3" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <div>جاري الإرسال...</div>
                    </div>
                `
            });
            $('body').append(loadingDiv);
        } else {
            $('#loadingOverlay').remove();
        }
    },

    _showMessage(type, title, text) {
        this._showLoading(false);

        const alertClass = type === 'error' ? 'alert-danger' : type === 'success' ? 'alert-success' : type === 'warning' ? 'alert-warning' : 'alert-info';
        const alertDiv = $('<div>', {
            class: `alert ${alertClass} alert-dismissible fade show position-fixed top-50 start-50 translate-middle`,
            style: 'z-index: 9999; min-width: 300px;',
            html: `
                <h5 class="alert-heading">${title}</h5>
                <p>${text}</p>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `
        });

        $('body').append(alertDiv);
        setTimeout(() => alertDiv.remove(), 5000);
    },

    async _onSubmit(ev) {
        ev.preventDefault();

        try {
            const formData = new FormData(this.el);
            const data = {};

            // جمع البيانات من الفورم
            for (let [key, value] of formData.entries()) {
                if (!key.endsWith('_file')) {
                    data[key] = value;
                }
            }

            this._showLoading(true);

            // معالجة الملفات المرفوعة
            const fileFields = ['id_front_file', 'id_back_file'];

            for (const fieldName of fileFields) {
                const fileInput = document.getElementById(fieldName);
                if (fileInput && fileInput.files[0]) {
                    const base64 = await this._fileToBase64(fileInput.files[0]);
                    data[fieldName] = base64.split(',')[1];
                    data[fieldName + '_name'] = fileInput.files[0].name;
                }
            }

            console.log('Sending data with files to server');

            // إعداد البيانات بصيغة JSON-RPC لـ Odoo
            const jsonRpcData = {
                jsonrpc: "2.0",
                method: "call",
                params: data,
                id: Math.floor(Math.random() * 1000000000)
            };

            // إرسال البيانات
            $.ajax({
                url: '/registration/submit/club',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify(jsonRpcData),
                dataType: 'json',
                success: (response) => {
                    console.log('Response received:', response);

                    if (response.error) {
                        console.error('Server error:', response.error);
                        this._showMessage('error', 'خطأ', response.error.message || response.error.data?.message || 'حدث خطأ');
                        return;
                    }

                    const result = response.result;
                    this._handleRegistrationResponse(result);
                },
                error: (xhr, status, error) => {
                    console.error('AJAX Error:', error);
                    console.error('Response:', xhr.responseText);

                    let errorMessage = 'حدث خطأ في الاتصال';
                    try {
                        const errorResponse = JSON.parse(xhr.responseText);
                        if (errorResponse.error) {
                            errorMessage = errorResponse.error.message || errorResponse.error.data?.message || errorMessage;
                        }
                    } catch (e) {
                        // ignore JSON parse errors
                    }

                    this._showMessage('error', 'خطأ', errorMessage);
                }
            });

        } catch (error) {
            console.error('Error:', error);
            this._showMessage('error', 'خطأ', error.message || 'حدث خطأ في المعالجة');
        }
    },

    _handleRegistrationResponse(response) {
        this._showLoading(false);

        if (!response.success) {
            this._showMessage('error', 'خطأ', response.error || 'حدث خطأ في التسجيل');
            return;
        }

        console.log('Registration response:', response);

        // التحقق من حالة المراجعة
        if (response.needs_review) {
            // التسجيل يحتاج مراجعة
            this._showMessage('warning', 'يحتاج مراجعة', response.message);

            // عرض رسالة تفصيلية
            const reviewAlert = $('<div>', {
                class: 'alert alert-warning alert-dismissible fade show position-fixed',
                style: 'top: 100px; left: 50%; transform: translateX(-50%); z-index: 9999; max-width: 600px; width: 90%;',
                html: `
                    <h4 class="alert-heading">
                        <i class="fa fa-exclamation-triangle"></i> التسجيل يحتاج مراجعة الإدارة
                    </h4>
                    <hr>
                    <p><strong>تم استلام طلب التسجيل بنجاح</strong></p>
                    <p>نظراً لوجود تعارض في البيانات، سيتم مراجعة الطلب من قبل الإدارة.</p>
                    <p class="mb-0">سيتم التواصل معك قريباً لتأكيد البيانات.</p>
                    <hr>
                    <div class="d-flex justify-content-between">
                        <span>رقم التسجيل: <strong>${response.registration_id}</strong></span>
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                `
            });

            $('body').append(reviewAlert);

            // التوجيه لصفحة خاصة بالمراجعة
            setTimeout(() => {
                window.location.href = `/registration/pending/club/${response.registration_id}`;
            }, 5000);
        }
        // التحقق من وجود فاتورة ورابط دفع
        else if (response.payment_url && response.has_invoice) {
            this._showMessage('success', 'تم التسجيل بنجاح', 'سيتم توجيهك لصفحة الدفع...');

            // حفظ معلومات التسجيل
            localStorage.setItem('charity_registration_id', response.registration_id);
            if (response.invoice_id) {
                localStorage.setItem('charity_invoice_id', response.invoice_id);
                localStorage.setItem('charity_invoice_name', response.invoice_name);
                localStorage.setItem('charity_amount', response.amount);
            }

            // التوجيه لصفحة الدفع
            setTimeout(() => {
                console.log('Redirecting to payment:', response.payment_url);
                window.location.href = response.payment_url;
            }, 1500);
        }
        else {
            // لا توجد فاتورة - التوجيه لصفحة النجاح
            this._showMessage('success', 'تم التسجيل بنجاح', 'سيتم توجيهك الآن...');
            setTimeout(() => {
                window.location.href = `/registration/success/club/${response.registration_id}`;
            }, 1500);
        }
    }
});

// Widget للتحقق من حالة الدفع بعد العودة من Odoo Portal
publicWidget.registry.CharityPaymentStatus = publicWidget.Widget.extend({
    selector: '.charity-registration-success',

    start() {
        this._super(...arguments);

        // التحقق من localStorage للحصول على معلومات الحجز
        const bookingId = localStorage.getItem('charity_booking_id');
        const invoiceId = localStorage.getItem('charity_invoice_id');

        if (bookingId) {
            // مسح البيانات من localStorage
            localStorage.removeItem('charity_booking_id');
            localStorage.removeItem('charity_invoice_id');
            localStorage.removeItem('charity_invoice_name');
            localStorage.removeItem('charity_amount');

            console.log('Payment completed for booking:', bookingId);
        }

        // نفس الشيء للتسجيلات
        const registrationId = localStorage.getItem('charity_registration_id');
        if (registrationId) {
            localStorage.removeItem('charity_registration_id');
            localStorage.removeItem('charity_invoice_id');
            localStorage.removeItem('charity_invoice_name');
            localStorage.removeItem('charity_amount');

            console.log('Payment completed for registration:', registrationId);
        }
    }
});

// Widget لصفحة تأكيد الدفع
publicWidget.registry.CharityPaymentConfirmation = publicWidget.Widget.extend({
    selector: '.payment-confirmation-page',
    events: {
        'click .check-payment-status': '_onCheckPaymentStatus',
    },

    start() {
        this._super(...arguments);

        // التحقق التلقائي من حالة الدفع كل 5 ثوان
        this.autoCheckInterval = setInterval(() => {
            this._checkPaymentStatus();
        }, 5000);
    },

    destroy() {
        if (this.autoCheckInterval) {
            clearInterval(this.autoCheckInterval);
        }
        this._super(...arguments);
    },

    _onCheckPaymentStatus(ev) {
        ev.preventDefault();
        this._checkPaymentStatus();
    },

    _checkPaymentStatus() {
        const bookingId = this.$el.data('booking-id');

        if (!bookingId) return;

        $.ajax({
            url: `/registration/check-payment/${bookingId}`,
            type: 'GET',
            success: (data) => {
                if (data.paid) {
                    // تم الدفع - إعادة تحميل الصفحة
                    window.location.reload();
                }
            },
            error: (xhr, status, error) => {
                console.error('Error checking payment status:', error);
            }
        });
    }
});

console.log('Charity registration widgets loaded with lady_type support');