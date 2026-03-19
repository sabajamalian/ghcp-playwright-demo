import json
import os
import uuid
from datetime import datetime, timezone

from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder="static")

DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")


def read_data():
    if not os.path.exists(DATA_FILE):
        return {"lists": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def write_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def find_list(data, list_id):
    for lst in data["lists"]:
        if lst["id"] == list_id:
            return lst
    return None


def find_task(lst, task_id):
    for task in lst["tasks"]:
        if task["id"] == task_id:
            return task
    return None


# ── Serve frontend ──────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


# ── Lists API ───────────────────────────────────────────────────

@app.route("/api/lists", methods=["GET"])
def get_lists():
    data = read_data()
    return jsonify(data["lists"])


@app.route("/api/lists", methods=["POST"])
def create_list():
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400

    new_list = {
        "id": uuid.uuid4().hex[:12],
        "name": name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "tasks": [],
    }
    data = read_data()
    data["lists"].append(new_list)
    write_data(data)
    return jsonify(new_list), 201


@app.route("/api/lists/<list_id>", methods=["PUT"])
def update_list(list_id):
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400

    data = read_data()
    lst = find_list(data, list_id)
    if not lst:
        return jsonify({"error": "List not found"}), 404

    lst["name"] = name
    write_data(data)
    return jsonify(lst)


@app.route("/api/lists/<list_id>", methods=["DELETE"])
def delete_list(list_id):
    data = read_data()
    original_len = len(data["lists"])
    data["lists"] = [l for l in data["lists"] if l["id"] != list_id]
    if len(data["lists"]) == original_len:
        return jsonify({"error": "List not found"}), 404
    write_data(data)
    return "", 204


# ── Tasks API ───────────────────────────────────────────────────

@app.route("/api/lists/<list_id>/tasks", methods=["POST"])
def create_task(list_id):
    body = request.get_json(silent=True) or {}
    title = (body.get("title") or "").strip()
    if not title:
        return jsonify({"error": "Title is required"}), 400

    data = read_data()
    lst = find_list(data, list_id)
    if not lst:
        return jsonify({"error": "List not found"}), 404

    new_task = {
        "id": uuid.uuid4().hex[:12],
        "title": title,
        "completed": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    lst["tasks"].append(new_task)
    write_data(data)
    return jsonify(new_task), 201


@app.route("/api/lists/<list_id>/tasks/<task_id>", methods=["PUT"])
def update_task(list_id, task_id):
    body = request.get_json(silent=True) or {}

    data = read_data()
    lst = find_list(data, list_id)
    if not lst:
        return jsonify({"error": "List not found"}), 404
    task = find_task(lst, task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    if "title" in body:
        title = (body["title"] or "").strip()
        if not title:
            return jsonify({"error": "Title cannot be empty"}), 400
        task["title"] = title
    if "completed" in body:
        task["completed"] = bool(body["completed"])

    write_data(data)
    return jsonify(task)


@app.route("/api/lists/<list_id>/tasks/<task_id>", methods=["DELETE"])
def delete_task(list_id, task_id):
    data = read_data()
    lst = find_list(data, list_id)
    if not lst:
        return jsonify({"error": "List not found"}), 404

    original_len = len(lst["tasks"])
    lst["tasks"] = [t for t in lst["tasks"] if t["id"] != task_id]
    if len(lst["tasks"]) == original_len:
        return jsonify({"error": "Task not found"}), 404

    write_data(data)
    return "", 204


if __name__ == "__main__":
    app.run(debug=True, port=3003)
