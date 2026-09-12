"""Contrato del analizador de recetas médicas.

⚠️ STUB — esta parte la implementa otra persona del equipo.
El bot ya deja la foto en disco y llama a `analizar_receta()`.
Solo hay que rellenar el cuerpo de la función respetando el contrato.
"""

from typing import TypedDict


class Medicamento(TypedDict, total=False):
    nombre: str          # "Paracetamol"
    presentacion: str    # "500 mg tabletas"
    dosis: str           # "1 tableta cada 8 horas"
    duracion: str        # "5 días"
    cantidad: str        # "15 tabletas"


class ResultadoReceta(TypedDict):
    ok: bool                        # False si la imagen no es legible / no es receta
    medicamentos: list[Medicamento]
    texto_crudo: str                # OCR o transcripción completa (para depurar)
    mensaje: str                    # texto listo para mandarle al usuario en Telegram.
                                    # ⚠️ EN INGLÉS: sale proyectado en la demo (ver AGENTS.md)


def analizar_receta(ruta_imagen: str, distrito: str, chat_id: int) -> ResultadoReceta:
    """Analiza la foto de una receta y devuelve los medicamentos detectados.

    Args:
        ruta_imagen: ruta local al .jpg ya descargado (p. ej. "data/recetas/12345_1.jpg").
        distrito: distrito de Lima que declaró el usuario (para buscar stock/farmacias).
        chat_id: id del chat de Telegram, por si necesitas trazabilidad.

    Returns:
        ResultadoReceta. Si algo falla, devolver ok=False y un `mensaje` explicativo;
        NO lanzar excepción (el bot ya captura, pero el mensaje sale más feo).
        `mensaje` SIEMPRE en inglés — es lo que se ve en la demo (AGENTS.md).
    """
    return {
        "ok": False,
        "medicamentos": [],
        "texto_crudo": "",
        "mensaje": (
            "🚧 The prescription analyzer isn't wired up yet.\n"
            f"I got your photo ({ruta_imagen}) and your district ({distrito}). "
            "As soon as the module is ready I'll send back your medicines."
        ),
    }
