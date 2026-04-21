
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from flask import Flask, jsonify, render_template, request

BASE_DIR = Path(__file__).resolve().parent
SCRIPT_WEBAPP_URL = os.environ.get(
    "GOOGLE_APPS_SCRIPT_URL",
    "https://script.google.com/macros/s/AKfycbxDSda53Wr_VMlvuBLMkVBcybLOsGthTHhJq8bZ9Ay6sDweJ-LsEpOzKywjbnAkVuI/exec",
)
SPREADSHEET_URL = os.environ.get(
    "GOOGLE_SHEET_URL",
    "https://docs.google.com/spreadsheets/d/1dSsj9rXwaQGaZ1MSogZnTYAsFyIasGQQ-u3RGXTQC0w/edit?usp=sharing",
)
TIMEZONE_LABEL = os.environ.get("ATTENDANCE_TIMEZONE_LABEL", "توقيت جهازك المحلي")

EMPLOYEES: List[Dict[str, str]] = [
    {"id": f"EMP-{i:03}", "name": name}
    for i, name in enumerate(
        [
            "احمد صلاح بيومي",
            "حميده محمد هنداوي",
            "يوسف مهدي",
            "فؤاد سيد",
            "مارتينا عماد",
        ],
        start=1,
    )
]
EMPLOYEE_MAP = {emp["id"]: emp["name"] for emp in EMPLOYEES}


def today_sheet_name() -> str:
    now = datetime.now()
    return f"{now.day}-{now.month}-{now.year}"


def default_summary() -> Dict[str, int]:
    return {
        "total_employees": len(EMPLOYEES),
        "check_ins": 0,
        "check_outs": 0,
        "tasks": 0,
        "completed": 0,
    }


def post_to_apps_script(payload: Dict[str, str]) -> Dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        SCRIPT_WEBAPP_URL,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            body = response.read().decode("utf-8")
            return json.loads(body or "{}")
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8")
            parsed = json.loads(body or "{}")
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
        raise RuntimeError(f"فشل الاتصال بـ Apps Script. رمز الحالة: {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("تعذر الوصول إلى رابط Apps Script. تأكد من أن النشر مضبوط على Anyone.") from exc


def test_connection() -> Tuple[str, str]:
    req = urllib.request.Request(SCRIPT_WEBAPP_URL, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            body = response.read().decode("utf-8")
            data = json.loads(body or "{}")
            if data.get("ok"):
                return "connected", "تم ربط الموقع مع Google Apps Script بنجاح."
            return "error", "الرابط متاح لكن الاستجابة غير متوقعة."
    except Exception as exc:
        return "error", f"تعذر اختبار الربط الآن: {exc}"


def app_factory() -> Flask:
    app = Flask(__name__)

    @app.route("/")
    def index():
        connection_status, connection_message = test_connection()
        return render_template(
            "index.html",
            employees=EMPLOYEES,
            today_sheet=today_sheet_name(),
            summary=default_summary(),
            timezone_label=TIMEZONE_LABEL,
            spreadsheet_url=SPREADSHEET_URL,
            script_url=SCRIPT_WEBAPP_URL,
            connection_status=connection_status,
            connection_message=connection_message,
        )

    @app.get("/api/state")
    def state():
        status, message = test_connection()
        return jsonify(
            {
                "ok": status == "connected",
                "sheet_name": today_sheet_name(),
                "summary": default_summary(),
                "employees": EMPLOYEES,
                "spreadsheet_url": SPREADSHEET_URL,
                "connection_message": message,
            }
        )

    @app.post("/api/check-in")
    def check_in():
        payload = request.get_json(force=True, silent=True) or {}
        employee_id = (payload.get("employee_id") or "").strip()
        body, status = write_event(employee_id, "attendance", None)
        return jsonify(body), status

    @app.post("/api/check-out")
    def check_out():
        payload = request.get_json(force=True, silent=True) or {}
        employee_id = (payload.get("employee_id") or "").strip()
        body, status = write_event(employee_id, "checkout", None)
        return jsonify(body), status

    @app.post("/api/task")
    def save_task():
        payload = request.get_json(force=True, silent=True) or {}
        employee_id = (payload.get("employee_id") or "").strip()
        task_text = (payload.get("task") or "").strip()
        body, status = write_event(employee_id, "task", task_text)
        return jsonify(body), status

    return app


def write_event(employee_id: str, action: str, task_text: str | None):
    if employee_id not in EMPLOYEE_MAP:
        return {"ok": False, "message": "الموظف غير موجود."}, 400
    if action == "task" and not task_text:
        return {"ok": False, "message": "اكتب المهمة اليومية أولاً."}, 400

    payload = {
        "employee": EMPLOYEE_MAP[employee_id],
        "action": action,
        "task": task_text or "",
    }

    try:
        result = post_to_apps_script(payload)
    except Exception as exc:
        return {"ok": False, "message": str(exc)}, 500

    if not isinstance(result, dict):
        return {"ok": False, "message": "وصل رد غير متوقع من Apps Script."}, 502

    if not result.get("ok"):
        return {
            "ok": False,
            "message": result.get("message", "فشل حفظ العملية داخل Google Sheet."),
        }, 409

    action_map = {
        "attendance": "الحضور",
        "checkout": "الانصراف",
        "task": "المهمة اليومية",
    }

    return {
        "ok": True,
        "message": result.get("message") or f"تم حفظ {action_map.get(action, action)} بنجاح.",
        "sheet_name": result.get("sheet") or today_sheet_name(),
        "spreadsheet_url": SPREADSHEET_URL,
        "action": action,
        "employee_id": employee_id,
    }, 200


app = app_factory()

if __name__ == "__main__":
    app.run(debug=True)
