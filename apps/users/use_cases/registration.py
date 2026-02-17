from apps.users.models.user import User

class RegisterUserUseCase:
    def __init__(self, email, password, first_name, last_name, phone=None, consent_data_processing=False):
        self.email = email
        self.password = password
        self.first_name = first_name
        self.last_name = last_name
        self.phone = phone
        self.consent_data_processing = consent_data_processing

    def execute(self) -> User:
        user = User.objects.create_user(
            email=self.email,
            password=self.password,
            first_name=self.first_name,
            last_name=self.last_name,
            phone=self.phone,
            consent_data_processing=self.consent_data_processing,
        )
        return user
