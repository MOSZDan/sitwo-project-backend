import hashlib
import io
from datetime import datetime
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from PIL import Image
import base64


def generar_pdf_consentimiento(consentimiento):
    """
    Genera un PDF del consentimiento con los datos del paciente, 
    el contenido del consentimiento y la firma digital
    """
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Título
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 50, f"Consentimiento Informado: {consentimiento.titulo}")

    # Datos del paciente
    p.setFont("Helvetica", 12)
    y_position = height - 100
    p.drawString(50, y_position, f"Paciente: {consentimiento.paciente.codusuario.nombre} {consentimiento.paciente.codusuario.apellido}")
    y_position -= 20
    p.drawString(50, y_position, f"Fecha de creación: {consentimiento.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S')}")
    y_position -= 20
    p.drawString(50, y_position, f"IP de creación: {consentimiento.ip_creacion}")
    y_position -= 40

    # Contenido del consentimiento
    p.setFont("Helvetica", 12)
    p.drawString(50, y_position, "Contenido del consentimiento:")
    y_position -= 20

    # Dividir el contenido en líneas para el PDF
    contenido = consentimiento.texto_contenido
    line_height = 14
    max_line_width = 60  # Aproximadamente 60 caracteres por línea
    
    lines = []
    current_line = ""
    
    for word in contenido.split():
        if len(current_line + word) <= max_line_width:
            current_line += word + " "
        else:
            lines.append(current_line)
            current_line = word + " "
    
    if current_line:
        lines.append(current_line)

    # Dibujar el contenido
    for line in lines:
        if y_position < 150:  # Si nos estamos quedando sin espacio, crear nueva página
            p.showPage()
            y_position = height - 50
        
        p.drawString(50, y_position, line)
        y_position -= line_height

    y_position -= 30  # Espacio antes de la firma

    # Dibujar la firma si existe
    if consentimiento.firma_base64:
        # Decodificar la imagen de la firma desde base64
        try:
            signature_data = base64.b64decode(consentimiento.firma_base64.split(',')[1] if ',' in consentimiento.firma_base64 else consentimiento.firma_base64)
            signature_image = Image.open(io.BytesIO(signature_data))
            
            # Convertir la imagen a RGBA si no lo es para manejar la transparencia
            if signature_image.mode != 'RGBA':
                signature_image = signature_image.convert('RGBA')
            
            # Crear una nueva imagen con fondo blanco para asegurar visibilidad
            background = Image.new('RGBA', signature_image.size, (255, 255, 255, 255))
            # Pegar la firma sobre el fondo blanco
            background.paste(signature_image, (0, 0), signature_image)
            # Convertir a RGB para evitar problemas con reportlab
            signature_image = background.convert('RGB')
            
            # Aumentar la calidad de la imagen si es pequeña
            width, height = signature_image.size
            if width < 300 or height < 100:
                # Ampliar la imagen manteniendo proporciones
                new_width = max(300, width * 2)
                new_height = max(100, height * 2)
                signature_image = signature_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Guardar temporalmente la imagen para reportlab
            signature_io = io.BytesIO()
            signature_image.save(signature_io, format='PNG')
            signature_io.seek(0)
            
            # Dibujar la firma en el PDF
            p.drawString(50, y_position, "Firma del paciente:")
            y_position -= 20
            
            p.drawImage(ImageReader(signature_io), 50, y_position - 100, width=200, height=100)
            y_position -= 120
        except Exception as e:
            print(f"Error al procesar la firma: {e}")
            p.drawString(50, y_position, "Firma del paciente: [No disponible]")
            y_position -= 20

    # Agregar información de sellado si está disponible
    # Verificar explícitamente si los campos existen y no son None
    if getattr(consentimiento, 'fecha_hora_sello', None):
        y_position -= 20
        p.drawString(50, y_position, f"Fecha y hora del sello digital: {consentimiento.fecha_hora_sello}")
        y_position -= 20
        
        hash_documento = getattr(consentimiento, 'hash_documento', None)
        if hash_documento:
            p.drawString(50, y_position, f"Hash del documento: {hash_documento}")
        y_position -= 20
        
        validado_por = getattr(consentimiento, 'validado_por', None)
        if validado_por:
            p.drawString(50, y_position, f"Validado por: {validado_por.nombre} {validado_por.apellido}")
            y_position -= 20
            
            fecha_validacion = getattr(consentimiento, 'fecha_validacion', None)
            if fecha_validacion:
                p.drawString(50, y_position, f"Fecha de validación: {fecha_validacion}")


    p.showPage()
    p.save()

    # Obtener el valor del buffer
    pdf_value = buffer.getvalue()
    buffer.close()
    
    return pdf_value


def calcular_hash_documento(documento_bytes):
    """
    Calcula el hash SHA-256 del documento
    """
    sha256_hash = hashlib.sha256()
    sha256_hash.update(documento_bytes)
    return sha256_hash.hexdigest()


def sellar_documento_consentimiento(consentimiento):
    """
    Genera el PDF, calcula el hash, y actualiza los campos de sellado
    """
    # Establecer los campos de sellado temporalmente para que se incluyan en el PDF
    fecha_sello_temp = datetime.now()
    hash_temp = None  # Calcularemos este valor después de generar el PDF inicial
    
    # Guardamos temporalmente los valores actuales para poder restaurarlos si es necesario
    fecha_hora_sello_original = getattr(consentimiento, 'fecha_hora_sello', None)
    hash_documento_original = getattr(consentimiento, 'hash_documento', None)
    
    # Establecer los campos de sellado en el objeto
    consentimiento.fecha_hora_sello = fecha_sello_temp
    
    # Generar el PDF inicial del consentimiento con la información de sellado
    pdf_bytes = generar_pdf_consentimiento(consentimiento)
    
    # Calcular el hash del PDF generado
    hash_documento = calcular_hash_documento(pdf_bytes)
    
    # Actualizar el objeto con el hash calculado
    consentimiento.hash_documento = hash_documento
    
    # Regenerar el PDF final con el hash incluido
    pdf_final = generar_pdf_consentimiento(consentimiento)
    
    # Actualizar el consentimiento con los datos finales de sellado
    consentimiento.pdf_firmado = pdf_final
    consentimiento.hash_documento = hash_documento
    consentimiento.fecha_hora_sello = fecha_sello_temp
    
    # Guardar los cambios
    consentimiento.save()
    
    return consentimiento