from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, label='Электронная почта')
    first_name = forms.CharField(required=True, label='Имя')
    last_name = forms.CharField(required=True, label='Фамилия')
    middle_name = forms.CharField(required=True, label='Отчество')
    birth_date = forms.DateField(required=True, label='Дата рождения', widget=forms.DateInput(attrs={'type': 'date'}))
    phone = forms.CharField(required=True, label='Номер телефона')
    city = forms.CharField(required=True, label='Город')
    gender = forms.ChoiceField(required=True, label='Пол', choices=[('M', 'Мужской'), ('F', 'Женский')])
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'middle_name',
                  'birth_date', 'phone', 'city', 'gender', 'password1', 'password2']
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Пользователь с такой почтой уже существует.')
        return email
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if User.objects.filter(phone=phone).exists():
            raise forms.ValidationError('Пользователь с таким телефоном уже существует.')
        return phone
    
    def clean(self):
        cleaned_data = super().clean()
        first = cleaned_data.get('first_name')
        last = cleaned_data.get('last_name')
        middle = cleaned_data.get('middle_name')
        birth = cleaned_data.get('birth_date')
        
        if first and last and middle and birth:
            if User.objects.filter(first_name=first, last_name=last, middle_name=middle, birth_date=birth).exists():
                raise forms.ValidationError('Пользователь с таким ФИО и датой рождения уже зарегистрирован.')
        return cleaned_data


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label='Логин или Email', widget=forms.TextInput(attrs={'placeholder': 'Введите логин или почту'}))
    
    class Meta:
        model = User
        fields = ['username', 'password']


class ProfileEditForm(forms.ModelForm):
    height = forms.IntegerField(required=False, label='Рост (см)', min_value=130, max_value=230,
                                widget=forms.NumberInput(attrs={'placeholder': 'От 130 до 230'}))
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'middle_name', 'email',
                  'phone', 'city', 'avatar', 'bio', 'height',
                  'vk_link', 'tg_link', 'tg_channel', 'max_link', 'gender']
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
        }