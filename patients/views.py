# patients/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Patient, MedicalProfile, Antecedent, Treatment, LabResult
from .forms import CustomUserForm, PatientForm, MedicalProfileForm, AntecedentForm, TreatmentForm


def complete_patient_profile(request):
    user = request.user
    if not user.is_authenticated:
        return redirect('user_login')
    if Patient.objects.filter(user=user).exists():
        return redirect('patients:dashboard')

    if request.method == 'POST':
        user_form    = CustomUserForm(request.POST, request.FILES, instance=user)
        patient_form = PatientForm(request.POST)
        if user_form.is_valid() and patient_form.is_valid():
            user_form.save()
            patient      = patient_form.save(commit=False)
            patient.user = user
            patient.save()
            MedicalProfile.objects.create(patient=patient)
            return redirect('patients:dashboard')
    else:
        user_form    = CustomUserForm(instance=user)
        patient_form = PatientForm()

    return render(request, 'patients/complete_profile.html', {
        'user_form': user_form,
        'patient_form': patient_form,
    })


@login_required
def dashboard(request):
    if not Patient.objects.filter(user=request.user).exists():
        return redirect('patients:complete_patient_profile')

    patient  = Patient.objects.get(user=request.user)
    profile, _ = MedicalProfile.objects.get_or_create(patient=patient)

    treatments         = patient.treatments.filter(is_active=True)[:3]
    recent_lab_results = patient.lab_results.order_by('-date')[:2]
    antecedents_count  = patient.antecedents.count()
    lab_results_count  = patient.lab_results.count()
    upcoming_appointments = []
    notifications_count   = 0

    return render(request, 'patients/dashboard.html', {
        'patient':              patient,
        'profile':              profile,
        'treatments':           treatments,
        'recent_lab_results':   recent_lab_results,
        'antecedents_count':    antecedents_count,
        'lab_results_count':    lab_results_count,
        'notifications_count':  notifications_count,
        'upcoming_appointments': upcoming_appointments,
    })


@login_required
def medical_profile(request):
    patient        = get_object_or_404(Patient, user=request.user)
    profile, _     = MedicalProfile.objects.get_or_create(patient=patient)
    antecedents    = patient.antecedents.all()
    treatments     = patient.treatments.filter(is_active=True)
    lab_results    = patient.lab_results.order_by('-date')
    analyses       = patient.symptom_analyses.order_by('-analysis_date')

    return render(request, 'patients/medical_profile.html', {
        'patient':     patient,
        'profile':     profile,
        'antecedents': antecedents,
        'treatments':  treatments,
        'lab_results': lab_results,
        'analyses':    analyses,
    })


@login_required
def edit_medical_profile(request):
    patient    = get_object_or_404(Patient, user=request.user)
    profile, _ = MedicalProfile.objects.get_or_create(patient=patient)
    if request.method == 'POST':
        form = MedicalProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Medical profile updated.')
            return redirect('patients:medical_profile')
    else:
        form = MedicalProfileForm(instance=profile)
    return render(request, 'patients/edit_medical_profile.html', {'form': form})


@login_required
def add_antecedent(request):
    patient = get_object_or_404(Patient, user=request.user)
    if request.method == 'POST':
        form = AntecedentForm(request.POST)
        if form.is_valid():
            ant         = form.save(commit=False)
            ant.patient = patient
            ant.save()
            messages.success(request, 'Antecedent added.')
            return redirect('patients:medical_profile')
    else:
        form = AntecedentForm()
    return render(request, 'patients/add_antecedent.html', {'form': form})


@login_required
def add_treatment(request):
    patient = get_object_or_404(Patient, user=request.user)
    if request.method == 'POST':
        form = TreatmentForm(request.POST)
        if form.is_valid():
            t         = form.save(commit=False)
            t.patient = patient
            t.save()
            messages.success(request, 'Treatment added.')
            return redirect('patients:medical_profile')
    else:
        form = TreatmentForm()
    return render(request, 'patients/add_treatment.html', {'form': form})


@login_required
def profile(request):
    patient = get_object_or_404(Patient, user=request.user)
    return render(request, 'patients/profile.html', {'patient': patient})


@login_required
def edit_profile(request):
    patient = get_object_or_404(Patient, user=request.user)
    if request.method == 'POST':
        form = PatientForm(request.POST, request.FILES, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('patients:profile')
    else:
        form = PatientForm(instance=patient)
    return render(request, 'patients/edit_profile.html', {'form': form})