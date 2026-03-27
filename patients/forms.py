# patients/forms.py
from django import forms
from .models import Patient, MedicalProfile, Antecedent, Treatment ,CustomUser


class PatientCompleteProfileForm(forms.ModelForm):
    class Meta:
        model  = CustomUser
        fields = ['sex', 'date_of_birth', 'phone', 'id_card_number',
                  'id_card_photo', 'address', 'postal_code', 'city',
                  'wilaya']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }
        
        class Meta:
            model = Patient
            fields = ['blood_group', 'emergency_contact','access_level']
     
     

class MedicalProfileForm(forms.ModelForm):
    allergies    = forms.CharField(required=False,
                     help_text='Comma separated: Penicillin, Pollen',
                     widget=forms.TextInput(attrs={'placeholder': 'Penicillin, Pollen'}))
    vaccinations = forms.CharField(required=False,
                     help_text='Comma separated',
                     widget=forms.TextInput(attrs={'placeholder': 'COVID-19, Flu'}))

    class Meta:
        model  = MedicalProfile
        fields = ['allergies', 'vaccinations']

    def clean_allergies(self):
        val = self.cleaned_data.get('allergies', '')
        return [a.strip() for a in val.split(',') if a.strip()]

    def clean_vaccinations(self):
        val = self.cleaned_data.get('vaccinations', '')
        return [v.strip() for v in val.split(',') if v.strip()]


class AntecedentForm(forms.ModelForm):
    class Meta:
        model  = Antecedent
        fields = ['name', 'diagnosed_year', 'status', 'icon']
        widgets = {
            'diagnosed_year': forms.NumberInput(attrs={'placeholder': '2018'}),
            'icon':           forms.TextInput(attrs={'placeholder': '🫀'}),
        }


class TreatmentForm(forms.ModelForm):
    class Meta:
        model  = Treatment
        fields = ['name', 'dosage', 'frequency', 'start_date', 'end_date', 'is_active']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date':   forms.DateInput(attrs={'type': 'date'}),
        }