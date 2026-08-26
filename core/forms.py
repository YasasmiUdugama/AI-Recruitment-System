
from django import forms
from .models import JobDescription, Candidate


class JobForm(forms.ModelForm):
    """Form for creating jobs (status auto-set to active)"""
    class Meta:
        model = JobDescription
        fields = [
            'title', 'description', 'required_skills',
            'experience_required', 'education_required',
            'department', 'location'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'required_skills': forms.Textarea(attrs={'rows': 3, 'placeholder': 'e.g., Python, SQL, Machine Learning (comma-separated)'}),
        }


class JobEditForm(forms.ModelForm):
    """Form for editing jobs (includes status)"""
    class Meta:
        model = JobDescription
        fields = [
            'title', 'description', 'required_skills',
            'experience_required', 'education_required',
            'department', 'location', 'status'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'required_skills': forms.Textarea(attrs={'rows': 3}),
        }


class SingleUploadForm(forms.Form):
    """Form for a single candidate CV upload"""
    job_id = forms.ModelChoiceField(
        queryset=JobDescription.objects.filter(status='active'),
        label="Select Job Position",
        required=True,
        empty_label="Select a job...",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    cv_file = forms.FileField(
        label="Upload CV",
        required=True,
        widget=forms.ClearableFileInput(attrs={
            'accept': '.pdf,.docx,.doc,.txt',
            'class': 'form-control',
        })
    )
    phone = forms.CharField(
        label="Phone (optional)",
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    def clean_cv_file(self):
        f = self.cleaned_data.get('cv_file')
        allowed_extensions = ['.pdf', '.docx', '.doc', '.txt']
        name_lower = f.name.lower()
        if not any(name_lower.endswith(ext) for ext in allowed_extensions):
            raise forms.ValidationError("Unsupported file format. Use PDF, DOCX, DOC, or TXT.")
        if f.size > 10 * 1024 * 1024:
            raise forms.ValidationError("File exceeds 10MB limit.")
        return f


class MultipleFileInput(forms.ClearableFileInput):
    """Custom widget to allow multiple file selection"""
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """Custom field that handles multiple file uploads"""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class BulkUploadForm(forms.Form):
    """Form for bulk CV upload with auto-parsing"""
    job_id = forms.ModelChoiceField(
        queryset=JobDescription.objects.filter(status='active'),
        label="Select Job Position",
        required=True,
        empty_label="Select a job...",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    cv_files = MultipleFileField(
        label="Upload CV Files",
        required=True,
        widget=MultipleFileInput(attrs={
            'accept': '.pdf,.docx,.doc,.txt',
            'class': 'form-control',
            'multiple': True,
        })
    )
    threshold = forms.FloatField(
        label="Shortlist threshold",
        required=False,
        initial=0.01,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '1'})
    )
    top_n = forms.IntegerField(
        label="Top N to shortlist",
        required=False,
        initial=10,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1'})
    )

    def clean_cv_files(self):
        files = self.cleaned_data.get('cv_files', [])
        if not files:
            raise forms.ValidationError("Please select at least one file.")
        if len(files) > 50:
            raise forms.ValidationError("You can upload a maximum of 50 files at once.")

        allowed_extensions = ['.pdf', '.docx', '.doc', '.txt']
        for f in files:
            name_lower = f.name.lower()
            if not any(name_lower.endswith(ext) for ext in allowed_extensions):
                raise forms.ValidationError(f"File '{f.name}' is not a supported format. Use PDF, DOCX, DOC, or TXT.")
            if f.size > 10 * 1024 * 1024:
                raise forms.ValidationError(f"File '{f.name}' exceeds 10MB limit.")

        return files


class CandidateEditForm(forms.ModelForm):
    """Form for editing candidate basic details"""
    class Meta:
        model = Candidate
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
        }
