from django import forms

class MessageForm(forms.Form):
    """
    نموذج لإدخال الرسائل النصية التي سيتم إرسالها إلى Kafka
    """
    message = forms.CharField(
        label='الرسالة',
        max_length=1000,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'أدخل رسالتك هنا...'
        })
    )

    def clean_message(self):
        """
        التحقق من صحة الرسالة
        """
        message = self.cleaned_data.get('message')
        if not message or message.strip() == '':
            raise forms.ValidationError('الرجاء إدخال رسالة صالحة')
        return message

class FileForm(forms.Form):
    """
    نموذج لرفع الملفات التي سيتم إرسالها إلى Kafka
    """
    file = forms.FileField(
        label='الملف',
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': '*/*',  # قبول جميع أنواع الملفات
        })
    )

    description = forms.CharField(
        label='وصف الملف',
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'أدخل وصفاً اختيارياً للملف...'
        })
    )

    def clean_file(self):
        """
        التحقق من الملف
        """
        file = self.cleaned_data.get('file')
        if not file:
            raise forms.ValidationError('الرجاء اختيار ملف')

        # التحقق من حجم الملف (الحد الأقصى 10 ميجابايت)
        if file.size > 10 * 1024 * 1024:  # 10 MB
            raise forms.ValidationError('حجم الملف كبير جداً. يجب أن يكون أقل من 10 ميجابايت')

        return file
