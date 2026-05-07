FIX v1.18 - Solo guardado formulario cliente + PDF taller

Sustituye la carpeta serial_printer_sale_personalization por esta completa y actualiza el módulo en Odoo.

Cambios reales:
- controllers/portal.py: guarda todos los marcajes antes de confirmar, y mantiene compatibilidad con save_marking antiguo.
- views/portal_templates.xml: usa un formulario global para que "Guardar todo" y "Guardar todo y enviar ficha" registren técnica, posición, color, tallas, medidas, notas y archivos de todos los marcajes.

No cambia modelos, vistas backend, presupuesto ni lógica de agrupación.
