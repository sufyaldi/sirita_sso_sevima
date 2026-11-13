# -*- coding: utf-8 -*-
from odoo.addons.web.controllers.home import Home
from odoo.http import request, route
from odoo.tools.translate import _lt


class SevimaHome(Home):

    @route('/web/login', type='http', auth='none', readonly=False, list_as_website_content=_lt("Login"))
    def web_login(self, *args, **kw):
        response = super().web_login(*args, **kw)
        if hasattr(response, 'qcontext') and response.qcontext is not None:
            ICP = request.env['ir.config_parameter'].sudo()
            enabled = getattr(ICP, 'get_bool', lambda k, d: ICP.get_str(k, str(d)) in ('true', 'True', '1'))('sirita_sso_sevima.enabled', True)
            response.qcontext['sevima_sso_enabled'] = enabled
        return response
