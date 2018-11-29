# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################

from odoo import fields, models, api, _
import datetime
from datetime import timedelta
import pytz
from pytz import timezone
import time
from odoo.exceptions import UserError

class pos_order(models.Model):
    _inherit = "pos.order"

    # @api.one
    # @api.depends('invoice_ids', 'invoice_ids.residual')
    # def _calculate_amount_due(self):
    #     total = 0.00
    #     for invoice in self.invoice_ids:
    #         total += invoice.residual
    #     if not self.invoice_ids:
    #         total = self.amount_total
    #     self.amount_due = total
    #
    # amount_due = fields.Float("Amount Due", compute="_calculate_amount_due")

    @api.model
    def create_pos_order(self, vals):
        pos_pool = self.env['pos.order']
        prod_pool = self.env['product.product']
        pos_line_pool = self.env['pos.order.line']
        customer_id = vals.get('customer_id')
        orderline = vals.get('orderlines')
        journals = vals.get('journals')
        location_id = vals.get('location_id')
        sale_id = False
        st_date = False
        if self.env.user and self.env.user.tz:
            tz = timezone(self.env.user.tz)
        else:
            tz = pytz.utc
        c_time = datetime.datetime.now(tz)
        hour_tz = int(str(c_time)[-5:][:2])
        min_tz = int(str(c_time)[-5:][3:])
        sign = str(c_time)[-6][:1]
        c_time = c_time.date()
        if vals.get('order_date'):
            if sign == '-':
                st_date = (datetime.datetime.strptime(vals.get('order_date'), '%Y-%m-%d %H:%M') + timedelta(hours=hour_tz, minutes=min_tz)).strftime('%Y-%m-%d %H:%M')
            if sign == '+':
                st_date = (datetime.datetime.strptime(vals.get('order_date'), '%Y-%m-%d %H:%M') - timedelta(hours=hour_tz, minutes=min_tz)).strftime('%Y-%m-%d %H:%M')
        if not vals.get('sale_order_id'):
            if customer_id:
                customer_id = int(customer_id)
                sale = {
                    'partner_id': customer_id,
                    'partner_invoice_id': vals.get('partner_invoice_id', customer_id),
                    'partner_shipping_id': vals.get('partner_shipping_id', customer_id),
#                     'from_pos': True,
                    'requested_date' : vals.get('requested_date') or False,
                    'date_order': st_date or datetime.datetime.now(),
                    'note': vals.get('note') or '',
                }
                new = pos_pool.new({'partner_id': customer_id})
                # new.onchange_partner_id()
                if vals.get('pricelist_id'):
                    sale.update({'pricelist_id': vals.get('pricelist_id')})
                if vals.get('partner_shipping_id'):
                    sale.update({'partner_shipping_id': vals.get('partner_shipping_id')})
                if vals.get('partner_invoice_id'):
                    sale.update({'partner_invoice_id': vals.get('partner_invoice_id')})
                if vals.get('warehouse_id'):
                    sale.update({'warehouse_id':vals.get('warehouse_id')})
                sale_id = pos_pool.create(sale)
                #create sale order line
                sale_line = {'order_id': sale_id.id}
                for line in orderline:
                    prod_rec = prod_pool.browse(line['product_id'])
                    sale_line.update({
                        'name': prod_rec.name or False,
                        'product_id': prod_rec.id,
                        'product_uom_qty': line['qty'],
                        'discount': line.get('discount'),
                        'price_unit': line.get('price_unit'),
                    })
                    new_prod = pos_line_pool.new({'product_id': prod_rec.id})
                    prod = new_prod.product_id_change()
                    sale_line.update(prod)
                    sale_line.update({'price_unit': line['price_unit']});
                    taxes = map(lambda a: a.id, prod_rec.taxes_id)
#                     if sale_line.get('tax_id'):
#                         sale_line.update({'tax_id': sale_line.get('tax_id')})
                    if taxes:
                        sale_line.update({'tax_id': [(6, 0, taxes)]})
                    sale_line.pop('domain')
                    sale_line.update({'product_uom': prod_rec.uom_id.id})
                    pos_line_pool.create(sale_line)

                if self._context.get('confirm'):
                    sale_id.action_confirm()
                if self._context.get('paid'):
                    sale_id.action_confirm()
                    for picking_id in sale_id.picking_ids:
                        if not picking_id.delivery_order(location_id):
                            return False
                    if not sale_id._make_payment(journals):
                        return False


        elif vals.get('sale_order_id') and vals.get('edit_quotation'):
            if customer_id:
                customer_id = int(customer_id)
                sale_id = self.browse(vals.get('sale_order_id'))
                if sale_id:
                    vals = {
                        'partner_id': customer_id,
                        'partner_invoice_id': vals.get('partner_invoice_id', customer_id),
                        'partner_shipping_id': vals.get('partner_shipping_id', customer_id),
#                         'from_pos': True,
                        'requested_date' : vals.get('requested_date') or False,
                        'date_order': st_date or datetime.datetime.now(),
                        'note': vals.get('note') or '',
                        'pricelist_id': vals.get('pricelist_id') or False,
                    }
                    sale_id.write(vals)
                    [line.unlink() for line in sale_id.order_line]
                    sale_line = {'order_id': sale_id.id}
                    for line in orderline:
                        prod_rec = prod_pool.browse(line['product_id'])
                        sale_line.update({
                            'name': prod_rec.name or False,
                            'product_id': prod_rec.id,
                            'product_uom_qty': line['qty'],
                            'discount': line.get('discount'),
                        })
                        new_prod = pos_line_pool.new({'product_id': prod_rec.id})
                        prod = new_prod.product_id_change()
                        sale_line.update(prod)
                        sale_line.update({'price_unit': line['price_unit']});
                        taxes = map(lambda a: a.id, prod_rec.taxes_id)
                        if sale_line.get('tax_id'):
                            sale_line.update({'tax_id': sale_line.get('tax_id')})
                        elif taxes:
                            sale_line.update({'tax_id': [(6, 0, taxes)]})
                        sale_line.pop('domain')
                        sale_line.update({'product_uom': prod_rec.uom_id.id})
                        pos_line_pool.create(sale_line)
                    if journals:
                        if sale_id.state in ['draft', 'sent']:
                            sale_id.action_confirm()
                            # for picking_id in sale_id.picking_ids:
                            #     if not picking_id.delivery_order(location_id):
                            #         return False
                        for picking_id in sale_id.picking_ids:
                            if picking_id.state != "done":
                                if not picking_id.delivery_order(location_id):
                                    return False
                        sale_id._make_payment(journals)

        elif vals.get('sale_order_id') and not vals.get('edit_quotation'):
            sale_id = self.browse(vals.get('sale_order_id'))
            if sale_id:
                inv_id = False
                if vals.get('inv_id'):
                    inv_id = vals.get('inv_id')
                if sale_id.state in ['draft', 'sent']:
                    sale_id.action_confirm()
                for picking_id in sale_id.picking_ids:
                    if picking_id.state != "done":
                        if not picking_id.delivery_order(location_id):
                            return False
                sale_id._make_payment(journals)
        if not sale_id:
            return  False
        if sale_id._action_order_lock():
            sale_id.action_done()
        return sale_id.read()

