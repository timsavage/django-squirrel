# -*- coding: utf-8 -*-
import django.dispatch

# Signal raised when a operation that causes cache to be invalidated is raised.
invalidate_cache = django.dispatch.Signal(providing_args=['instance'])
