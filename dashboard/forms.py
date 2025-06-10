from django import forms
from datatable import models as datatables
from cbs import models as cbsmodel
from accounts.models import CustomUser
from django import forms
from phonenumber_field.formfields import PhoneNumberField


class AddQuestionForm(forms.ModelForm):
    class Meta:
        model = datatables.SecurityQuestion
        fields = ["question"]


class AddTransactionPurposeForm(forms.ModelForm):
    class Meta:
        model = datatables.TransactionPurpose
        fields = ["name"]


class AddOccupationForm(forms.ModelForm):
    class Meta:
        model = datatables.Occupation
        fields = ["name"]


class AddBankBranchForm(forms.ModelForm):
    class Meta:
        model = datatables.BankBranch
        fields = (
            "name",
            "country",
            "langtitude_cordinates",
            "longitude_cordinates",
            "address",
            "closed",
        )


class AddAtmLocation(forms.ModelForm):
    class Meta:
        model = datatables.Atm
        fields = (
            "country",
            "langtitude_cordinates",
            "longitude_cordinates",
            "address",
        )


class AccountDeactivationForm(forms.Form):
    reason = forms.CharField(max_length=255, widget=forms.Textarea())
    password = forms.CharField(max_length=255, widget=forms.PasswordInput())

    def __init__(self, *args, **kwargs):
        super(AccountDeactivationForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs["class"] = "form-control"
            visible.field.required = True


class CustomerPasswordResetForm(forms.Form):
    pin = forms.CharField(max_length=100)
    new_password = forms.CharField(max_length=255, widget=forms.PasswordInput())


class CustomerPINResetForm(forms.Form):
    password = forms.CharField(max_length=100, widget=forms.PasswordInput())
    new_pin = forms.CharField(max_length=100, widget=forms.PasswordInput())


class EditTransferForm(forms.ModelForm):
    class Meta:
        model = cbsmodel.Transfer
        fields = (
            "status",
            "t24_reference",
        )


class CorporateUserForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = (
            "first_name",
            "last_name",
            "phone_number",
            "email",
        )


class ChangeBankStatementStatus(forms.ModelForm):
    class Meta:
        model = cbsmodel.BankStatement
        fields = ("status", "comments")

    def __init__(self, *args, **kwargs):
        super(ChangeBankStatementStatus, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs["class"] = "form-control"
            visible.field.required = True


class ChangeLoanrequestStatus(forms.ModelForm):
    class Meta:
        model = cbsmodel.LoanRequest
        fields = ("application_id", "status", "comments")

    def __init__(self, *args, **kwargs):
        super(ChangeLoanrequestStatus, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs["class"] = "form-control"
            if visible.name != "application_id":
                visible.field.required = True


class ChangeTransferRequestStatus(forms.ModelForm):
    class Meta:
        model = cbsmodel.Transfer
        fields = ("t24_reference", "status", "failed_reason")

    def __init__(self, *args, **kwargs):
        super(ChangeTransferRequestStatus, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs["class"] = "form-control"
            if visible.name != "t24_reference" and visible.name != "failed_reason":
                visible.field.required = True


class ChequeRequestStatusChange(forms.ModelForm):
    class Meta:
        model = cbsmodel.ChequeRequest
        fields = ("status", "comments")

    def __init__(self, *args, **kwargs):
        super(ChequeRequestStatusChange, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs["class"] = "form-control"
            visible.field.required = True


class CardRequestStatusChange(forms.ModelForm):
    class Meta:
        model = cbsmodel.CardRequest
        fields = ("status", "comments")

    def __init__(self, *args, **kwargs):
        super(CardRequestStatusChange, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs["class"] = "form-control"
            visible.field.required = True


class NewCustomerVerifyPhoneForm(forms.Form):
    phone_number = PhoneNumberField()


class NewCustomerVerifyEmailForm(forms.Form):
    email = forms.EmailField(label="Email")
