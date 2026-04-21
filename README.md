# Attendance System - Google Apps Script Edition

## النسخة الحالية
هذه النسخة مربوطة مباشرة برابط Google Apps Script Web App الذي نشرته أنت.

## التشغيل
```bash
pip install -r requirements.txt
python app.py
```

ثم افتح:
```bash
http://127.0.0.1:5000
```

## ملاحظات مهمة
- لا تحتاج الآن إلى Google Cloud أو Service Account JSON.
- رابط Web App مضبوط داخل `app.py` على الرابط الذي أرسلته.
- عند تسجيل الحضور أو الانصراف أو المهمة، يرسل الموقع الطلب إلى Apps Script ثم تُحفظ البيانات داخل Google Sheet.
- إنشاء الشيت اليومي ومنع التعديل يتمان داخل كود Apps Script الذي نشرته في Google Sheets.
- العدادات الظاهرة في أعلى الصفحة يتم تحديثها أثناء الجلسة الحالية داخل الموقع، أما المرجع الأساسي فهو Google Sheet نفسه.
