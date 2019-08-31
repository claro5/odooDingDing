# -*- coding: utf-8 -*-
###################################################################################
#
#    Copyright (C) 2019 SuXueFeng
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###################################################################################
import json
import logging
import requests
from requests import ReadTimeout
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class DingDingApprovalMain(models.Model):
    """
    所有需要提交审批的单据都需要继承本模型，方便使用共有的方法函数
    """
    _name = 'dingding.approval.main'
    _inherit = ['mail.thread']
    _description = "审批表单基类"
    _rec_name = 'title'

    OASTATE = [
        ('00', '草稿'),
        ('01', '审批中'),
        ('02', '审批结束'),
    ]
    OARESULT = [
        ('agree', '同意'),
        ('refuse', '拒绝'),
        ('redirect', '转交'),
    ]
    
    active = fields.Boolean(string=u'Active', default=True)
    process_code = fields.Char(string='单据编号', index=True, copy=False)
    business_id = fields.Char(string='审批实例业务编号', index=True, copy=False)
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id.id)
    originator_user_id = fields.Many2one('hr.employee', string=u'发起人', domain=[('ding_id', '!=', False)])
    originator_dept_id = fields.Many2one('hr.department', string=u'发起部门', domain=[('ding_id', '!=', False)])
    title = fields.Char(string='标题')
    process_instance_id = fields.Char(string='钉钉审批实例id')
    reason_leave = fields.Text(string=u'事由')
    oa_state = fields.Selection(string=u'单据状态', selection=OASTATE, default='00')
    oa_result = fields.Selection(string=u'审批结果', selection=OARESULT)
    oa_message = fields.Char(string='审批消息')
    oa_url = fields.Char(string='钉钉单据url')
    approver_users = fields.Many2many('hr.employee', string=u'审批人')
    make_copy_users = fields.Many2many('hr.employee', string=u'抄送人')

    @api.multi
    def summit_approval(self):
        """
        提交审批按钮，将单据审批信息发送到钉钉
        :return:
        """
        pass

    @api.multi
    def unlink(self):
        for res in self:
            if res.oa_state != '00':
                raise UserError('非草稿单据不能删除!')
        super(DingDingApprovalMain, self).unlink()

    @api.model
    def _summit_din_approval(self, process_code, form_values):
        """
        提交到钉钉进行审批
        :param process_code:审批模型编码
        :param form_values:表单参数
        :return: 审批实例id
        """
        url, token = self.env['dingding.parameter'].get_parameter_value_and_token('processinstance_create')
        user_id, dept_id = self._get_originator_user_id()
        data = {
            'process_code': process_code,  # 审批模型编码
            'originator_user_id': user_id,  # 发起人userid
            'dept_id': dept_id,             # 发起人部门id
            'form_component_values': form_values  # 表单参数
        }
        result = self.env['dingding.api.tools'].send_post_request(url, token, data, 10)
        logging.info(result)
        if result.get('errcode') == 0:
            return result.get('process_instance_id')
        else:
            raise UserError('提交审批实例失败，失败原因:{}'.format(result.get('errmsg')))

    @api.model
    def _check_oa_model(self, model_name):
        """
        检查oa模型与审批单据的关联
        :param model_name:
        :return:
        """
        model_id = self.env['ir.model'].sudo().search([('model', '=', model_name)]).id
        dac = self.env['dingding.approval.control'].search([('oa_model_id', '=', model_id)], limit=1)
        if not dac:
            raise UserError("没有对应的审批关联！请前往钉钉->审批关联中进行配置!")
        return dac.template_id.process_code

    @api.multi
    def _get_originator_user_id(self):
        """
        返回发起人钉钉id和部门id
        :return:
        """
        for res in self:
            return res.originator_user_id.ding_id, res.originator_user_id.department_id.ding_id




