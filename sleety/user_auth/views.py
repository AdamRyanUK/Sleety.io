from typing import Any
from django.db import models
from django.shortcuts import render
from django.views import generic 
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.urls import reverse_lazy
from django.contrib.auth.models import User
from django import forms

class UserRegisterView(generic.CreateView):
    form_class = UserCreationForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('login')

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

        widgets = {
            'username' : forms.TextInput(attrs={'class': 'form-control'}),
            'first_name' : forms.TextInput(attrs={'class': 'form-control'}),
            'last_name' : forms.TextInput(attrs={'class': 'form-control'}),
            'email' : forms.TextInput(attrs={'class': 'form-control'}),
        }

class UserEditView(generic.UpdateView):
    form_class = CustomUserChangeForm
    template_name = 'registration/edit_profile.html'
    success_url = reverse_lazy('blog')

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        # You can add additional logic here if needed
        return super().form_valid(form)

