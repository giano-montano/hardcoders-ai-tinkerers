# Fixture de respuesta de precios

`prices-recorded.json` deriva de la respuesta oficial registrada el 2026-09-12
para grupo 1515, familia 3, concentración 20mg, ubigeo 150116.
Se seleccionó una fila por combinación sustancia/forma (tres filas).

Se conservaron estructura, sustancia, concentración, formas, precios y fracciones
de la respuesta. Identificadores de establecimiento/producto, farmacia, dirección,
teléfono, laboratorio y titular se sustituyeron por datos sintéticos. `cantidad`
se ajustó al subconjunto para representar una respuesta completa de prueba.
No representa establecimientos reales ni contiene recetas, chats o datos del usuario.

Los tests ejecutan fetch y su normalizador reales sustituyendo solamente el cliente
HTTP. Rank se invoca como consumidor sin modificar su implementación ni usar red.
