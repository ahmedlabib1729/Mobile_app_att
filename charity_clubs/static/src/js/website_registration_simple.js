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

// في ملف website_registration_simple.js
// ابحث عن method _onSubmit في CharityLadiesRegistration widget
// وعدلها كالتالي:

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

        // إضافة معالجة booking_mode والورش - هنا المكان الصحيح
        const bookingMode = $('input[name="booking_mode"]').val();
        if (bookingMode) {
            data['booking_mode'] = bookingMode;

            // إذا كان النوع ورشة، أضف معرف الورشة المختارة
            if (bookingMode === 'workshop' && $('input[name="workshop_id"]:checked').length > 0) {
                data['workshop_id'] = $('input[name="workshop_id"]:checked').val();
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

        // فقط أضف program_ids إذا كان النوع programs
        if (bookingMode === 'programs' && programIds.length > 0) {
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

        console.log('Sending data to server with booking_mode:', data.booking_mode);
        if (data.workshop_id) {
            console.log('Selected workshop:', data.workshop_id);
        }

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
// في ملف website_registration_simple.js
// استبدل الـ Widget الخاص بالنوادي بهذا:

publicWidget.registry.CharityClubRegistration = publicWidget.Widget.extend({
    selector: '#clubRegistrationForm',
    events: {
        'submit': '_onSubmit',
        'change #hasHealth': '_onHealthChange',
        'change #esaadDiscount': '_onEsaadChange',
        'change .file-upload': '_onFileChange',
        'click .remove-file': '_onRemoveFile',
    },

    start() {
        this._super(...arguments);
        console.log('Club registration widget initialized - Two-Step Version');

        // متغير لحفظ validation token
        this.validationToken = null;
        this.validationExpiry = null;
    },

    // الدوال الموجودة تبقى كما هي
    _onHealthChange(ev) {
    const $checkbox = this.$(ev.currentTarget);
    const $healthDetails = this.$('#healthDetails');
    const $healthTextarea = this.$('textarea[name="health_requirements"]');

    if ($checkbox.is(':checked')) {
        $healthDetails.slideDown();
        // جعل الحقل مطلوب
        $healthTextarea.attr('required', 'required');
    } else {
        $healthDetails.slideUp();
        // إزالة الإلزامية ومسح القيمة
        $healthTextarea.removeAttr('required');
        $healthTextarea.val('');
        // إزالة أي رسائل خطأ
        $healthTextarea.removeClass('is-invalid');
        $healthTextarea.next('.invalid-feedback').remove();
    }
},

    _onEsaadChange(ev) {
        const $checkbox = this.$(ev.currentTarget);
        const $esaadDetails = this.$('#esaadDetails');
        if ($checkbox.is(':checked')) {
            $esaadDetails.slideDown();
            this.$('#esaad_card_file').attr('required', 'required');
        } else {
            $esaadDetails.slideUp();
            this.$('#esaad_card_file').removeAttr('required');
            this.$('#esaad_card_file').val('');
            this.$('#esaad_card_preview').hide();
            this.$('#esaad_card_file').parent().find('.file-upload-info').show();
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

    _validateRequiredFields() {
    let isValid = true;

    // التحقق من الحقول المطلوبة العادية
    this.$('input[required], select[required], textarea[required]').each(function() {
        if (!$(this).is(':visible')) return; // تجاهل الحقول المخفية

        const value = $(this).val();
        if (!value || value.trim() === '') {
            $(this).addClass('is-invalid');
            isValid = false;
        } else {
            $(this).removeClass('is-invalid');
        }
    });

    // === التحقق الخاص بالمتطلبات الصحية ===
    if (this.$('#hasHealth').is(':checked')) {
        const healthDetails = this.$('textarea[name="health_requirements"]');
        const healthValue = healthDetails.val();

        if (!healthValue || healthValue.trim() === '') {
            healthDetails.addClass('is-invalid');

            // إضافة رسالة خطأ مخصصة
            if (!healthDetails.next('.invalid-feedback').length) {
                healthDetails.after(
                    '<div class="invalid-feedback d-block">يجب كتابة تفاصيل المتطلبات الصحية عند تحديد وجودها</div>'
                );
            }

            this._showMessage('error', 'خطأ', 'يجب كتابة تفاصيل المتطلبات الصحية أو إلغاء تحديد الخيار');
            isValid = false;
        } else {
            healthDetails.removeClass('is-invalid');
            healthDetails.next('.invalid-feedback').remove();
        }
    }

    // التحقق الخاص بخصم إسعاد
    if (this.$('#esaadDiscount').is(':checked')) {
        const esaadFile = this.$('#esaad_card_file')[0];
        if (!esaadFile || !esaadFile.files || !esaadFile.files[0]) {
            this.$('#esaad_card_file').addClass('is-invalid');
            this._showMessage('error', 'خطأ', 'يجب رفع صورة بطاقة إسعاد عند طلب الخصم');
            isValid = false;
        }
    }

    return isValid;
},

    // دالة جديدة لعرض التقدم
    _showProgress(step, message) {
        const progressHtml = `
            <div id="registrationProgress" class="position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center"
                 style="background: rgba(0,0,0,0.7); z-index: 10000;">
                <div class="bg-white rounded p-4 text-center" style="min-width: 350px;">
                    <div class="progress mb-3" style="height: 25px;">
                        <div class="progress-bar progress-bar-striped progress-bar-animated"
                             role="progressbar"
                             style="width: ${step}%">
                            ${step}%
                        </div>
                    </div>
                    <h5>${message}</h5>
                    <div class="spinner-border text-primary mt-3" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </div>
            </div>
        `;

        $('#registrationProgress').remove();
        $('body').append(progressHtml);
    },

    _hideProgress() {
        $('#registrationProgress').fadeOut(300, function() {
            $(this).remove();
        });
    },

    _showLoading(show = true, message = 'جاري المعالجة...') {
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
                        <div>${message}</div>
                    </div>
                `
            });
            $('body').append(loadingDiv);
        } else {
            $('#loadingOverlay').remove();
        }
    },

    _showMessage(type, title, text, duration = 5000) {
        this._hideProgress();
        this._showLoading(false);

        const alertClass = type === 'error' ? 'alert-danger' :
                          type === 'success' ? 'alert-success' :
                          type === 'warning' ? 'alert-warning' : 'alert-info';

        const alertDiv = $('<div>', {
            class: `alert ${alertClass} alert-dismissible fade show position-fixed`,
            style: 'top: 20px; left: 50%; transform: translateX(-50%); z-index: 9999; min-width: 400px; max-width: 600px;',
            html: `
                <h5 class="alert-heading">${title}</h5>
                <p>${text}</p>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `
        });

        $('body').append(alertDiv);
        if (duration > 0) {
            setTimeout(() => alertDiv.remove(), duration);
        }
    },

    // دالة جديدة لعرض أخطاء الحقول
    _displayFieldErrors(errors) {
        // مسح الأخطاء السابقة
        this.$('.is-invalid').removeClass('is-invalid');
        this.$('.invalid-feedback').remove();

        // عرض الأخطاء الجديدة
        Object.keys(errors).forEach(fieldName => {
            const field = this.$(`[name="${fieldName}"]`);
            if (field.length > 0) {
                field.addClass('is-invalid');

                // إضافة رسالة الخطأ
                const errorDiv = $('<div>', {
                    class: 'invalid-feedback d-block',
                    text: errors[fieldName]
                });

                // وضع رسالة الخطأ في المكان المناسب
                if (field.parent().hasClass('form-check')) {
                    field.parent().after(errorDiv);
                } else {
                    field.after(errorDiv);
                }
            }
        });

        // التمرير لأول خطأ
        const firstError = this.$('.is-invalid').first();
        if (firstError.length) {
            $('html, body').animate({
                scrollTop: firstError.offset().top - 100
            }, 500);
        }
    },

    // دالة جديدة للتحقق من البيانات (Step 1)
    async _validateRegistrationData(formData) {
        try {
            console.log('Starting validation step...');

            const idNumber = formData.id_number;
            const termId = formData.term_id;

            if (idNumber && termId) {
                // يمكن إضافة استدعاء AJAX للتحقق من التكرار
                console.log('Checking for duplicate registration...');
            }
            // إعداد البيانات للvalidation
            const validationData = {
                jsonrpc: "2.0",
                method: "call",
                params: formData,
                id: Math.floor(Math.random() * 1000000000)
            };

            // إرسال طلب validation
            const response = await $.ajax({
                url: '/registration/validate/club',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify(validationData),
                dataType: 'json'
            });

            if (response.error) {
                console.error('Validation server error:', response.error);
                return {
                    success: false,
                    errors: {
                        general: response.error.message || 'خطأ في التحقق من البيانات'
                    }
                };
            }

            const result = response.result;
            console.log('Validation result:', result);

            if (!result.success) {
                return {
                    success: false,
                    errors: result.errors || {general: 'فشل التحقق من البيانات'}
                };
            }

            // حفظ token والوقت
            this.validationToken = result.validation_token;
            this.validationExpiry = new Date(result.expires_at);

            // عرض التحذيرات إن وجدت
            if (result.warnings && result.warnings.length > 0) {
                result.warnings.forEach(warning => {
                    this._showMessage('warning', 'تنبيه', warning, 3000);
                });
            }

            return {
                success: true,
                token: result.validation_token,
                expires_at: result.expires_at
            };

        } catch (error) {
            console.error('Validation error:', error);
            return {
                success: false,
                errors: {
                    general: 'خطأ في الاتصال بالخادم'
                }
            };
        }
    },

    // دالة جديدة لإرسال البيانات مع التوكن (Step 2)
    async _submitWithToken(formData, token) {
        try {
            console.log('Submitting registration with token...');

            // إضافة التوكن للبيانات
            formData.validation_token = token;

            const submitData = {
                jsonrpc: "2.0",
                method: "call",
                params: formData,
                id: Math.floor(Math.random() * 1000000000)
            };

            const response = await $.ajax({
                url: '/registration/submit/club',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify(submitData),
                dataType: 'json'
            });

            if (response.error) {
                console.error('Submit error:', response.error);
                return {
                    success: false,
                    error: response.error.message || 'خطأ في حفظ التسجيل'
                };
            }

            return response.result;

        } catch (error) {
            console.error('Submit error:', error);
            return {
                success: false,
                error: 'خطأ في الاتصال بالخادم'
            };
        }
    },

    // تعديل دالة _onSubmit الرئيسية
    async _onSubmit(ev) {
        ev.preventDefault();

        try {
            // التحقق من الحقول المطلوبة أولاً
            if (!this._validateRequiredFields()) {
                this._showMessage('error', 'خطأ', 'يرجى ملء جميع الحقول المطلوبة');
                return;
            }

            // جمع البيانات من الفورم
            const formData = new FormData(this.el);
            const data = {};

            for (let [key, value] of formData.entries()) {
                if (!key.endsWith('_file')) {
                    data[key] = value;
                }
            }

            // === STEP 1: Validation ===
            this._showProgress(30, 'جاري التحقق من البيانات...');

            // معالجة الملفات للvalidation
            const fileFields = ['id_front_file', 'id_back_file', 'esaad_card_file'];
            for (const fieldName of fileFields) {
                const fileInput = document.getElementById(fieldName);
                if (fileInput && fileInput.files[0]) {
                    const file = fileInput.files[0];

                    // التحقق من حجم الملف
                    const maxSize = 5 * 1024 * 1024; // 5MB
                    if (file.size > maxSize) {
                        this._showMessage('error', 'خطأ', `حجم ملف ${this._getFileLabel(fieldName)} يتجاوز 5MB`);
                        return;
                    }

                    try {
                        const base64 = await this._fileToBase64(file);
                        data[fieldName] = base64.split(',')[1];
                        data[fieldName + '_name'] = file.name;
                    } catch (fileError) {
                        console.error('Error processing file:', fileError);
                        this._showMessage('error', 'خطأ', `فشل في معالجة ${this._getFileLabel(fieldName)}`);
                        return;
                    }
                }
            }

            // إرسال للvalidation
            const validationResult = await this._validateRegistrationData(data);

            if (!validationResult.success) {
                this._hideProgress();

                // عرض الأخطاء
                if (validationResult.errors) {
                    this._displayFieldErrors(validationResult.errors);

                    // رسالة عامة للأخطاء
                    const errorCount = Object.keys(validationResult.errors).length;
                    const errorMessage = errorCount > 1 ?
                        `يوجد ${errorCount} أخطاء في البيانات المدخلة` :
                        'يوجد خطأ في البيانات المدخلة';

                    this._showMessage('error', 'خطأ في التحقق', errorMessage);
                }
                return;
            }

            // === STEP 2: Submit with Token ===
            this._showProgress(70, 'جاري حفظ التسجيل...');

            const submitResult = await this._submitWithToken(data, validationResult.token);

            if (!submitResult.success) {
                this._hideProgress();
                this._showMessage('error', 'خطأ', submitResult.error || 'فشل في حفظ التسجيل');
                return;
            }

            // === STEP 3: Handle Response ===
            this._showProgress(100, 'تم التسجيل بنجاح!');

            setTimeout(() => {
                this._hideProgress();
                this._handleRegistrationResponse(submitResult);
            }, 1000);

        } catch (error) {
            console.error('Error in form submission:', error);
            this._hideProgress();
            this._showMessage('error', 'خطأ', error.message || 'حدث خطأ في معالجة البيانات');
        }
    },

    // دالة مساعدة للحصول على اسم الملف بالعربية
    _getFileLabel(fieldName) {
        const labels = {
            'id_front_file': 'الوجه الأول من الهوية',
            'id_back_file': 'الوجه الثاني من الهوية',
            'esaad_card_file': 'بطاقة إسعاد'
        };
        return labels[fieldName] || fieldName;
    },

    // تبقى دالة _handleRegistrationResponse كما هي
    _handleRegistrationResponse(response) {
        this._showLoading(false);
        this._hideProgress();

            if (!response.success) {
        // التحقق من وجود تسجيل مكرر
        if (response.duplicate_found) {
            // عرض رسالة خاصة للتسجيل المكرر
            const duplicateHtml = `
                <div class="duplicate-error-overlay" style="
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0,0,0,0.8);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 10000;">
                    <div class="duplicate-error-content" style="
                        background: white;
                        border-radius: 10px;
                        padding: 30px;
                        max-width: 500px;
                        width: 90%;
                        text-align: center;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <div style="color: #dc3545; font-size: 60px; margin-bottom: 20px;">
                            <i class="fa fa-exclamation-triangle"></i>
                        </div>
                        <h3 style="color: #dc3545; margin-bottom: 20px;">التسجيل مكرر!</h3>
                        <div style="text-align: right; margin-bottom: 20px;">
                            <p><strong>رقم التسجيل السابق:</strong> ${response.existing_registration?.number || ''}</p>
                            <p><strong>اسم الطالب:</strong> ${response.existing_registration?.student_name || ''}</p>
                        </div>
                        <div style="background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 5px; padding: 15px; margin-bottom: 20px;">
                            <p style="margin: 0;">لا يمكن تسجيل نفس الطالب مرتين في نفس الترم</p>
                        </div>
                        <div style="display: flex; gap: 10px; justify-content: center;">
                            <button class="btn btn-secondary" onclick="$(this).closest('.duplicate-error-overlay').remove()">
                                إغلاق
                            </button>
                            <button class="btn btn-primary" onclick="window.location.href='/registration'">
                                العودة للصفحة الرئيسية
                            </button>
                        </div>
                    </div>
                </div>
            `;

            $('body').append(duplicateHtml);
            return;
        }

        // رسالة خطأ عادية
        this._showMessage('error', 'خطأ', response.error || 'حدث خطأ في التسجيل');
        return;
    }

        console.log('Registration response:', response);

        // التحقق من حالة المراجعة (خصم إسعاد)
        if (response.needs_review) {
            if (response.esaad_review) {
                // عرض رسالة نجاح خاصة بإسعاد
                const esaadSuccessHtml = `
                    <div class="esaad-success-overlay" style="
                        position: fixed;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                        background: rgba(0,0,0,0.8);
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        z-index: 10000;">
                        <div class="esaad-success-content" style="
                            background: white;
                            border-radius: 10px;
                            padding: 30px;
                            max-width: 500px;
                            width: 90%;
                            text-align: center;
                            box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                            <div style="color: #17a2b8; font-size: 60px; margin-bottom: 20px;">
                                <i class="fa fa-credit-card"></i>
                            </div>
                            <h3 style="margin-bottom: 20px;">تم استلام طلبك</h3>
                            <div style="background: #d1ecf1; border: 1px solid #bee5eb; border-radius: 5px; padding: 15px; margin-bottom: 20px;">
                                <h5 style="margin-bottom: 15px;">الخطوات التالية:</h5>
                                <ol style="text-align: right; margin-bottom: 0;">
                                    <li>سيتم مراجعة بطاقة إسعاد المرفقة</li>
                                    <li>التحقق من صلاحية البطاقة ومطابقة الاسم</li>
                                    <li>التواصل معك خلال 24-48 ساعة</li>
                                    <li>إرسال رابط الدفع بعد الموافقة</li>
                                </ol>
                            </div>
                            <div style="margin-bottom: 20px;">
                                <p style="margin-bottom: 5px;"><strong>رقم التسجيل:</strong> ${response.registration_number}</p>
                                <p style="color: #6c757d; margin-bottom: 0;">احتفظ بهذا الرقم للمتابعة</p>
                            </div>
                            <button class="btn btn-primary btn-lg" onclick="window.location.href='/registration'">
                                العودة للصفحة الرئيسية
                            </button>
                        </div>
                    </div>
                `;

                $('body').append(esaadSuccessHtml);

                $('.esaad-success-overlay').on('click', function(e) {
                    if (e.target === this) {
                        $(this).fadeOut(300, function() {
                            $(this).remove();
                        });
                    }
                });

            } else {
                // التسجيل يحتاج مراجعة عادية
                this._showMessage('warning', 'يحتاج مراجعة', response.message, 0);

                setTimeout(() => {
                    window.location.href = `/registration/pending/club/${response.registration_id}`;
                }, 3000);
            }
        }
        // التحقق من وجود فاتورة ورابط دفع
        else if (response.payment_url && response.has_invoice) {
            this._showMessage('success', 'تم التسجيل بنجاح', 'سيتم توجيهك لصفحة الدفع...');

            localStorage.setItem('charity_registration_id', response.registration_id);
            if (response.invoice_id) {
                localStorage.setItem('charity_invoice_id', response.invoice_id);
                localStorage.setItem('charity_invoice_name', response.invoice_name);
                localStorage.setItem('charity_amount', response.amount);
            }

            setTimeout(() => {
                console.log('Redirecting to payment:', response.payment_url);
                window.location.href = response.payment_url;
            }, 1500);
        }
        else {
            this._showMessage('success', 'تم التسجيل بنجاح', 'سيتم توجيهك الآن...');
            setTimeout(() => {
                window.location.href = `/registration/success/club/${response.registration_id}`;
            }, 1500);
        }
    }
});

// Widget للحضانة - الجديد
publicWidget.registry.CharityNurseryRegistration = publicWidget.Widget.extend({
    selector: '#nurseryRegistrationForm',
    events: {
        'submit': '_onSubmit',
        'change #has_siblings': '_onSiblingsChange',
        'click .add-sibling': '_onAddSibling',
        'click .remove-sibling': '_onRemoveSibling',
        'click .add-emergency': '_onAddEmergency',
        'click .remove-emergency': '_onRemoveEmergency',
        'change input[name="nursery_plan_id"]': '_onPlanChange',
        'change select[name="attendance_days"]': '_onAttendanceDaysChange',
        'change .nursery-file-input': '_onFileChange',
        'click .remove-file': '_onRemoveFile',
    },

    start() {
        this._super(...arguments);
        console.log('Nursery registration widget initialized');

        // إضافة جهة طوارئ افتراضية
        this._addEmergencyContact();

        // تحديث السعر عند التحميل
        this._updatePrice();

        // تحديث خيارات الأيام عند التحميل إذا كانت هناك خطة محددة
        this._updateAttendanceDaysOptions();
    },

    // إضافة دالة _fileToBase64 المفقودة
    _fileToBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = () => resolve(reader.result);
            reader.onerror = error => reject(error);
        });
    },

    // دالة مساعدة للحصول على اسم الملف بالعربية
    _getFileLabel(fieldName) {
        const labels = {
            'child_id_front': 'الوجه الأمامي لهوية الطفل',
            'child_id_back': 'الوجه الخلفي لهوية الطفل',
            'guardian_id_front': 'الوجه الأمامي لهوية ولي الأمر',
            'guardian_id_back': 'الوجه الخلفي لهوية ولي الأمر'
        };
        return labels[fieldName] || fieldName;
    },

    _onFileChange(ev) {
        const input = ev.currentTarget;
        const fileId = input.id;
        const previewDiv = this.$(`#${fileId}_preview`);

        if (input.files && input.files[0]) {
            const file = input.files[0];
            const fileName = file.name;
            const fileSize = (file.size / 1024 / 1024).toFixed(2);

            if (parseFloat(fileSize) > 5) {
                this._showMessage('error', 'خطأ', 'حجم الملف يجب أن يكون أقل من 5MB');
                input.value = '';
                return;
            }

            // عرض معاينة للصور
            if (file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    previewDiv.find('.preview-img').attr('src', e.target.result).show();
                };
                reader.readAsDataURL(file);
            } else {
                previewDiv.find('.preview-img').hide();
            }

            previewDiv.find('.file-name').text(`${fileName} (${fileSize} MB)`);
            previewDiv.show();
            $(input).parent().find('.file-upload-info').hide();
        }
    },

    _onRemoveFile(ev) {
        const targetId = $(ev.currentTarget).data('target');
        this.$(`#${targetId}`).val('');
        this.$(`#${targetId}_preview`).hide();
        this.$(`#${targetId}`).parent().find('.file-upload-info').show();
    },

    _onSiblingsChange(ev) {
        const checkbox = ev.currentTarget;
        const siblingsSection = this.$('#siblingsSection');

        if (checkbox.checked) {
            siblingsSection.slideDown();
            // إضافة صف أخ/أخت افتراضي إذا لم يكن موجود
            if (this.$('.sibling-row').length === 0) {
                this._addSiblingRow();
            }
        } else {
            siblingsSection.slideUp();
        }
    },

    _onAddSibling(ev) {
        ev.preventDefault();
        this._addSiblingRow();
    },

    _addSiblingRow() {
        const siblingHtml = `
            <div class="sibling-row mb-3">
                <div class="row g-2">
                    <div class="col-md-5">
                        <input type="text" class="form-control" name="sibling_name[]"
                               placeholder="اسم الأخ/الأخت" required>
                    </div>
                    <div class="col-md-3">
                        <input type="number" class="form-control" name="sibling_age[]"
                               placeholder="العمر" min="1" max="99">
                    </div>
                    <div class="col-md-3">
                        <input type="text" class="form-control" name="sibling_class[]"
                               placeholder="الصف">
                    </div>
                    <div class="col-md-1">
                        <button type="button" class="btn btn-danger btn-sm remove-sibling">
                            <i class="fa fa-times"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
        this.$('#siblingsList').append(siblingHtml);
    },

    _onRemoveSibling(ev) {
        ev.preventDefault();
        this.$(ev.currentTarget).closest('.sibling-row').remove();
    },

    _onAddEmergency(ev) {
        ev.preventDefault();
        this._addEmergencyContact();
    },

    _addEmergencyContact() {
        const emergencyHtml = `
            <div class="emergency-row mb-3">
                <div class="row g-2">
                    <div class="col-md-4">
                        <input type="text" class="form-control" name="emergency_name[]"
                               placeholder="اسم الشخص" required>
                    </div>
                    <div class="col-md-4">
                        <input type="tel" class="form-control" name="emergency_mobile[]"
                               placeholder="رقم الهاتف" required>
                    </div>
                    <div class="col-md-3">
                        <input type="text" class="form-control" name="emergency_relationship[]"
                               placeholder="صلة القرابة" required>
                    </div>
                    <div class="col-md-1">
                        <button type="button" class="btn btn-danger btn-sm remove-emergency">
                            <i class="fa fa-times"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
        this.$('#emergencyList').append(emergencyHtml);
    },

    _onRemoveEmergency(ev) {
        ev.preventDefault();
        const row = this.$(ev.currentTarget).closest('.emergency-row');
        // لا نسمح بحذف آخر جهة طوارئ
        if (this.$('.emergency-row').length > 1) {
            row.remove();
        } else {
            this._showMessage('warning', 'تنبيه', 'يجب إضافة جهة طوارئ واحدة على الأقل');
        }
    },

    _onPlanChange(ev) {
        this._updatePrice();
        this._updateAttendanceDaysOptions();
    },

    _onAttendanceDaysChange(ev) {
        this._updatePrice();
    },

    _updateAttendanceDaysOptions() {
        const selectedPlan = this.$('input[name="nursery_plan_id"]:checked');
        const attendanceSelect = this.$('select[name="attendance_days"]');

        if (selectedPlan.length) {
            // تفعيل الحقل
            attendanceSelect.prop('disabled', false);

            // قراءة الخيارات المتاحة من الخطة المختارة
            const show5Days = selectedPlan.data('show-5') === 'true' || selectedPlan.data('show-5') === true;
            const show4Days = selectedPlan.data('show-4') === 'true' || selectedPlan.data('show-4') === true;
            const show3Days = selectedPlan.data('show-3') === 'true' || selectedPlan.data('show-3') === true;
            const price5 = parseFloat(selectedPlan.data('price-5')) || 0;
            const price4 = parseFloat(selectedPlan.data('price-4')) || 0;
            const price3 = parseFloat(selectedPlan.data('price-3')) || 0;

            console.log('Plan options:', {
                show5Days, show4Days, show3Days,
                price5, price4, price3
            });

            // حفظ القيمة الحالية
            const currentValue = attendanceSelect.val();

            // إعادة بناء الخيارات
            attendanceSelect.empty();
            attendanceSelect.append('<option value="">اختر عدد الأيام...</option>');

            // إضافة الخيارات المتاحة فقط - التحقق من show و price معاً
            if (show5Days && price5 > 0) {
                attendanceSelect.append('<option value="5">5 أيام في الأسبوع</option>');
            }
            if (show4Days && price4 > 0) {
                attendanceSelect.append('<option value="4">4 أيام في الأسبوع</option>');
            }
            if (show3Days && price3 > 0) {
                attendanceSelect.append('<option value="3">3 أيام في الأسبوع</option>');
            }

            // إزالة رسالة المساعدة
            attendanceSelect.siblings('small').hide();

            // إعادة تحديد القيمة إذا كانت متاحة
            if (currentValue && attendanceSelect.find(`option[value="${currentValue}"]`).length) {
                attendanceSelect.val(currentValue);
            } else {
                // اختيار أول خيار متاح تلقائياً إذا كان هناك خيار واحد فقط
                const availableOptions = attendanceSelect.find('option:not([value=""])');
                if (availableOptions.length === 1) {
                    attendanceSelect.val(availableOptions.first().val());
                    this._updatePrice();
                }
            }

            // إضافة تأثير بصري للتنبيه
            attendanceSelect.addClass('border-primary');
            setTimeout(() => {
                attendanceSelect.removeClass('border-primary');
            }, 1000);

        } else {
            // تعطيل الحقل إذا لم يتم اختيار خطة
            attendanceSelect.prop('disabled', true);
            attendanceSelect.empty();
            attendanceSelect.append('<option value="">يرجى اختيار نظام الدوام أولاً...</option>');
            attendanceSelect.siblings('small').show();
        }
    },

    _updatePrice() {
        const selectedPlan = this.$('input[name="nursery_plan_id"]:checked');
        const attendanceDays = this.$('select[name="attendance_days"]').val();

        if (selectedPlan.length && attendanceDays) {
            let price = 0;

            if (attendanceDays === '5') {
                price = parseFloat(selectedPlan.data('price-5')) || 0;
            } else if (attendanceDays === '4') {
                price = parseFloat(selectedPlan.data('price-4')) || 0;
            } else if (attendanceDays === '3') {
                price = parseFloat(selectedPlan.data('price-3')) || 0;
            }

            // تحديث عرض السعر
            const priceDisplay = this.$('#priceDisplay');
            if (price > 0) {
                priceDisplay.html(`
                    <div class="alert alert-info">
                        <h4 class="mb-0">
                            <i class="fa fa-tag"></i>
                            الرسوم المستحقة: <span class="text-primary">${price}</span> درهم
                        </h4>
                    </div>
                `);
                priceDisplay.show();
            } else {
                priceDisplay.hide();
            }
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
                        <div>جاري التسجيل...</div>
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

        const alertClass = type === 'error' ? 'alert-danger' :
                          type === 'success' ? 'alert-success' :
                          type === 'warning' ? 'alert-warning' : 'alert-info';

        const alertDiv = $('<div>', {
            class: `alert ${alertClass} alert-dismissible fade show position-fixed`,
            style: 'top: 20px; left: 50%; transform: translateX(-50%); z-index: 9999; min-width: 300px;',
            html: `
                <h5 class="alert-heading">${title}</h5>
                <p>${text}</p>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `
        });

        $('body').append(alertDiv);
        setTimeout(() => alertDiv.remove(), 5000);
    },

    _validateForm() {
        let isValid = true;

        // التحقق من الحقول المطلوبة
        this.$('input[required], select[required], textarea[required]').each(function() {
            const field = $(this);
            if (!field.val() || (field.attr('type') === 'radio' && !$(`input[name="${field.attr('name')}"]:checked`).length)) {
                field.addClass('is-invalid');
                isValid = false;
            } else {
                field.removeClass('is-invalid');
            }
        });

        // التحقق من اختيار الخطة
        if (!this.$('input[name="nursery_plan_id"]:checked').length) {
            this.$('.plan-option').addClass('border-danger');
            isValid = false;
        }

        // التحقق من تأكيد المعلومات
        if (!this.$('#confirm_info').is(':checked')) {
            this.$('#confirm_info').addClass('is-invalid');
            isValid = false;
        }

        return isValid;
    },

    async _onSubmit(ev) {
        ev.preventDefault();

        if (!this._validateForm()) {
            this._showMessage('error', 'خطأ', 'يرجى ملء جميع الحقول المطلوبة');
            return;
        }

        try {
            this._showLoading(true);

            const formData = new FormData(this.el);
            const data = {};

            // جمع البيانات العادية
            for (let [key, value] of formData.entries()) {
                if (!key.includes('[]') && !key.endsWith('_file')) {
                    data[key] = value;
                }
            }

            // معالجة checkbox confirm_info
            data['confirm_info'] = this.$('#confirm_info').is(':checked');

            // معالجة has_siblings
            data['has_siblings'] = this.$('#has_siblings').is(':checked');

            // جمع بيانات الأخوة
            if (data['has_siblings']) {
                const siblingNames = [];
                const siblingAges = [];
                const siblingClasses = [];

                this.$('input[name="sibling_name[]"]').each(function() {
                    siblingNames.push($(this).val());
                });
                this.$('input[name="sibling_age[]"]').each(function() {
                    siblingAges.push($(this).val());
                });
                this.$('input[name="sibling_class[]"]').each(function() {
                    siblingClasses.push($(this).val());
                });

                data['sibling_name[]'] = siblingNames;
                data['sibling_age[]'] = siblingAges;
                data['sibling_class[]'] = siblingClasses;
            }

            // جمع بيانات جهات الطوارئ
            const emergencyNames = [];
            const emergencyMobiles = [];
            const emergencyRelations = [];

            this.$('input[name="emergency_name[]"]').each(function() {
                emergencyNames.push($(this).val());
            });
            this.$('input[name="emergency_mobile[]"]').each(function() {
                emergencyMobiles.push($(this).val());
            });
            this.$('input[name="emergency_relationship[]"]').each(function() {
                emergencyRelations.push($(this).val());
            });

            data['emergency_name[]'] = emergencyNames;
            data['emergency_mobile[]'] = emergencyMobiles;
            data['emergency_relationship[]'] = emergencyRelations;

            // معالجة الملفات المرفوعة
            const fileFields = ['child_id_front', 'child_id_back', 'guardian_id_front', 'guardian_id_back'];

            for (const fieldName of fileFields) {
                const fileInput = document.getElementById(fieldName);
                if (fileInput && fileInput.files && fileInput.files[0]) {
                    const file = fileInput.files[0];

                    // التحقق من حجم الملف
                    const maxSize = 5 * 1024 * 1024; // 5MB
                    if (file.size > maxSize) {
                        this._showMessage('error', 'خطأ', `حجم ملف ${this._getFileLabel(fieldName)} يتجاوز 5MB`);
                        this._showLoading(false);
                        return;
                    }

                    try {
                        const base64 = await this._fileToBase64(file);
                        data[fieldName] = base64.split(',')[1]; // إزالة البادئة data:image/...;base64,
                        data[fieldName + '_name'] = file.name;
                    } catch (fileError) {
                        console.error('Error processing file:', fileError);
                        this._showMessage('error', 'خطأ', `فشل في معالجة ${this._getFileLabel(fieldName)}`);
                        this._showLoading(false);
                        return;
                    }
                }
            }

            console.log('Sending nursery registration data:', data);

            // إعداد البيانات بصيغة JSON-RPC
            const jsonRpcData = {
                jsonrpc: "2.0",
                method: "call",
                params: data,
                id: Math.floor(Math.random() * 1000000000)
            };

            // إرسال البيانات
            $.ajax({
                url: '/registration/submit/nursery',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify(jsonRpcData),
                dataType: 'json',
                success: (response) => {
                    console.log('Response received:', response);

                    if (response.error) {
                        this._showMessage('error', 'خطأ', response.error.message || response.error.data?.message || 'حدث خطأ');
                        return;
                    }

                    const result = response.result;
                    this._handleRegistrationResponse(result);
                },
                error: (xhr, status, error) => {
                    console.error('AJAX Error:', error);
                    this._showMessage('error', 'خطأ', 'حدث خطأ في الاتصال');
                },
                complete: () => {
                    this._showLoading(false);
                }
            });

        } catch (error) {
            console.error('Error:', error);
            this._showMessage('error', 'خطأ', error.message || 'حدث خطأ في المعالجة');
            this._showLoading(false);
        }
    },

    _handleRegistrationResponse(response) {
        this._showLoading(false);

        if (!response.success) {
            this._showMessage('error', 'خطأ', response.error || 'حدث خطأ في التسجيل');
            return;
        }

        console.log('Registration response:', response);

        // لا توجد فاتورة - التوجيه مباشرة لصفحة النجاح
        this._showMessage('success', 'تم التسجيل بنجاح', 'سيتم توجيهك الآن...');
        setTimeout(() => {
            window.location.href = `/registration/success/nursery/${response.registration_id}`;
        }, 1500);
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

        // للحضانة
        const nurseryRegistrationId = localStorage.getItem('nursery_registration_id');
        if (nurseryRegistrationId) {
            localStorage.removeItem('nursery_registration_id');
            localStorage.removeItem('nursery_invoice_id');

            console.log('Payment completed for nursery registration:', nurseryRegistrationId);
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

console.log('Charity registration widgets loaded - including Nursery widget');