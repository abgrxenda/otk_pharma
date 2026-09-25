# Location: otk_pharma_onboarding/__manifest__.py

{
    'name': 'Pharma B2B Onboarding',
    'version': '18.0.1.0.0',
    'category': 'Pharmacy',
    'summary': 'B2B partner onboarding with digital contract signing',
    'description': """
        Handles the full onboarding flow for partner pharmacies:
        - Public registration form
        - Digital contract e-signature
        - Admin activation with delivery fee and discount tier
        - Welcome and rejection email notifications
    """,
    'author': 'Omer Kadir',
    'depends': [
        'base',
        'mail',
        'portal',
        'sale_management',
        'account',
        'website',
        'website_sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_templates.xml',
        'views/backend_views.xml',
        'views/portal_templates.xml',
    ],
    'post_init_hook': 'create_delivery_fee_product',
    'images': [
        'static/description/pharmacy-thumbnail.png',
        'static/description/pharmacy-register.png',
        'static/description/pharmacy-b2b.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'OPL-1',
}