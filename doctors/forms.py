from django import forms
from .models import Doctor , Doctor_professionel_info , Exercice ,CustomUser

class DoctorCompleteProfileForm(forms.ModelForm):
    class Meta:
        model  = CustomUser
        fields = ['sex', 'date_of_birth', 'phone', 'id_card_number',
                  'id_card_photo', 'address', 'postal_code', 'city',
                  'wilaya']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }

class Doctor_professionel_infoForm(forms.ModelForm):
    class Meta: 
        model  = Doctor_professionel_info   
        fields = ['doctor_professional_phone', 'doctor_diplome', 'doctor_experience_years', 'doctor_medical_speciality','doctor_num_denregistration_au_conseil_de_ordre', 'doctor_license_number', 'doctor_authorisation_exercer', 'doctor_convention_cnas']   

class ExerciceForm(forms.ModelForm):
    class Meta:                     
        model  = Exercice   
        fields = ['type_etablissement', 'nom_etablissement', 'adresse_etablissement', 'doctor_exercer_hours']
                
                 