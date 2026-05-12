from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Clients, Adresses
from django.contrib.auth.forms import PasswordChangeForm
import re

class ContactForm(forms.Form):
    name = forms.CharField(max_length=100, label="Votre nom")
    email = forms.EmailField(label="Votre email")
    subject = forms.CharField(max_length=150, label="Sujet")
    message = forms.CharField(widget=forms.Textarea, label="Message")

    def clean_message(self):
        message = self.cleaned_data["message"].strip()
        if len(message) < 10:
            raise forms.ValidationError("Le message doit contenir au moins 10 caractères.")
        return message

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email")
    first_name = forms.CharField(max_length=30, required=True, label="Prénom")
    last_name = forms.CharField(max_length=30, required=True, label="Nom")
    
    num_telephone = forms.CharField(max_length=20, required=True, label="Téléphone")
    
    numero = forms.CharField(max_length=10, required=True, label="Numéro")
    rue = forms.CharField(max_length=100, required=True, label="Rue")
    ville = forms.CharField(max_length=50, required=True, label="Ville")
    province = forms.CharField(max_length=50, required=True, label="Province")
    code_postal = forms.CharField(max_length=20, required=True, label="Code postal")
    pays = forms.CharField(max_length=50, required=True, label="Pays", initial="Canada")
    boite = forms.CharField(max_length=20, required=False, label="Boîte postale")

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Nom d\'utilisateur'
        })
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Adresse email'
        })
        self.fields['first_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Prénom'
        })
        self.fields['last_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Nom de famille'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Mot de passe'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirmer le mot de passe'
        })
        self.fields['num_telephone'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Numéro de téléphone'
        })
        self.fields['numero'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'No'
        })
        self.fields['rue'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Nom de rue'
        })
        self.fields['ville'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Ville'
        })
        self.fields['province'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Province'
        })
        self.fields['code_postal'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Code postal'
        })
        self.fields['pays'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Pays'
        })
        self.fields['boite'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Boîte postale (optionnel)'
        })

    def clean_email(self):
        """Valider que l'email est unique"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Cet email est déjà utilisé.")
        return email
    
    def clean_username(self):
        """Valider le nom d'utilisateur"""
        username = self.cleaned_data.get('username')
        if len(username) < 3:
            raise forms.ValidationError("Le nom d'utilisateur doit contenir au moins 3 caractères.")
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise forms.ValidationError("Le nom d'utilisateur ne peut contenir que des lettres, chiffres et underscores.")
        return username
    
    def clean_num_telephone(self):
        """Valider le format du numéro de téléphone"""
        telephone = self.cleaned_data.get('num_telephone')
        # Supprimer les espaces, tirets, parenthèses
        telephone_clean = re.sub(r'[\s\-\(\)]', '', telephone)
        
        if not re.match(r'^\+?1?\d{10}$', telephone_clean):
            raise forms.ValidationError("Format invalide. Ex: 418-123-4567 ou 4181234567")
        return telephone
    
    def clean_code_postal(self):
        """Valider le format du code postal canadien"""
        code_postal = self.cleaned_data.get('code_postal').upper().replace(' ', '')
        
        # Format canadien: A1A 1A1 ou A1A1A1
        if not re.match(r'^[A-Z]\d[A-Z]\d[A-Z]\d$', code_postal):
            raise forms.ValidationError("Format invalide. Ex: G7H 2B1")
        
        # Reformater avec espace
        return f"{code_postal[:3]} {code_postal[3:]}"
    
    def clean_numero(self):
        """Valider le numéro de porte"""
        numero = self.cleaned_data.get('numero')
        if not numero.isdigit():
            raise forms.ValidationError("Le numéro doit être un nombre.")
        if not numero.strip():
            raise forms.ValidationError("Le numéro est requis.")
        return numero
    
    def clean_rue(self):
        """Valider le nom de rue"""
        rue = self.cleaned_data.get('rue')
        if len(rue.strip()) < 3:
            raise forms.ValidationError("Le nom de rue doit contenir au moins 3 caractères.")
        return rue.strip()
    
    def clean_ville(self):
        """Valider le nom de ville"""
        ville = self.cleaned_data.get('ville')
        if len(ville.strip()) < 2:
            raise forms.ValidationError("Le nom de ville doit contenir au moins 2 caractères.")
        return ville.strip()

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            nouvelle_adresse = Adresses.objects.create(
                numero=self.cleaned_data['numero'],
                rue=self.cleaned_data['rue'],
                ville=self.cleaned_data['ville'],
                province=self.cleaned_data['province'],
                code_postal=self.cleaned_data['code_postal'],
                pays=self.cleaned_data['pays'],
                boite=self.cleaned_data.get('boite', '')
            )
            
            nouveau_client = Clients.objects.create(
                utilisateur=user, 
                adresse=nouvelle_adresse,
                num_telephone=self.cleaned_data['num_telephone'],
                est_admin=False
            )
        
        return user
    
class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nom d''utilisateur'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mot de passe'
        })
    )

class ProfileUpdateForm(forms.ModelForm):
    """Formulaire pour modifier les informations de l'utilisateur"""
    first_name = forms.CharField(max_length=30, required=True, label="Prénom")
    last_name = forms.CharField(max_length=30, required=True, label="Nom")
    email = forms.EmailField(required=True, label="Email")
    num_telephone = forms.CharField(max_length=20, required=True, label="Téléphone")
    
    # Champs d'adresse
    numero = forms.CharField(max_length=10, required=True, label="Numéro")
    rue = forms.CharField(max_length=100, required=True, label="Rue")
    ville = forms.CharField(max_length=50, required=True, label="Ville")
    province = forms.CharField(max_length=50, required=True, label="Province")
    code_postal = forms.CharField(max_length=20, required=True, label="Code postal")
    pays = forms.CharField(max_length=50, required=True, label="Pays")
    boite = forms.CharField(max_length=20, required=False, label="Boîte postale")

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Pré-remplir les champs avec les données existantes
        if self.instance and hasattr(self.instance, 'clients'):
            client = self.instance.clients
            self.fields['num_telephone'].initial = client.num_telephone
            
            if client.adresse:
                adresse = client.adresse
                self.fields['numero'].initial = adresse.numero
                self.fields['rue'].initial = adresse.rue
                self.fields['ville'].initial = adresse.ville
                self.fields['province'].initial = adresse.province
                self.fields['code_postal'].initial = adresse.code_postal
                self.fields['pays'].initial = adresse.pays
                self.fields['boite'].initial = adresse.boite
        
        # Ajouter des classes CSS
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

    def save(self, commit=True):
        user = super().save(commit=False)
        
        if commit:
            user.save()
            
            # Mettre à jour le client
            if hasattr(user, 'clients'):
                client = user.clients
                client.num_telephone = self.cleaned_data['num_telephone']
                client.save()
                
                # Mettre à jour l'adresse
                if client.adresse:
                    adresse = client.adresse
                    adresse.numero = self.cleaned_data['numero']
                    adresse.rue = self.cleaned_data['rue']
                    adresse.ville = self.cleaned_data['ville']
                    adresse.province = self.cleaned_data['province']
                    adresse.code_postal = self.cleaned_data['code_postal']
                    adresse.pays = self.cleaned_data['pays']
                    adresse.boite = self.cleaned_data.get('boite', '')
                    adresse.save()
                else:
                    # Créer une nouvelle adresse si elle n'existe pas
                    nouvelle_adresse = Adresses.objects.create(
                        numero=self.cleaned_data['numero'],
                        rue=self.cleaned_data['rue'],
                        ville=self.cleaned_data['ville'],
                        province=self.cleaned_data['province'],
                        code_postal=self.cleaned_data['code_postal'],
                        pays=self.cleaned_data['pays'],
                        boite=self.cleaned_data.get('boite', '')
                    )
                    client.adresse = nouvelle_adresse
                    client.save()
        
        return user
    
class MyPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        label="Ancien mot de passe",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Ancien mot de passe"
        })
    )

    new_password1 = forms.CharField(
        label="Nouveau mot de passe",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Nouveau mot de passe"
        })
    )

    new_password2 = forms.CharField(
        label="Confirmer",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Confirmer le nouveau"
        })
    )