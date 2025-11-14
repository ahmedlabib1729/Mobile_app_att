# Custom Invoice Report - Odoo 18
## فاتورة مخصصة بدون Header و Footer

### الوصف
موديول فاتورة مخصصة بتصميم Dot Matrix بدون header أو footer في الطباعة، مع:
- تصميم يشبه طابعات Dot Matrix
- جدول تفصيلي للمنتجات مع VAT
- جدول ملخص الضرائب
- المبلغ بالكلمات (بالإنجليزية)
- قسم التوقيعات (Prepared By, Verified By, Authorised Signatory)
- إعلان قانوني

### التثبيت

#### 1. نسخ الموديول
```bash
cp -r custom_invoice_report /path/to/odoo/addons/
```

#### 2. تثبيت المكتبات المطلوبة
```bash
pip3 install num2words
```

#### 3. تفعيل الموديول
1. قم بتحديث قائمة الموديولات في Odoo
2. ابحث عن "Custom Invoice Report - Dot Matrix Style"
3. قم بتثبيت الموديول

### الاستخدام

#### طباعة الفاتورة
1. افتح أي فاتورة (Customer Invoice)
2. اضغط على زر "Print" أو "طباعة"
3. اختر "Tax Invoice (Custom)"
4. سيتم تحميل الـ PDF بدون header أو footer

### الميزات

#### 1. معلومات الفاتورة
- رقم الفاتورة (Invoice No.)
- رقم المرجع (Ref No.)
- التاريخ (Date)
- رقم السجل التجاري (CR.NO)

#### 2. معلومات العميل
- اسم العميل
- العنوان
- الدولة
- الرقم الضريبي

#### 3. جدول المنتجات
- الرقم التسلسلي
- الوصف
- الكمية
- السعر
- الخصم
- المبلغ بدون VAT
- نسبة VAT
- مبلغ VAT
- الإجمالي شامل VAT

#### 4. ملخص VAT
- جدول منفصل يوضح:
  - نسبة VAT
  - القيمة الخاضعة للضريبة
  - مبلغ الضريبة

#### 5. المبلغ بالكلمات
- المبلغ الإجمالي بالكلمات بالإنجليزية
- مبلغ VAT بالكلمات بالإنجليزية
- يدعم الدينار البحريني (BHD) مع الفلوس

#### 6. قسم التوقيعات
- Prepared By
- Verified By
- Authorised Signatory

### التخصيص

#### تغيير العملة
الموديول يدعم حالياً الدينار البحريني (BHD). لإضافة عملات أخرى، قم بتعديل function `_get_amount_in_words` في ملف `models/account_move.py`.

#### تعديل التصميم
لتعديل التصميم، قم بتعديل ملف `views/report_invoice_custom.xml`:
- CSS في قسم `<style>`
- HTML في قسم template

#### إضافة حقول جديدة
لإضافة حقول جديدة:
1. أضف الحقل في `models/account_move.py`
2. أضف الحقل في template في `views/report_invoice_custom.xml`

### ملاحظات مهمة

1. **إزالة Header و Footer**: تم إزالتهم تماماً من خلال:
   ```xml
   @page {
       margin: 0mm;
   }
   ```

2. **الخطوط**: يستخدم Courier New لمحاكاة طابعات Dot Matrix

3. **حجم الورق**: A4 (210mm × 297mm)

4. **الهوامش**: 
   - الهوامش الجانبية: 10mm
   - الهوامش العلوية والسفلية: 15mm

### الدعم الفني

في حالة وجود أي مشاكل:
1. تأكد من تثبيت مكتبة `num2words`
2. تأكد من إعادة تشغيل Odoo بعد التثبيت
3. تأكد من update الموديول بعد أي تعديلات

### الإصدار
- Version: 18.0.1.0.0
- Odoo Version: 18.0
- License: LGPL-3

### المطور
Your Company - https://www.yourcompany.com
