from django.core.management.base import BaseCommand
from api.models import Consentimiento, Usuario
from api.utils_consentimiento import sellar_documento_consentimiento


class Command(BaseCommand):
    help = 'Probar funcionalidad de sellado digital de consentimientos'

    def handle(self, *args, **options):
        # Buscar un consentimiento de prueba
        consentimientos = Consentimiento.objects.all()[:3]
        
        if not consentimientos:
            self.stdout.write(
                self.style.WARNING('No se encontraron consentimientos para probar')
            )
            return
            
        self.stdout.write(
            self.style.SUCCESS(f'Se encontraron {len(consentimientos)} consentimientos para probar')
        )
        
        for consentimiento in consentimientos:
            self.stdout.write(f'\nProcesando consentimiento ID: {consentimiento.id}')
            self.stdout.write(f'  - Paciente: {consentimiento.paciente.codusuario.nombre} {consentimiento.paciente.codusuario.apellido}')
            self.stdout.write(f'  - Titulo: {consentimiento.titulo}')
            self.stdout.write(f'  - Fecha creacion: {consentimiento.fecha_creacion}')
            
            # Probar el sellado digital
            try:
                consentimiento_actualizado = sellar_documento_consentimiento(consentimiento)
                
                self.stdout.write(
                    self.style.SUCCESS(f'  [OK] Consentimiento sellado exitosamente')
                )
                self.stdout.write(f'    - Hash: {consentimiento_actualizado.hash_documento[:20]}...')
                self.stdout.write(f'    - Fecha sello: {consentimiento_actualizado.fecha_hora_sello}')
                
                # Verificar que el PDF se haya generado
                if consentimiento_actualizado.pdf_firmado:
                    self.stdout.write(
                        self.style.SUCCESS(f'    [OK] PDF generado correctamente ({len(consentimiento_actualizado.pdf_firmado)} bytes)')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f'    [ERROR] No se genero el PDF')
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  [ERROR] Error al sellar consentimiento: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS('\nPrueba completada. Todos los consentimientos han sido procesados.')
        )