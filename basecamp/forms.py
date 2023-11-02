from django import forms
from blog.models import Inquiry


class InquiryForm(forms.ModelForm):
    class Meta:
        model = Inquiry
        fields = {'name', 'contact', 'email', 'flight_date', 'flight_number', 'flight_time', 'pickup_time',
                  'direction', 'suburb', 'street', 'no_of_passenger', 'no_of_baggage', 'return_direction',
                  'return_flight_date', 'return_flight_number', 'return_flight_time', 'return_pickup_time',
                  'message'} 
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'John Doe'}),
            'contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your mobile phone number'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'j.doe@example.com'}),
            'flight_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'flight_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your flight number'}),
            'flight_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'pickup_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'direction': forms.Select(attrs={'class': 'form-select'}),
            'suburb': forms.Select(attrs={'class': 'form-select'}),
            'street': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Street No and Street Name'}),
            'no_of_passenger': forms.TextInput(attrs={'class': 'form-control'}),
            'no_of_baggage': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'How many baggage?'}),
            'return_direction': forms.TextInput(attrs={'class': 'form-control'}),
            'return_flight_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'return_flight_number': forms.TextInput(attrs={'class': 'form-control'}),
            'return_flight_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'return_pickup_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Write your message here'}),
        }



