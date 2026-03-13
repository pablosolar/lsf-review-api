"""
LSF Review API — FastAPI para aprobación de posts por Laura.

Endpoints:
  GET  /aprobar?token=xxx          → aprueba el post
  GET  /rechazar?token=xxx         → muestra formulario de motivo
  POST /rechazar                   → guarda motivo y rechaza
  GET  /estado?token=xxx           → consulta el estado (para polling)
"""
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse

DB_PATH = Path("reviews.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                token TEXT PRIMARY KEY,
                estado TEXT DEFAULT 'pendiente',
                motivo TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="LSF Review API", lifespan=lifespan)


@app.get("/aprobar", response_class=HTMLResponse)
def aprobar(token: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM reviews WHERE token = ?", (token,)).fetchone()
        if not row:
            return HTMLResponse("<h2>Token no encontrado</h2>", status_code=404)
        conn.execute(
            "UPDATE reviews SET estado = 'aprobado', updated_at = CURRENT_TIMESTAMP WHERE token = ?",
            (token,)
        )
        conn.commit()

    return """
    <html>
    <head><meta charset="utf-8"><title>Post aprobado ✅</title></head>
    <body style="font-family:sans-serif;text-align:center;padding:60px;background:#f5ebe0;">
        <h1 style="color:#2d6a4f">✅ Post aprobado</h1>
        <p>El post se publicará en Instagram en breve. ¡Gracias Laura! 🌿</p>
    </body>
    </html>
    """


@app.get("/rechazar", response_class=HTMLResponse)
def rechazar_form(token: str):
    """Muestra formulario para que Laura escriba el motivo del rechazo."""
    return f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Rechazar post ❌</title>
        <style>
            body {{ font-family:sans-serif; max-width:500px; margin:60px auto; padding:20px; background:#f5ebe0; }}
            h2 {{ color:#c1121f; }}
            textarea {{ width:100%; padding:12px; border-radius:8px; border:1px solid #ccc; font-size:15px; margin:10px 0; }}
            button {{ background:#c1121f; color:white; padding:12px 30px; border:none; border-radius:8px; font-size:16px; cursor:pointer; width:100%; }}
            button:hover {{ background:#a00e18; }}
        </style>
    </head>
    <body>
        <h2>❌ Rechazar post</h2>
        <p>Cuéntame qué no te ha gustado para que el sistema aprenda y genere algo mejor:</p>
        <form method="post" action="/rechazar">
            <input type="hidden" name="token" value="{token}">
            <textarea name="motivo" rows="4" placeholder="Ej: El tono es demasiado clínico, la imagen no encaja con la marca..."></textarea>
            <button type="submit">Enviar rechazo</button>
        </form>
    </body>
    </html>
    """


@app.post("/rechazar", response_class=HTMLResponse)
def rechazar_submit(token: str = Form(...), motivo: str = Form(...)):
    """Guarda el motivo de rechazo."""
    motivo = motivo.strip() or "Sin motivo especificado"

    with get_db() as conn:
        row = conn.execute("SELECT * FROM reviews WHERE token = ?", (token,)).fetchone()
        if not row:
            return HTMLResponse("<h2>Token no encontrado</h2>", status_code=404)
        conn.execute(
            "UPDATE reviews SET estado = 'rechazado', motivo = ?, updated_at = CURRENT_TIMESTAMP WHERE token = ?",
            (motivo, token)
        )
        conn.commit()

    return f"""
    <html>
    <head><meta charset="utf-8"><title>Post rechazado ❌</title></head>
    <body style="font-family:sans-serif;text-align:center;padding:60px;background:#f5ebe0;">
        <h1 style="color:#c1121f">❌ Post rechazado</h1>
        <p>Motivo registrado: <strong>{motivo}</strong></p>
        <p>El sistema generará un nuevo post automáticamente. ¡Gracias Laura! 🌿</p>
    </body>
    </html>
    """


@app.get("/estado")
def estado(token: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM reviews WHERE token = ?", (token,)).fetchone()
        if not row:
            conn.execute("INSERT INTO reviews (token) VALUES (?)", (token,))
            conn.commit()
            return {"estado": "pendiente", "motivo": None}
        return {"estado": row["estado"], "motivo": row["motivo"]}


@app.get("/health")
def health():
    return {"status": "ok"}
