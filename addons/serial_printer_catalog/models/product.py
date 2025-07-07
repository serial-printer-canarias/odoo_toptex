import logging
import json
import os
from odoo import models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def import_toptex_from_json(self, file_path=None):
        """
        Importa productos desde un JSON local grande de TopTex.
        Si file_path es None, busca automáticamente en varias rutas comunes.
        """
        # 1. Detectar archivo automáticamente si no se pasa ruta
        candidate_paths = []
        if file_path:
            candidate_paths.append(file_path)
        candidate_paths += [
            '/home/odoo/src/user/addons/serial_printer_catalog/data/toptex_catalog.json',
            '/data/build/addons/serial_printer_catalog/data/toptex_catalog.json',
            'addons/serial_printer_catalog/data/toptex_catalog.json',
            'serial_printer_catalog/data/toptex_catalog.json',
            'data/toptex_catalog.json',
        ]
        file_found = None
        for path in candidate_paths:
            _logger.info(f"🔎 Probando path: {path}")
            if os.path.exists(path):
                file_found = path
                _logger.info(f"✅ JSON encontrado en: {file_found}")
                break
        if not file_found:
            raise UserError("❌ No se pudo encontrar el archivo toptex_catalog.json en ninguna ruta común.")
        
        # 2. Leer el JSON (optimizado para grandes archivos)
        try:
            with open(file_found, "r", encoding="utf-8") as f:
                products_data = json.load(f)
            _logger.info(f"🟢 Cargado JSON: {file_found}")
        except Exception as e:
            raise UserError(f"❌ No se pudo abrir el JSON: {e}")

        # Si está envuelto en {'items': [...]}, desenrollar
        if isinstance(products_data, dict) and "items" in products_data:
            products_data = products_data["items"]

        # 3. Prepara atributos
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].create({'name': 'Color'})
        talla_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not talla_attr:
            talla_attr = self.env['product.attribute'].create({'name': 'Talla'})

        creados = 0
        for prod in products_data:
            brand = prod.get("brand", "TopTex")
            name = prod.get("designation", {}).get("es", "Producto sin nombre")
            default_code = prod.get("catalogReference", prod.get("productReference", ""))
            description = prod.get("description", {}).get("es", "")
            colors = prod.get("colors", [])
            all_colors = set()
            all_tallas = set()
            for color in colors:
                color_name = color.get("colors", {}).get("es", "") or color.get("colorName", "")
                if color_name: all_colors.add(color_name)
                for size in color.get("sizes", []):
                    talla = size.get("size", "")
                    if talla: all_tallas.add(talla)
            # Crea valores de atributo si faltan
            color_val_objs = []
            for c in all_colors:
                val = self.env['product.attribute.value'].search([('name', '=', c), ('attribute_id', '=', color_attr.id)], limit=1)
                if not val:
                    val = self.env['product.attribute.value'].create({'name': c, 'attribute_id': color_attr.id})
                color_val_objs.append(val)
            talla_val_objs = []
            for t in all_tallas:
                val = self.env['product.attribute.value'].search([('name', '=', t), ('attribute_id', '=', talla_attr.id)], limit=1)
                if not val:
                    val = self.env['product.attribute.value'].create({'name': t, 'attribute_id': talla_attr.id})
                talla_val_objs.append(val)
            attribute_lines = []
            if color_val_objs:
                attribute_lines.append({'attribute_id': color_attr.id, 'value_ids': [(6, 0, [v.id for v in color_val_objs])]})
            if talla_val_objs:
                attribute_lines.append({'attribute_id': talla_attr.id, 'value_ids': [(6, 0, [v.id for v in talla_val_objs])]})
            vals = {
                'name': f"{brand} {name}".strip(),
                'default_code': default_code,
                'type': 'consu',
                'is_storable': True,
                'description_sale': description,
                'categ_id': self.env.ref("product.product_category_all").id,
                'attribute_line_ids': [(0, 0, l) for l in attribute_lines],
            }
            existe = self.env['product.template'].search([('default_code', '=', default_code)], limit=1)
            if not existe:
                template = self.create(vals)
                creados += 1
                # Variante: sin stock, sin imágenes, sin precio (a rellenar luego)
            else:
                _logger.info(f"⏭️ Ya existe plantilla {existe.name} [{existe.id}]")
        _logger.info(f"🚀 FIN: {creados} plantillas de producto creadas con variantes color/talla (TopTex)")