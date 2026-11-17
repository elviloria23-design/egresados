"""Despublica oportunidades cuya vigencia ya finalizó."""

from django.core.management.base import BaseCommand
from django.utils import timezone

from app_oportunidades.models import Oportunidad


class Command(BaseCommand):
    """Comando para ejecutar diariamente desde el planificador del servidor."""

    help = 'Despublica oportunidades vencidas.'

    def handle(self, *args, **options):
        """Despublica las ofertas vencidas e informa el total."""

        updated = Oportunidad.objects.filter(
            publicada=True,
            vigente_hasta__lt=timezone.localdate(),
        ).update(publicada=False)
        self.stdout.write(
            self.style.SUCCESS(f'Oportunidades despublicadas: {updated}')
        )
