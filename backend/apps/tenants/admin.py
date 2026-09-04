from django.contrib import admin
from .models import Tenant, Membership, WorkCalendar, Contour

admin.site.register(Tenant)
admin.site.register(Membership)
admin.site.register(WorkCalendar)
admin.site.register(Contour)
