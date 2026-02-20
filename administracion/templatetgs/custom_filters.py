from django import template
register = template.Library()

@register.filter
def pluck(queryset, key):
    return [item[key] for item in queryset]
