{
    'name': 'Serial Printer Web Custom',
    'version': '18.0.1.0.0',
    'depends': ['website_sale'],
    'data': [],
    'assets': {
        'web.assets_frontend': [
            # OJO: solo este archivo. Nada de SCSS por ahora.
            'serial_printer_web_custom/static/src/js/sp_matrix_boot.js',
        ],
    },
}