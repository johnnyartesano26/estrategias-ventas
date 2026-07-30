#!/usr/bin/env python3
"""
update_encuestas.py
Lee las respuestas de la encuesta desde Google Sheet,
promedia por cliente y actualiza los scores en el dashboard.

Mapeo encuesta → dashboard:
  calidad_cerveza (1-5)  → calidad_del_producto.score (×2 → 0-10)
  atencion_servicio (1-5) → calidad_del_servicio.score (×2 → 0-10)  
  nps (0-10)              → calidad_del_servicio.nps (×10 → 0-100)
  feedback con texto      → cuenta como queja_ultimo_trimestre

Uso: python3 update_encuestas.py
"""

import json
import csv
import io
import os
import sys
from datetime import datetime
from collections import defaultdict
import requests

# Config
SHEET_ID = "1N5efHRcCRtnvnvd1nklPKAhVlvC2UjvEKYkcZ1iY5oM"
SHEET_CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")


def load_survey_data():
    """Descarga y parsea el CSV de respuestas de encuesta."""
    resp = requests.get(SHEET_CSV_URL, timeout=30)
    resp.raise_for_status()
    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    print(f"  Encuestas cargadas: {len(rows)} respuestas")
    return rows


def average_by_client(rows):
    """Agrupa respuestas por cliente_id y promedia scores."""
    clients = defaultdict(lambda: {
        "nps": [], "calidad": [], "servicio": [],
        "entregas": [], "musica": [], "comida": [], "higiene": [],
        "feedbacks": [], "total": 0
    })

    for r in rows:
        cid = (r.get("Cliente ID") or "").strip()
        if not cid or cid == "PROSPECTO":
            continue  # Skip prospects for now

        c = clients[cid]
        c["total"] += 1

        for field, key in [
            ("NPS", "nps"), ("Calidad Cerveza", "calidad"),
            ("Atención servicio", "servicio"), ("Entregas", "entregas"),
            ("Musica Sonido", "musica"), ("Comida", "comida"),
            ("Higiene", "higiene")
        ]:
            val = r.get(field, "").strip()
            if val:
                try:
                    c[key].append(float(val))
                except ValueError:
                    pass

        fb = (r.get("Feedback") or "").strip()
        if fb and len(fb) > 3:
            c["feedbacks"].append(fb)

    # Build result
    result = {}
    for cid, c in clients.items():
        avg = lambda lst: round(sum(lst) / len(lst), 1) if lst else None
        result[cid] = {
            "total_respuestas": c["total"],
            "nps_promedio": avg(c["nps"]),
            "calidad_promedio": avg(c["calidad"]),
            "servicio_promedio": avg(c["servicio"]),
            "entregas_promedio": avg(c["entregas"]),
            "musica_promedio": avg(c["musica"]),
            "comida_promedio": avg(c["comida"]),
            "higiene_promedio": avg(c["higiene"]),
            "quejas_count": len(c["feedbacks"]),
            "ultimos_feedbacks": c["feedbacks"][-3:],
        }

    return result


def update_dashboard(scores):
    """Actualiza EMBEDDED_DATA en index.html con los promedios de encuesta."""
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    idx = html.find("EMBEDDED_DATA = {")
    json_start = html.find("{", idx)
    depth = 0
    json_end = json_start
    for i in range(json_start, len(html)):
        if html[i] == "{":
            depth += 1
        elif html[i] == "}":
            depth -= 1
            if depth == 0:
                json_end = i
                break

    data = json.loads(html[json_start : json_end + 1])

    updated = 0
    for c in data["customers"]:
        cid = c["id"]
        if cid not in scores:
            continue

        s = scores[cid]
        print(f"\n  {cid} — {c['nombre'][:40]}")
        print(f"    Respuestas: {s['total_respuestas']}")

        if s["nps_promedio"] is not None:
            old = c["calidad_del_servicio"]["nps"]
            c["calidad_del_servicio"]["nps"] = round(s["nps_promedio"] * 10)
            print(f"    NPS: {old} → {c['calidad_del_servicio']['nps']}")

        if s["calidad_promedio"] is not None:
            old = c["calidad_del_producto"]["score"]
            c["calidad_del_producto"]["score"] = round(s["calidad_promedio"] * 2, 1)
            print(f"    Calidad producto: {old} → {c['calidad_del_producto']['score']}")

        if s["servicio_promedio"] is not None:
            old = c["calidad_del_servicio"]["score"]
            c["calidad_del_servicio"]["score"] = round(s["servicio_promedio"] * 2, 1)
            print(f"    Calidad servicio: {old} → {c['calidad_del_servicio']['score']}")

        if s["quejas_count"] > 0:
            c["calidad_del_servicio"]["quejas_ultimo_trimestre"] = s["quejas_count"]
            print(f"    Quejas/feedback: {s['quejas_count']}")

        if s["ultimos_feedbacks"]:
            if "encuestas" not in c:
                c["encuestas"] = {}
            c["encuestas"]["ultimos_feedbacks"] = s["ultimos_feedbacks"]
            c["encuestas"]["total_respuestas"] = s["total_respuestas"]

        updated += 1

    if updated == 0:
        print("\n  ⚠️  Ningún cliente tiene encuestas todavía.")
        return False

    # Guardar
    new_json = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    before = html[:json_start]
    after = html[json_end + 1 :]
    new_html = before + new_json + after

    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(new_html)

    print(f"\n  ✅ {updated} clientes actualizados en el dashboard.")
    return True


def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Actualizando encuestas → dashboard...")
    rows = load_survey_data()
    if not rows:
        print("  ⚠️  No hay respuestas en el Sheet.")
        return 1

    scores = average_by_client(rows)
    if not scores:
        print("  ⚠️  No hay respuestas de clientes registrados.")
        return 1

    ok = update_dashboard(scores)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
