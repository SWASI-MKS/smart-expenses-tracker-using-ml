from django.apps import AppConfig


class BankSimulatorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bank_simulator'

    def ready(self):
        import bank_simulator.signals
