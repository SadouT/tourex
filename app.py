"""TourEx Flutter App Builder - Flask backend."""

import json
import os
import io
import zipfile
from pathlib import Path

from flask import Flask, render_template, request, jsonify, send_file

from flutter_generator import generate_full_app, generate_pubspec

app = Flask(__name__)
PROJECTS_DIR = Path(__file__).parent / "projects"
PROJECTS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("builder.html")


# ---------------------------------------------------------------------------
# Project CRUD API
# ---------------------------------------------------------------------------

@app.route("/api/projects", methods=["GET"])
def list_projects():
    projects = []
    for p in sorted(PROJECTS_DIR.iterdir()):
        if p.is_dir():
            meta_file = p / "meta.json"
            if meta_file.exists():
                meta = json.loads(meta_file.read_text())
                projects.append(meta)
    return jsonify(projects)


@app.route("/api/projects", methods=["POST"])
def create_project():
    data = request.get_json()
    name = data.get("name", "Untitled")
    slug = name.lower().replace(" ", "_").replace("-", "_")
    project_dir = PROJECTS_DIR / slug
    project_dir.mkdir(exist_ok=True)

    meta = {
        "name": name,
        "slug": slug,
        "pages": [
            {
                "name": "Home",
                "tree": {
                    "id": "root",
                    "type": "Scaffold",
                    "properties": {},
                    "children": [
                        {
                            "id": "appbar-1",
                            "type": "AppBar",
                            "properties": {"title": name},
                            "children": [],
                        },
                        {
                            "id": "center-1",
                            "type": "Center",
                            "properties": {},
                            "children": [
                                {
                                    "id": "text-1",
                                    "type": "Text",
                                    "properties": {
                                        "text": "Welcome to " + name,
                                        "fontSize": "24",
                                        "fontWeight": "bold",
                                    },
                                    "children": [],
                                }
                            ],
                        },
                    ],
                },
            }
        ],
        "theme": {"primaryColor": "blue", "brightness": "light"},
    }
    (project_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    return jsonify(meta), 201


@app.route("/api/projects/<slug>", methods=["GET"])
def get_project(slug):
    meta_file = PROJECTS_DIR / slug / "meta.json"
    if not meta_file.exists():
        return jsonify({"error": "Not found"}), 404
    return jsonify(json.loads(meta_file.read_text()))


@app.route("/api/projects/<slug>", methods=["PUT"])
def update_project(slug):
    meta_file = PROJECTS_DIR / slug / "meta.json"
    if not meta_file.exists():
        return jsonify({"error": "Not found"}), 404
    data = request.get_json()
    meta_file.write_text(json.dumps(data, indent=2))
    return jsonify(data)


@app.route("/api/projects/<slug>", methods=["DELETE"])
def delete_project(slug):
    project_dir = PROJECTS_DIR / slug
    if project_dir.exists():
        import shutil
        shutil.rmtree(project_dir)
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Code generation
# ---------------------------------------------------------------------------

@app.route("/api/projects/<slug>/generate", methods=["POST"])
def generate_code(slug):
    meta_file = PROJECTS_DIR / slug / "meta.json"
    if not meta_file.exists():
        return jsonify({"error": "Not found"}), 404
    meta = json.loads(meta_file.read_text())
    code = generate_full_app(meta["name"], meta.get("pages", []), meta.get("theme"))
    return jsonify({"code": code})


@app.route("/api/projects/<slug>/export", methods=["GET"])
def export_project(slug):
    meta_file = PROJECTS_DIR / slug / "meta.json"
    if not meta_file.exists():
        return jsonify({"error": "Not found"}), 404
    meta = json.loads(meta_file.read_text())

    main_dart = generate_full_app(meta["name"], meta.get("pages", []), meta.get("theme"))
    pubspec = generate_pubspec(meta["name"])

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{slug}/lib/main.dart", main_dart)
        zf.writestr(f"{slug}/pubspec.yaml", pubspec)
        zf.writestr(f"{slug}/analysis_options.yaml", "include: package:flutter_lints/flutter.yaml\n")
        zf.writestr(f"{slug}/README.md", f"# {meta['name']}\n\nBuilt with TourEx Flutter Builder.\n")
    buf.seek(0)
    return send_file(buf, mimetype="application/zip", as_attachment=True, download_name=f"{slug}.zip")


# ---------------------------------------------------------------------------
# Live preview code (returns Dart string for preview panel)
# ---------------------------------------------------------------------------

@app.route("/api/preview", methods=["POST"])
def preview():
    data = request.get_json()
    pages = data.get("pages", [])
    name = data.get("name", "Preview")
    theme = data.get("theme", None)
    code = generate_full_app(name, pages, theme)
    return jsonify({"code": code})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
