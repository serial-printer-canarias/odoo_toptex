Serial Printer Sale Personalization
===================================

Modulo para Odoo 18/19 en Odoo.sh.

Objetivo:
- Crear una ficha de personalizacion desde presupuesto o factura.
- Agrupar el textil por producto base + color.
- Registrar marcajes por tallas, tecnica, posicion, color y tamano.
- Permitir archivos por ubicacion: pecho, espalda, cuello, manga, gorra.
- Guardar archivo de produccion + preview visible.
- Generar PDF de taller y enviar emails.

Instalacion en Odoo.sh:
1. Copia la carpeta serial_printer_sale_personalization en el repo.
2. Haz commit y push.
3. En Odoo: Apps > Actualizar lista de aplicaciones.
4. Instala "Serial Printer Sale Personalization".
5. Anade tu usuario al grupo: Serial Printer Personalizacion / Usuario.

Uso:
1. Abre un presupuesto.
2. Pulsa "Crear personalizacion".
3. Revisa la ficha creada.
4. Pulsa "Enviar al cliente" para mandar el enlace.
5. Cliente rellena formulario y sube archivos.
6. Recibes notificacion por email.
7. Genera "PDF taller".

Notas importantes:
- Desde factura tambien se puede crear ficha, pero la imagen siempre se toma del producto/variante de Odoo, no de la factura.
- La facturacion automatica de personalizaciones queda preparada para una fase 2.
- El modulo no toca TopTex ni el wizard actual de producto.
