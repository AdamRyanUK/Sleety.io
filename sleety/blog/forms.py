from django import forms
from .models import Post, Category, Comment

choices = Category.objects.all().values_list('category_name','category_name')
choice_list = []

for item in choices: 
    choice_list.append(item)

class PostForm(forms.ModelForm):
    class Meta: 
        model = Post
        fields = ('title', 'titletag', 'header_image', 'category', 'author', 'snippet', 'body')

        widgets = {
            'title': forms.TextInput(attrs={'class':'form-control', 'placeholder':'Enter the title of the blogpost'}),
            'titletag': forms.TextInput(attrs={'class':'form-control'}),
            'category': forms.Select(choices=choice_list, attrs={'class':'form-control'}),
            'author': forms.Select(attrs={'class':'form-control'}),
            'snippet': forms.Textarea(attrs={'class':'form-control'}),
            'body': forms.Textarea(attrs={'class':'form-control'}),
        }

class EditForm(forms.ModelForm):
    class Meta: 
        model = Post
        fields = ('title', 'titletag', 'category', 'snippet', 'body')

        widgets = {
            'title': forms.TextInput(attrs={'class':'form-control', 'placeholder':'Enter the title of the blogpost'}),
            'titletag': forms.TextInput(attrs={'class':'form-control'}),
            'category': forms.Select(choices=choice_list, attrs={'class':'form-control'}),
            'snippet': forms.Textarea(attrs={'class':'form-control'}),
            'body': forms.Textarea(attrs={'class':'form-control'}),
        }

class CommentForm(forms.ModelForm):
    class Meta: 
        model = Comment
        fields = ('name', 'body')

        widgets = {
            'name': forms.TextInput(attrs={'class':'form-control', 'placeholder':'Enter your name'}),
            'body': forms.Textarea(attrs={'class':'form-control'}),
        }