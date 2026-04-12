# doctors/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Doctor, Doctor_professionel_info, Exercice
from .forms import DoctorCompleteProfileForm, Doctor_professionel_infoForm, ExerciceForm


def complete_doctor_profile(request):
    user = request.user
    if not user.is_authenticated:
        return redirect('user_login')
    if Doctor.objects.filter(user=user).exists():
        return redirect('doctors:dashboard')

    if request.method == 'POST':
        form          = DoctorCompleteProfileForm(request.POST, request.FILES)
        pro_form      = Doctor_professionel_infoForm(request.POST, request.FILES)
        exercice_form = ExerciceForm(request.POST)

        if form.is_valid() and pro_form.is_valid() and exercice_form.is_valid():
            doctor = form.save(commit=False)
            doctor.user = user
            doctor.save()
            pro = pro_form.save(commit=False)
            pro.doctor = doctor
            pro.save()
            exercice = exercice_form.save(commit=False)
            exercice.doctor = doctor
            exercice.save()
            return redirect('doctors:dashboard')
    else:
        form          = DoctorCompleteProfileForm()
        pro_form      = Doctor_professionel_infoForm()
        exercice_form = ExerciceForm()

    return render(request, 'doctors/complete_doctor_profile.html', {
        'form': form,
        'pro_form': pro_form,
        'exercice_form': exercice_form,
    })

@login_required
def dashboard(request):
    # if no doctor profile yet → redirect to complete it
    if not Doctor.objects.filter(user=request.user).exists():
        return redirect('doctors:doctor_complete_profile')

    doctor = Doctor.objects.get(user=request.user)
    return render(request, 'doctors/doctor_dashboard.html', {'doctor': doctor})


