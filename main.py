"""
LSF Review API — FastAPI para aprobación de posts por Laura.

Endpoints:
  GET /aprobar?token=xxx        → aprueba el post
  GET /rechazar?token=xxx&motivo=yyy → rechaza el post
  GET /estado?token=xxx         → consulta el estado (para polling)
"""
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

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
            raise HTTPException(status_code=404, detail="Token no encontrado")
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
        <p>El post se publicará en Instagram. ¡Gracias Laura! 🌿</p>
    </body>
    </html>
    """


@app.get("/rechazar", response_class=HTMLResponse)
def rechazar(token: str, motivo: str = "Sin motivo especificado"):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM reviews WHERE token = ?", (token,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Token no encontrado")
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
        <p>Se generará un nuevo post. ¡Gracias Laura! 🌿</p>
    </body>
    </html>
    """


@app.get("/estado")
def estado(token: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM reviews WHERE token = ?", (token,)).fetchone()
        if not row:
            # Token nuevo — lo registramos como pendiente
            conn.execute("INSERT INTO reviews (token) VALUES (?)", (token,))
            conn.commit()
            return {"estado": "pendiente", "motivo": None}
        return {"estado": row["estado"], "motivo": row["motivo"]}


@app.get("/health")
def health():
    return {"status": "ok"}
