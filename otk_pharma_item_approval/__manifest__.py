# otk_pharma_item_approval/__manifest__.py

{
    'name': 'Pharma Item Approval',
    'version': '18.0.1.2.0',
    'category': 'Pharmacy',
    'summary': 'Controlled item approval gate for B2B pharmacy orders',
    'description': """
        Marks certain products as controlled compounds.
        When a small pharmacy places an order containing a controlled item,
        the entire order is held pending approval from the main pharmacy.
        A one-time auth code is issued to release the order.
    """,
    'author': 'Omer Kadir',
    'depends': [
        'base',
        'mail',
        'portal',
        'product',
        'sale',
        'sale_management',
        'otk_pharma_onboarding',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_templates.xml',
        'data/cron.xml',
        'views/backend_views.xml',
        'views/portal_templates.xml',
        'views/portal_prescription_templates.xml',
    ],
    'images': [
        'static/description/pharmacy-thumbnail.png',
        'static/description/pharma-approval.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'OPL-1',
}
