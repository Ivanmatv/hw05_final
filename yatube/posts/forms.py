from django import forms

from .models import Post, Comment


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('text', 'group', 'image')
        lable = {
            'Названия'
            'text': 'Текст поста',
            'group': 'Группа',
        }
        help_texts = {
            'Текс подсказки'
            'group': 'Выберите группу',
            'text': 'Введите сообщение',
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
        lable = {
            'Комментарий'
            'text': 'Текст коменнтария',
        }
        help_text = {
            'Текст подсказки комментария'
            'text': 'Введите комментарий',
        }
