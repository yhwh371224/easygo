from django import template
register = template.Library()


@register.inclusion_tag('widgets/time_picker.html')
def time_picker(field_name, label, value='', hint=''):
    hour, minute, ampm = '', '', 'AM'
    if value:
        try:
            h, m = int(value[:2]), int(value[3:5])
            minute = m
            if h == 0:       hour, ampm = 12, 'AM'
            elif h < 12:     hour, ampm = h,  'AM'
            elif h == 12:    hour, ampm = 12, 'PM'
            else:            hour, ampm = h - 12, 'PM'
        except (ValueError, IndexError):
            pass
    return {'field_name': field_name, 'label': label,
            'hour': hour, 'minute': str(minute).zfill(2), 'ampm': ampm, 'hint': hint}
