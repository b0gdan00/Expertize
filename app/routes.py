from pathlib import Path
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, session, url_for, current_app, send_file

from . import db
from .services import find_placeholders, render_docx_with_values

bp = Blueprint("main", __name__)


@bp.context_processor
def inject_globals():
    return {
        "current_expert": session.get("expert_name"),
        "expert_details": db.get_expert_details(),
        "stored_variables": db.list_variables(),
    }


@bp.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        name = request.form.get("expert_name", "").strip()
        if not name:
            flash("Введіть ім'я експерта", "danger")
            return redirect(url_for("main.home"))

        session["expert_name"] = name
        if not db.get_expert_details():
            db.save_expert_details(name)
        flash(f"Ласкаво просимо, {name}!", "success")
        return redirect(url_for("main.new_expertise"))

    return render_template("index.html", title="Авторизація експерта")


@bp.route("/expertise/new", methods=["GET", "POST"])
def new_expertise():
    if "expert_name" not in session:
        flash("Авторизуйтеся, щоб продовжити", "warning")
        return redirect(url_for("main.home"))

    variables = db.list_variables()
    if request.method == "POST":
        action = request.form.get("action", "save")
        payload = {}
        for var in variables:
            form_key = f"var_{var.doc_id}"
            value = request.form.get(form_key, "").strip()
            payload[var["key"]] = value

        if action == "render":
            template_meta = db.get_template_metadata()
            filename = template_meta.get("filename")
            if not filename:
                flash("Немає завантаженого шаблону для підстановки.", "danger")
                return redirect(url_for("main.new_expertise"))

            template_path = Path(current_app.config["UPLOAD_FOLDER"]) / filename
            if not template_path.exists():
                flash("Файл шаблону не знайдено. Завантажте знову.", "danger")
                return redirect(url_for("main.new_expertise"))

            output = render_docx_with_values(template_path, payload)
            stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            download_name = f"expertise_{stamp}.docx"
            return send_file(
                output,
                as_attachment=True,
                download_name=download_name,
                mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

        db.save_expertise(session.get("expert_name", ""), payload)
        flash("Чернетку експертизи збережено.", "success")
        return redirect(url_for("main.new_expertise"))

    template_meta = db.get_template_metadata()
    return render_template(
        "expertise_new.html",
        title="Нова експертиза",
        variables=variables,
        template_meta=template_meta,
    )


@bp.route("/settings/expert", methods=["GET", "POST"])
def expert_settings():
    current_details = db.get_expert_details()
    if request.method == "POST":
        details = request.form.get("expert_details", "").strip()
        db.save_expert_details(details)
        if details:
            session["expert_name"] = details
        flash("Дані експерта оновлено", "success")
        return redirect(url_for("main.expert_settings"))

    return render_template(
        "settings_expert.html",
        title="Налаштування експерта",
        expert_details=current_details,
    )


@bp.route("/settings/variables", methods=["GET", "POST"])
def variables_settings():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            key = request.form.get("key", "").strip()
            description = request.form.get("description", "").strip()
            if not key:
                flash("Вкажіть ключ змінної", "danger")
            else:
                db.upsert_variable(key=key, description=description, auto_created=False)
                flash(f"Змінну {{{key}}} збережено", "success")
        elif action == "delete":
            doc_id_raw = request.form.get("doc_id")
            if doc_id_raw:
                db.delete_variable(int(doc_id_raw))
                flash("Змінну видалено", "info")
        return redirect(url_for("main.variables_settings"))

    variables = db.list_variables()
    return render_template("settings_variables.html", title="Змінні шаблону", variables=variables)


@bp.route("/template/upload", methods=["GET", "POST"])
def upload_template():
    template_meta = db.get_template_metadata()

    if request.method == "POST":
        file = request.files.get("template_file")
        if not file or file.filename == "":
            flash("Оберіть файл шаблону .docx", "danger")
            return redirect(url_for("main.upload_template"))

        filename = "template.docx"
        target_path = Path(current_app.config["UPLOAD_FOLDER"]) / filename
        file.save(target_path)

        placeholders = find_placeholders(target_path)
        db.add_placeholders(placeholders)
        db.save_template_metadata(filename=filename)

        flash(
            f"Шаблон завантажено. Знайдено {len(placeholders)} змінних: "
            + ", ".join(sorted(placeholders)) if placeholders else "Шаблон завантажено, змінних не знайдено.",
            "success",
        )
        return redirect(url_for("main.upload_template"))

    return render_template("template_upload.html", title="Шаблон експертизи", template_meta=template_meta)


@bp.route("/logout")
def logout():
    session.clear()
    flash("Сесію завершено", "info")
    return redirect(url_for("main.home"))
