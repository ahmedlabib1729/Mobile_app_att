# POS Receipt Custom - Professional Design

**تخصيص احترافي لإيصال POS في Odoo 18**

## التنصيب | Installation

```bash
# 1. انسخ المديول لمجلد addons
cp -r pos_receipt_custom /path/to/odoo/addons/

# 2. أعد تشغيل Odoo
sudo systemctl restart odoo

# 3. حدّث قائمة التطبيقات
Settings → Apps → Update Apps List

# 4. نصّب المديول
ابحث عن "POS Receipt Custom" واضغط Install
```

## الإعدادات | Configuration

### 1. معلومات الشركة | Company Info
```
Settings → Companies → [Your Company]
```
املأ:
- Company Name
- Address (Street, City)
- Phone
- Email
- Tax Number (VAT)
- Logo (PNG/JPG)

### 2. إعدادات POS | POS Settings
```
Point of Sale → Configuration → Point of Sale → [Your POS]
→ Custom Receipt Settings
```

الحقول المتاحة:
- **Receipt Footer**: نص مخصص في التذييل
- **Show Line Numbers**: عرض أرقام الأسطر
- **Show Receipt Barcode**: عرض الباركود

## المميزات | Features

✅ عرض لوجو الشركة  
✅ معلومات الشركة الكاملة  
✅ ترقيم المنتجات  
✅ عرض الخصومات  
✅ تفصيل الضرائب  
✅ باركود تلقائي  
✅ نص تذييل مخصص  
✅ دعم العربية والإنجليزية  

## حل المشاكل | Troubleshooting

### الإيصال لا يطبع بالشكل الجديد

1. امسح الـ cache:
```
Ctrl + Shift + R
```

2. أعد فتح POS session جديد

3. تأكد من upgrade المديول:
```bash
./odoo-bin -u pos_receipt_custom -d your_database
```

### اللوجو لا يظهر

1. تأكد من رفع اللوجو في Company settings
2. استخدم صورة PNG بحجم مناسب (<200px)
3. امسح browser cache

## الدعم | Support

📧 Email: support@yourcompany.com  
💬 Website: www.yourcompany.com  

## الترخيص | License

LGPL-3

---

**Developed with ❤️ by Ahmed - ERP Accounting & Auditing L.L.C.**

Version: 18.0.1.0.0  
Compatible with: Odoo 18.0
