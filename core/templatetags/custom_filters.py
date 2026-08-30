from django import template

register = template.Library()


@register.filter
def mul(value, arg):

    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def div(value, arg):

    try:
        if float(arg) == 0:
            return 0
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


@register.filter
def sub(value, arg):

    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def add_filter(value, arg):
    try:
        return float(value) + float(arg)
    except (ValueError, TypeError):
        return 0
