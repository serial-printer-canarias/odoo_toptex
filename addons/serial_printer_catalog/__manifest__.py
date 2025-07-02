{
    'name': 'Catálogo TopTex',
    'version': '1.0.0',
    'category': 'Sales',
    'summary': 'Importación de productos TopTex para Odoo',
    'description': 'Crea productos y variantes desde la API de TopTex',
    'author': 'Serial Printer',
    'license': 'LGPL-3',
    'depends': ['base', 'product'],
    'data': [
        'ir.model.access.csv',
        'data/cron_product.xml',  # Solo si usas el cron, si no, bórralo o comenta
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}