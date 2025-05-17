from odoo import models, fields, api
import requests

class SerialPrinterProduct(models.Model):
    _inherit = 'product.template'

    toptex_id = fields.Char(string="TopTex ID")

    @api.model
    def import_products_from_api(self):
        # Aquí va la llamada real a la API de TopTex
        pass

    @api.model
    def sync_stock_from_api(self):
        # Aquí va la lógica de sincronización de stock
        pass
