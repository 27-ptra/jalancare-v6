import os
from datetime import datetime
from functools import wraps

import cv2
import numpy as np
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from ultralytics import YOLO
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

try:
    from supabase import create_client
except Exception:
    create_client = None

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet


app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY", "jalancare_v5_dev_secret_key")

UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "static/uploads")
RESULT_FOLDER = os.environ.get("RESULT_FOLDER", "static/results")
REPAIR_FOLDER = os.environ.get("REPAIR_FOLDER", "static/repairs")
PDF_FOLDER = os.environ.get("PDF_FOLDER", "static/pdf")
MODEL_PATH = os.environ.get("MODEL_PATH", "best.pt")

USE_SUPABASE_STORAGE = os.environ.get("USE_SUPABASE_STORAGE", "false").lower() == "true"
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_STORAGE_BUCKET = os.environ.get("SUPABASE_STORAGE_BUCKET", "jalancare")

supabase_client = None
if USE_SUPABASE_STORAGE:
    if create_client and SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    else:
        print("PERINGATAN: Supabase Storage aktif, tetapi SUPABASE_URL / SERVICE_ROLE_KEY belum lengkap.")

for folder in [UPLOAD_FOLDER, RESULT_FOLDER, REPAIR_FOLDER, PDF_FOLDER]:
    os.makedirs(folder, exist_ok=True)

database_url = os.environ.get("DATABASE_URL")

if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Supabase pooler/serverless environments benefit from safer connection recycling.
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

db = SQLAlchemy(app)

if os.path.exists(MODEL_PATH):
    model = YOLO(MODEL_PATH)
else:
    model = None
    print("PERINGATAN: best.pt belum ditemukan. Letakkan best.pt sejajar dengan app.py atau set MODEL_PATH.")


class Admin(db.Model):
    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(150))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(80), default="Admin")
    created_at = db.Column(db.String(30))


class Report(db.Model):
    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    ticket_code = db.Column(db.String(80), unique=True)
    reporter_name = db.Column(db.String(150))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(150))
    description = db.Column(db.Text)

    original_image = db.Column(db.String(255))
    result_image = db.Column(db.String(255))
    repair_image = db.Column(db.String(255))

    latitude = db.Column(db.String(50))
    longitude = db.Column(db.String(50))

    pothole_count = db.Column(db.Integer, default=0)
    damage_area = db.Column(db.Integer, default=0)
    damage_percentage = db.Column(db.Float, default=0.0)

    severity = db.Column(db.String(50))
    priority = db.Column(db.String(50))
    recommendation = db.Column(db.Text)

    status = db.Column(db.String(50), default="Menunggu")
    admin_note = db.Column(db.Text)
    completed_at = db.Column(db.String(30))
    created_at = db.Column(db.String(30))


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer)
    ticket_code = db.Column(db.String(80))
    target_type = db.Column(db.String(50))
    target_value = db.Column(db.String(150))
    message = db.Column(db.Text)
    status = db.Column(db.String(80))
    created_at = db.Column(db.String(30))


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("Silakan login sebagai admin terlebih dahulu.")
            return redirect(url_for("admin_login"))
        return func(*args, **kwargs)
    return wrapper


def init_db():
    db.create_all()

    if Admin.query.count() == 0:
        username = os.environ.get("ADMIN_DEFAULT_USERNAME", "admin")
        password = os.environ.get("ADMIN_DEFAULT_PASSWORD", "admin123")
        email = os.environ.get("ADMIN_DEFAULT_EMAIL", "admin@jalancare.local")

        admin = Admin(
            name="Administrator",
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role="Super Admin",
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        db.session.add(admin)
        db.session.commit()


def create_notification(report_id, ticket, target_type, target_value, message):
    item = Notification(
        report_id=report_id,
        ticket_code=ticket,
        target_type=target_type,
        target_value=target_value,
        message=message,
        status="Simulasi terkirim",
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    db.session.add(item)
    db.session.commit()


def is_url(path):
    return isinstance(path, str) and (path.startswith("http://") or path.startswith("https://"))


def media_url(path):
    if not path:
        return ""
    if is_url(path):
        return path
    return "/" + path.replace("\\", "/")


@app.context_processor
def inject_helpers():
    return {"media_url": media_url}


def upload_to_supabase_storage(local_path, storage_folder):
    """
    Upload file lokal ke Supabase Storage jika fitur storage aktif.
    Return:
    - public URL jika upload berhasil dan storage aktif
    - local_path jika storage tidak aktif atau upload gagal
    """
    if not USE_SUPABASE_STORAGE or not supabase_client:
        return local_path

    try:
        filename = os.path.basename(local_path)
        storage_path = f"{storage_folder}/{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"

        with open(local_path, "rb") as file:
            supabase_client.storage.from_(SUPABASE_STORAGE_BUCKET).upload(
                path=storage_path,
                file=file,
                file_options={"upsert": "true"}
            )

        public_url = supabase_client.storage.from_(SUPABASE_STORAGE_BUCKET).get_public_url(storage_path)
        return public_url

    except Exception as error:
        print(f"PERINGATAN: Upload Supabase Storage gagal: {error}")
        return local_path


def ticket_code(report_id):
    return f"JLC-{datetime.now().strftime('%Y%m%d')}-{report_id:04d}"


def severity_from_percentage(percent):
    if percent < 5:
        return "Ringan"
    if percent < 15:
        return "Sedang"
    return "Parah"


def priority_from_result(severity, count):
    if severity == "Parah" or count >= 3:
        return "Tinggi"
    if severity == "Sedang":
        return "Normal"
    return "Rendah"


def recommendation_from_severity(severity):
    if severity == "Ringan":
        return "Kerusakan masih kecil. Disarankan pemantauan rutin dan penambalan ringan bila diperlukan."
    if severity == "Sedang":
        return "Kerusakan cukup terlihat. Disarankan masuk daftar perbaikan dan penambalan lokal."
    return "Kerusakan parah. Disarankan segera diprioritaskan untuk penanganan lapangan."


def process_image(image_path, result_path):
    if model is None:
        raise FileNotFoundError("Model best.pt belum ditemukan. Letakkan best.pt di folder utama project atau set MODEL_PATH.")

    image = cv2.imread(image_path)
    if image is None:
        raise ValueError("File gambar tidak dapat dibaca.")

    height, width = image.shape[:2]
    total_pixels = height * width
    total_damage = 0
    pothole_count = 0

    results = model.predict(source=image_path, conf=0.25, save=False)

    for result in results:
        if result.masks is None:
            continue

        for mask in result.masks.data:
            mask_np = mask.cpu().numpy()
            mask_resize = cv2.resize(mask_np, (width, height))
            binary = mask_resize > 0.5

            area = int(np.sum(binary))
            total_damage += area
            pothole_count += 1

            overlay = image.copy()
            overlay[binary] = (20, 20, 235)
            image = cv2.addWeighted(overlay, 0.45, image, 0.55, 0)

    percentage = (total_damage / total_pixels) * 100 if total_pixels else 0
    severity = severity_from_percentage(percentage)

    label = f"Lubang: {pothole_count} | Kerusakan: {percentage:.2f}% | {severity}"
    cv2.rectangle(image, (18, 18), (min(width - 18, 860), 72), (10, 20, 35), -1)
    cv2.putText(image, label, (30, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.82, (255, 255, 255), 2)
    cv2.imwrite(result_path, image)

    return pothole_count, total_damage, percentage, severity


def make_pdf(report):
    filename = f"laporan_{report.ticket_code}.pdf"
    pdf_path = os.path.join(PDF_FOLDER, filename)

    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Laporan Kerusakan Jalan - JalanCare", styles["Title"]))
    story.append(Spacer(1, 0.35 * cm))
    story.append(Paragraph(f"Nomor Tiket: {report.ticket_code}", styles["Heading2"]))
    story.append(Spacer(1, 0.35 * cm))

    rows = [
        ["Nama Pelapor", report.reporter_name or "-"],
        ["No. HP", report.phone or "-"],
        ["Email", report.email or "-"],
        ["Tanggal", report.created_at or "-"],
        ["Status", report.status or "-"],
        ["Jumlah Lubang", str(report.pothole_count)],
        ["Luas Kerusakan", f"{report.damage_area} pixel"],
        ["Persentase Kerusakan", f"{report.damage_percentage:.2f}%"],
        ["Tingkat Kerusakan", report.severity or "-"],
        ["Prioritas", report.priority or "-"],
        ["Latitude", report.latitude or "-"],
        ["Longitude", report.longitude or "-"],
        ["Tanggal Selesai", report.completed_at or "-"],
    ]

    table = Table(rows, colWidths=[5 * cm, 10 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e5e7eb")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9ca3af")),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.45 * cm))

    story.append(Paragraph("Deskripsi Pelapor", styles["Heading3"]))
    story.append(Paragraph(report.description or "-", styles["BodyText"]))
    story.append(Spacer(1, 0.25 * cm))

    story.append(Paragraph("Rekomendasi Sistem", styles["Heading3"]))
    story.append(Paragraph(report.recommendation or "-", styles["BodyText"]))
    story.append(Spacer(1, 0.25 * cm))

    story.append(Paragraph("Catatan Admin", styles["Heading3"]))
    story.append(Paragraph(report.admin_note or "-", styles["BodyText"]))
    story.append(Spacer(1, 0.4 * cm))

    if report.result_image and not is_url(report.result_image) and os.path.exists(report.result_image):
        story.append(Paragraph("Foto Hasil Deteksi AI", styles["Heading3"]))
        story.append(Image(report.result_image, width=14 * cm, height=9 * cm))
        story.append(Spacer(1, 0.4 * cm))

    if report.repair_image and not is_url(report.repair_image) and os.path.exists(report.repair_image):
        story.append(Paragraph("Foto Bukti Setelah Perbaikan", styles["Heading3"]))
        story.append(Image(report.repair_image, width=14 * cm, height=9 * cm))

    doc.build(story)
    return pdf_path


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/lapor")
def public_form():
    return render_template("public_form.html")


@app.route("/lapor", methods=["POST"])
def submit_report():
    photo = request.files.get("photo")
    if not photo or photo.filename == "":
        flash("Foto belum dipilih.")
        return redirect(url_for("public_form"))

    reporter_name = request.form.get("reporter_name", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()
    description = request.form.get("description", "").strip()
    latitude = request.form.get("latitude", "").strip()
    longitude = request.form.get("longitude", "").strip()

    safe_name = secure_filename(photo.filename)
    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{safe_name}"

    original_path = os.path.join(UPLOAD_FOLDER, filename)
    result_path = os.path.join(RESULT_FOLDER, filename)
    photo.save(original_path)

    try:
        count, area, percentage, severity = process_image(original_path, result_path)
    except Exception as err:
        flash(f"Gagal memproses gambar: {err}")
        return redirect(url_for("public_form"))

    original_store_path = upload_to_supabase_storage(original_path, "uploads")
    result_store_path = upload_to_supabase_storage(result_path, "results")

    report = Report(
        ticket_code="",
        reporter_name=reporter_name,
        phone=phone,
        email=email,
        description=description,
        original_image=original_store_path,
        result_image=result_store_path,
        repair_image="",
        latitude=latitude,
        longitude=longitude,
        pothole_count=count,
        damage_area=area,
        damage_percentage=percentage,
        severity=severity,
        priority=priority_from_result(severity, count),
        recommendation=recommendation_from_severity(severity),
        status="Menunggu",
        admin_note="",
        completed_at="",
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    db.session.add(report)
    db.session.commit()

    report.ticket_code = ticket_code(report.id)
    db.session.commit()

    if phone:
        create_notification(
            report.id,
            report.ticket_code,
            "WhatsApp",
            phone,
            f"Laporan JalanCare berhasil dibuat. Nomor tiket Anda: {report.ticket_code}. Status awal: Menunggu."
        )

    if email:
        create_notification(
            report.id,
            report.ticket_code,
            "Email",
            email,
            f"Laporan JalanCare berhasil dibuat. Nomor tiket Anda: {report.ticket_code}."
        )

    return redirect(url_for("public_result", report_id=report.id))


@app.route("/laporan/<int:report_id>")
def public_result(report_id):
    report = Report.query.get(report_id)
    if not report:
        flash("Laporan tidak ditemukan.")
        return redirect(url_for("public_form"))

    return render_template("public_result.html", report=report)


@app.route("/cek-status", methods=["GET", "POST"])
def check_status():
    report = None
    if request.method == "POST":
        code = request.form.get("ticket_code", "").strip()
        report = Report.query.filter_by(ticket_code=code).first()
        if not report:
            flash("Nomor tiket tidak ditemukan.")

    return render_template("check_status.html", report=report)


@app.route("/admin/register", methods=["GET", "POST"])
def admin_register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if password != confirm:
            flash("Konfirmasi password tidak sama.")
            return redirect(url_for("admin_register"))

        if len(password) < 6:
            flash("Password minimal 6 karakter.")
            return redirect(url_for("admin_register"))

        existing = Admin.query.filter_by(username=username).first()
        if existing:
            flash("Username sudah digunakan.")
            return redirect(url_for("admin_register"))

        admin = Admin(
            name=name,
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role="Admin",
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        db.session.add(admin)
        db.session.commit()

        flash("Akun admin berhasil dibuat. Silakan login.")
        return redirect(url_for("admin_login"))

    return render_template("admin_register.html")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        admin = Admin.query.filter_by(username=username).first()

        if admin and check_password_hash(admin.password_hash, password):
            session["admin_logged_in"] = True
            session["admin_id"] = admin.id
            session["admin_name"] = admin.name
            session["admin_role"] = admin.role
            return redirect(url_for("admin_dashboard"))

        flash("Username atau password salah.")

    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/admin")
@login_required
def admin_dashboard():
    status_filter = request.args.get("status", "")
    severity_filter = request.args.get("severity", "")

    query = Report.query

    if status_filter:
        query = query.filter_by(status=status_filter)

    if severity_filter:
        query = query.filter_by(severity=severity_filter)

    reports = query.order_by(Report.id.desc()).all()

    stats = {
        "total": Report.query.count(),
        "menunggu": Report.query.filter_by(status="Menunggu").count(),
        "diproses": Report.query.filter_by(status="Diproses").count(),
        "selesai": Report.query.filter_by(status="Selesai").count(),
        "parah": Report.query.filter_by(severity="Parah").count(),
    }

    status_stats = db.session.query(Report.status, db.func.count(Report.id).label("total")).group_by(Report.status).all()
    severity_stats = db.session.query(Report.severity, db.func.count(Report.id).label("total")).group_by(Report.severity).all()

    return render_template(
        "admin_dashboard.html",
        reports=reports,
        stats=stats,
        status_stats=status_stats,
        severity_stats=severity_stats,
        status_filter=status_filter,
        severity_filter=severity_filter
    )


@app.route("/admin/laporan/<int:report_id>")
@login_required
def admin_detail(report_id):
    report = Report.query.get(report_id)

    if not report:
        flash("Laporan tidak ditemukan.")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin_detail.html", report=report)


@app.route("/admin/update/<int:report_id>", methods=["POST"])
@login_required
def admin_update(report_id):
    report = Report.query.get(report_id)

    if not report:
        flash("Laporan tidak ditemukan.")
        return redirect(url_for("admin_dashboard"))

    status = request.form.get("status", "Menunggu")
    note = request.form.get("admin_note", "").strip()
    repair_photo = request.files.get("repair_image")

    if repair_photo and repair_photo.filename:
        safe_name = secure_filename(repair_photo.filename)
        filename = f"repair_{datetime.now().strftime('%Y%m%d%H%M%S')}_{safe_name}"
        repair_path = os.path.join(REPAIR_FOLDER, filename)
        repair_photo.save(repair_path)
        report.repair_image = upload_to_supabase_storage(repair_path, "repairs")

    if status == "Selesai" and not report.completed_at:
        report.completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report.status = status
    report.admin_note = note
    db.session.commit()

    message = f"Status laporan {report.ticket_code} diperbarui menjadi {status}."
    if report.phone:
        create_notification(report.id, report.ticket_code, "WhatsApp", report.phone, message)
    if report.email:
        create_notification(report.id, report.ticket_code, "Email", report.email, message)

    flash("Laporan berhasil diperbarui dan notifikasi simulasi dibuat.")
    return redirect(url_for("admin_detail", report_id=report_id))


@app.route("/admin/map")
@login_required
def admin_map():
    reports = Report.query.filter(
        Report.latitude.isnot(None),
        Report.longitude.isnot(None),
        Report.latitude != "",
        Report.longitude != ""
    ).order_by(Report.id.desc()).all()

    return render_template("admin_map.html", reports=reports)


@app.route("/admin/pdf/<int:report_id>")
@login_required
def admin_pdf(report_id):
    report = Report.query.get(report_id)

    if not report:
        flash("Laporan tidak ditemukan.")
        return redirect(url_for("admin_dashboard"))

    pdf_path = make_pdf(report)
    return send_file(pdf_path, as_attachment=True)


@app.route("/admin/notifications")
@login_required
def admin_notifications():
    notifications = Notification.query.order_by(Notification.id.desc()).all()
    return render_template("admin_notifications.html", notifications=notifications)


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(debug=True)
