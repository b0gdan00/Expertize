from pathlib import Path
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, session, url_for, current_app, send_file

from . import db
from .services import find_placeholders, render_docx_with_values

bp = Blueprint("main", __name__)


@bp.context_processor
def inject_globals():
    expert_id = session.get("expert_id")
    expert = db.get_expert(expert_id) if expert_id else None
    current_expert = expert.get("name") if expert else None
    return {
        "current_expert": current_expert,
        "expert_details": db.get_expert_details(expert_id),
        "stored_variables": db.list_variables(expert_id),
    }


@bp.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        name = request.form.get("expert_name", "").strip()
        if not name:
            flash("Вкажіть ім'я експерта", "danger")
            return redirect(url_for("main.home"))

        expert = db.get_or_create_expert(name)
        session["expert_id"] = expert.doc_id
        session["expert_name"] = expert["name"]
        flash(f"Ласкаво просимо, {name}!", "success")
        return redirect(url_for("main.new_expertise"))

    return render_template("index.html", title="Експертний помічник")


@bp.route("/expertise/new", methods=["GET", "POST"])
def new_expertise():
    expert_id = session.get("expert_id")
    expert = db.get_expert(expert_id) if expert_id else None
    if not expert:
        flash("Ви не авторизовані!", "warning")
        return redirect(url_for("main.home"))

    variables = db.list_variables(expert_id)
    if request.method == "POST":
        payload = {}
        for var in variables:
            form_key = f"var_{var.doc_id}"
            value = request.form.get(form_key, "").strip()
            payload[var["key"]] = value

        template_meta = db.get_template_metadata()
        filename = template_meta.get("filename")
        if not filename:
            flash("Немає завантаженого шаблону для заповнення.", "danger")
            return redirect(url_for("main.new_expertise"))

        template_path = Path(current_app.config["UPLOAD_FOLDER"]) / filename
        if not template_path.exists():
            flash("Файл шаблону не знайдено. Завантажте його знову.", "danger")
            return redirect(url_for("main.new_expertise"))

        db.save_expertise(expert_id=expert.doc_id, expert_name=expert["name"], variables_payload=payload)
        output = render_docx_with_values(template_path, payload)
        stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        download_name = f"expertise_{stamp}.docx"
        return send_file(
            output,
            as_attachment=True,
            download_name=download_name,
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    template_meta = db.get_template_metadata()
    return render_template(
        "expertise_new.html",
        title="Нова експертиза",
        variables=variables,
        template_meta=template_meta,
    )


@bp.route("/settings/expert", methods=["GET", "POST"])
def expert_settings():
    expert_id = session.get("expert_id")
    expert = db.get_expert(expert_id) if expert_id else None
    if not expert:
        flash("Ви не авторизовані!", "warning")
        return redirect(url_for("main.home"))

    current_details = db.get_expert_details(expert_id)
    if request.method == "POST":
        details = request.form.get("expert_details", "").strip()
        db.save_expert_details(expert_id=expert_id, details=details)
        flash("Дані експерта збережено", "success")
        return redirect(url_for("main.expert_settings"))

    return render_template(
        "settings_expert.html",
        title="Налаштування експерта",
        expert_details=current_details,
    )


@bp.route("/settings/variables", methods=["GET", "POST"])
def variables_settings():
    expert_id = session.get("expert_id")
    if not expert_id:
        flash("Ви не авторизовані!", "warning")
        return redirect(url_for("main.home"))

    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            key = request.form.get("key", "").strip()
            description = request.form.get("description", "").strip()
            if not key:
                flash("Вкажіть назву змінної", "danger")
            else:
                db.upsert_variable(expert_id=expert_id, key=key, description=description, auto_created=False)
                flash(f"Змінна {{{key}}} збережена", "success")
        elif action == "delete":
            doc_id_raw = request.form.get("doc_id")
            if doc_id_raw:
                db.delete_variable(expert_id=expert_id, doc_id=int(doc_id_raw))
                flash("Змінну видалено", "info")
        return redirect(url_for("main.variables_settings"))

    variables = db.list_variables(expert_id)
    return render_template("settings_variables.html", title="Ваші змінні", variables=variables)


@bp.route("/template/upload", methods=["GET", "POST"])
def upload_template():
    expert_id = session.get("expert_id")
    if not expert_id:
        flash("Ви не авторизовані!", "warning")
        return redirect(url_for("main.home"))

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
        db.add_placeholders(expert_id=expert_id, placeholders=placeholders)
        db.save_template_metadata(filename=filename)

        flash(
            f"Шаблон завантажено. Знайдено {len(placeholders)} змінних: "
            + ", ".join(sorted(placeholders)) if placeholders else "Шаблон завантажено, змін не знайдено.",
            "success",
        )
        return redirect(url_for("main.upload_template"))

    return render_template("template_upload.html", title="Завантаження шаблону", template_meta=template_meta)


@bp.route("/logout")
def logout():
    session.clear()
    flash("Сесію завершено", "info")
    return redirect(url_for("main.home"))
