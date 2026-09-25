from odoo import models, fields, api


class SaleOrderPrescriptionUpload(models.Model):
    _name = 'sale.order.prescription.upload'
    _description = 'Sale Order Prescription Upload'
    _order = 'order_id, product_id'

    order_id = fields.Many2one(
        'sale.order', string='Sales Order', required=True, ondelete='cascade',
    )
    product_id = fields.Many2one(
        'product.product', string='Product', required=True,
    )
    product_name = fields.Char(
        string='Product Name', related='product_id.display_name', readonly=True,
    )
    prescription_file = fields.Binary(
        string='Prescription File', required=True, attachment=True,
    )
    prescription_filename = fields.Char(
        string='File Name',
    )
    state = fields.Selection([
        ('pending', 'Pending Upload'),
        ('uploaded', 'Uploaded'),
    ], string='Status', default='pending', required=True)

    def action_mark_uploaded(self):
        self.write({'state': 'uploaded'})

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('prescription_file'):
                vals['state'] = 'uploaded'
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('prescription_file'):
            vals['state'] = 'uploaded'
        return super().write(vals)
