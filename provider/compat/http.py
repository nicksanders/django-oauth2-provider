# -*- coding: utf-8 -*-

import json

try:
    from django.http import JsonResponse
except ImportError:
    from django.http import HttpResponse
    def JsonResponse(response_data, *args, **kwargs):
        return HttpResponse(json.dumps(response_data), *args, content_type='application/json', **kwargs)
