import logging
from odoo import models, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        if not all([username, password, api_key, proxy_url]):
            raise UserError(_("❌ Faltan credenciales o parámetros del sistema."))

        # 1. Autenticación
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_payload = {"username": username, "password": password}
        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        if auth_response.status_code != 200:
            raise UserError(_(f"❌ Error autenticando: {auth_response.status_code} - {auth_response.text}"))
        token = auth_response.json().get("token")
        if not token:
            raise UserError(_("❌ No se recibió un token válido."))
        _logger.info("🔐 Token recibido correctamente.")

        # 2. Petición para obtener el enlace temporal de productos
        catalog_url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&result_in_file=1"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }
        link_response = requests.get(catalog_url, headers=headers)
        if link_response.status_code != 200:
            raise UserError(_(f"❌ Error obteniendo enlace de catálogo: {link_response.status_code} - {link_response.text}"))
        link_data = link_response.json()
        file_url = link_data.get('link')
        if not file_url:
            raise UserError(_("❌ No se recibió un enlace de descarga de catálogo."))
        _logger.info(f"🔗 Link temporal de catálogo: {file_url}")

        # 3. Esperar hasta que el archivo JSON esté disponible (polling)
        import time
        max_wait = 420  # 7 minutos
        waited = 0
        products_data = None
        while waited < max_wait:
            file_response = requests.get(file_url, headers=headers)
            try:
                products_data = file_response.json()
                if isinstance(products_data, list) and products_data:
                    _logger.info(f"✅ JSON listo con {len(products_data)} productos recibidos tras {waited} segundos.")
                    break
            except Exception:
                _logger.info(f"❌ JSON no listo. Esperando 10 segundos más...")
            time.sleep(10)
            waited += 10

        if not products_data or not isinstance(products_data, list):
            raise UserError(_("🚨 El catálogo descargado no es una lista de productos válida o ha tardado demasiado en generarse."))

        _logger.info(f"🟢 Procesando {len(products_data)} productos TopTex...")

        # 4. Procesar y mapear cada producto SOLO info principal y variantes (no imágenes, no stock)
        for prod in products_data:
            # MARCA
            brand = prod.get("brand") or {}
            brand_name = ""
            if brand:
                brand_name = (
                    brand.get("name", {}).get("es")
                    or brand.get("name", {}).get("en")
                    or brand.get("name", {}).get("fr")
                    or "TopTex"
                )

            # NOMBRE, REFERENCIA, DESCRIPCIÓN
            name = prod.get("designation", {}).get("es") or prod.get("designation", {}).get("en") or "Producto sin nombre"
            default_code = prod.get("catalogReference") or prod.get("productReference") or ""
            description = prod.get("description", {}).get("es") or ""

            # VARIANTES (COLORES Y TALLAS)
            all_colors = set()
            all_sizes = set()
            for color in prod.get("colors", []):
                color_name = (
                    color.get("colors", {}).get("es")
                    or color.get("colors", {}).get("en")
                    or color.get("colors", {}).get("fr")
                    or ""
                )
                if color_name:
                    all_colors.add(color_name)
                for size in color.get("sizes", []):
                    size_name = size.get("size")
                    if size_name:
                        all_sizes.add(size_name)

            # Crear atributos y valores
            color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
            if not color_attr:
                color_attr = self.env['product.attribute'].create({'name': 'Color'})
            size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
            if not size_attr:
                size_attr = self.env['product.attribute'].create({'name': 'Talla'})
            color_vals = []
            for c in all_colors:
                val = self.env['product.attribute.value'].search([('name', '=', c), ('attribute_id', '=', color_attr.id)], limit=1)
                if not val:
                    val = self.env['product.attribute.value'].create({'name': c, 'attribute_id': color_attr.id})
                color_vals.append(val.id)
            size_vals = []
            for s in all_sizes:
                val = self.env['product.attribute.value'].search([('name', '=', s), ('attribute_id', '=', size_attr.id)], limit=1)
                if not val:
                    val = self.env['product.attribute.value'].create({'name': s, 'attribute_id': size_attr.id})
                size_vals.append(val.id)

            attribute_lines = []
            if color_vals:
                attribute_lines.append({'attribute_id': color_attr.id, 'value_ids': [(6, 0, color_vals)]})
            if size_vals:
                attribute_lines.append({'attribute_id': size_attr.id, 'value_ids': [(6, 0, size_vals)]})

            # Buscar categoría si existe
            categ = self.env.ref("product.product_category_all")
            # PRECIOS (coste y venta, primero por defecto para plantilla, luego por variante se mejora)
            price_cost = 0.0
            price_sale = 0.0
            # Intenta pillar el primer precio de la lista, por si lo necesitas para la plantilla:
            price_list = prod.get("prices", [])
            if price_list and isinstance(price_list, list):
                price_cost = float(price_list[0].get("price", 0.0))
                price_sale = price_cost * 1.25  # o usar otro markup

            template_vals = {
                'name': f"{brand_name} {name}".strip(),
                'default_code': default_code,
                'type': 'consu',
                'is_storable': True,
                'description_sale': description,
                'categ_id': categ.id if categ else False,
                'attribute_line_ids': [(0, 0, line) for line in attribute_lines],
                'standard_price': price_cost,
                'lst_price': price_sale,
            }
            template = self.env['product.template'].create(template_vals)
            _logger.info(f"✅ Creada plantilla {template.name} [{template.id}]")

            # -- Precios por variante (sólo ejemplo, se puede mejorar):
            # for variant in template.product_variant_ids:
            #    # Aquí podrías buscar la combinación color/talla para poner precios individualizados

        _logger.info("✅ Sincronización de productos terminada. (SOLO plantillas y variantes)")