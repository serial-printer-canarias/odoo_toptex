import json
import logging
import requests
from odoo import models, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_toptex_products(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        if not all([username, password, api_key, proxy_url]):
            raise UserError(_("❌ Faltan parámetros de API TopTex."))

        # 1. Autenticación
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_payload = {"username": username, "password": password}
        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        if auth_response.status_code != 200:
            raise UserError(_("❌ Error autenticando: %s") % auth_response.text)
        token = auth_response.json().get("token")
        if not token:
            raise UserError(_("❌ No se recibió un token."))

        # 2. Enlace temporal del catálogo
        catalog_url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&result_in_file=1"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
        }
        link_response = requests.get(catalog_url, headers=headers)
        if link_response.status_code != 200:
            raise UserError(_("❌ Error obteniendo enlace catálogo: %s") % link_response.text)
        file_url = link_response.json().get('link')
        if not file_url:
            raise UserError(_("❌ No se recibió el enlace de descarga de catálogo."))

        # 3. Espera hasta que el JSON esté disponible (bucle cada 30s, máximo 8 minutos)
        import time
        for intento in range(16):
            json_response = requests.get(file_url, headers=headers)
            if json_response.status_code == 200:
                try:
                    products_data = json_response.json()
                    if isinstance(products_data, list) and len(products_data) > 10:
                        break  # JSON listo y válido
                except Exception:
                    pass
            _logger.info(f"⏳ Esperando generación del JSON... ({intento+1}/16)")
            time.sleep(30)
        else:
            raise UserError(_("❌ El archivo JSON no estuvo disponible a tiempo."))

        # 4. MAPEO de productos con variantes y atributos
        attr_obj = self.env['product.attribute']
        attr_val_obj = self.env['product.attribute.value']
        categ = self.env.ref("product.product_category_all")
        brand_field = "brand"  # Si tienes una tabla para marcas, deberías mapearla

        for prod in products_data:
            # Valores básicos
            code = prod.get("catalogReference") or prod.get("productReference") or ""
            name = prod.get("designation", {}).get("es", "") or code
            desc = prod.get("description", {}).get("es", "")
            marca = prod.get("brand", "") or prod.get("brand", {}).get("name", {}).get("es", "") or ""
            colores = prod.get("colors", [])
            prices = prod.get("prices", [])

            # Generar sets de variantes
            color_names = set()
            size_names = set()
            for c in colores:
                color_name = c.get("colors", {}).get("es", "")
                if color_name:
                    color_names.add(color_name)
                for sz in c.get("sizes", []):
                    talla = sz.get("size") or sz.get("sizeCode")
                    if talla:
                        size_names.add(talla)

            # Crear atributos si no existen
            color_attr = attr_obj.search([('name', '=', 'Color')], limit=1) or attr_obj.create({'name': 'Color'})
            size_attr = attr_obj.search([('name', '=', 'Talla')], limit=1) or attr_obj.create({'name': 'Talla'})
            color_vals = {}
            for cname in color_names:
                v = attr_val_obj.search([('name', '=', cname), ('attribute_id', '=', color_attr.id)], limit=1)
                if not v:
                    v = attr_val_obj.create({'name': cname, 'attribute_id': color_attr.id})
                color_vals[cname] = v
            size_vals = {}
            for sname in size_names:
                v = attr_val_obj.search([('name', '=', sname), ('attribute_id', '=', size_attr.id)], limit=1)
                if not v:
                    v = attr_val_obj.create({'name': sname, 'attribute_id': size_attr.id})
                size_vals[sname] = v

            attribute_lines = []
            if color_vals:
                attribute_lines.append({'attribute_id': color_attr.id, 'value_ids': [(6, 0, [v.id for v in color_vals.values()])]})
            if size_vals:
                attribute_lines.append({'attribute_id': size_attr.id, 'value_ids': [(6, 0, [v.id for v in size_vals.values()])]})

            # No duplicar productos
            existing = self.env['product.template'].search([('default_code', '=', code)], limit=1)
            if existing:
                continue

            # Precio coste y venta (tira del primer color/talla que encuentre)
            precio_venta = 0.0
            precio_coste = 0.0
            for c in colores:
                for sz in c.get("sizes", []):
                    if sz.get("prices"):
                        precio_coste = float(sz["prices"][0]["price"])
                        precio_venta = round(precio_coste * 1.30, 2)  # margen editable
                        break
                if precio_venta:
                    break

            # Crear producto
            template_vals = {
                'name': name,
                'default_code': code,
                'type': 'consu',
                'is_storable': True,
                'description_sale': desc,
                'categ_id': categ.id,
                'list_price': precio_venta,
                'standard_price': precio_coste,
                'attribute_line_ids': [(0, 0, line) for line in attribute_lines],
                # Si tienes módulo de marcas, añade el id aquí
            }
            t = self.create(template_vals)
            _logger.info(f"✅ Creada plantilla {name} [{code}]")

        _logger.info(f"FTN: {len(products_data)} productos procesados TopTex")