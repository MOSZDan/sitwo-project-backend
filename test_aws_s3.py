"""
Script para probar la conexión con AWS S3
"""
import os
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

# Cargar variables de entorno
load_dotenv()

def test_aws_connection():
    """Probar conexión con AWS S3"""
    print("=" * 60)
    print("PROBANDO CONEXIÓN CON AWS S3")
    print("=" * 60)

    # Obtener credenciales
    aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
    bucket_name = os.environ.get('AWS_STORAGE_BUCKET_NAME')
    region = 'us-east-2'

    print(f"\n📋 Configuración:")
    print(f"   - Access Key: {aws_access_key[:10]}...")
    print(f"   - Bucket: {bucket_name}")
    print(f"   - Region: {region}")

    if not all([aws_access_key, aws_secret_key, bucket_name]):
        print("\n❌ ERROR: Faltan credenciales en el archivo .env")
        return False

    try:
        # Crear cliente S3
        print("\n🔄 Conectando con AWS S3...")
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=region
        )

        # Verificar si el bucket existe
        print(f"🔍 Verificando bucket '{bucket_name}'...")
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            print(f"✅ Bucket '{bucket_name}' existe y es accesible")

            # Listar algunos objetos
            print("\n📦 Listando objetos en el bucket...")
            response = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=5)

            if 'Contents' in response:
                print(f"   Archivos encontrados: {len(response['Contents'])}")
                for obj in response['Contents'][:5]:
                    print(f"   - {obj['Key']} ({obj['Size']} bytes)")
            else:
                print("   El bucket está vacío (esto es normal)")

            # Verificar región del bucket
            location_response = s3_client.get_bucket_location(Bucket=bucket_name)
            bucket_region = location_response['LocationConstraint']
            print(f"\n📍 Región del bucket: {bucket_region}")

            if bucket_region != region:
                print(f"⚠️  ADVERTENCIA: La región configurada ({region}) no coincide con la región del bucket ({bucket_region})")
                print(f"   Actualiza AWS_S3_REGION_NAME en settings.py a '{bucket_region}'")

            return True

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                print(f"\n❌ ERROR: El bucket '{bucket_name}' no existe")
                print("\n💡 Solución:")
                print(f"   1. Ve a https://s3.console.aws.amazon.com/s3/")
                print(f"   2. Crea un bucket llamado '{bucket_name}' en la región {region}")
                print(f"   3. O actualiza AWS_STORAGE_BUCKET_NAME en .env con un bucket existente")
            elif error_code == '403':
                print(f"\n❌ ERROR: No tienes permiso para acceder al bucket '{bucket_name}'")
                print("\n💡 Solución:")
                print("   1. Verifica que las credenciales sean correctas")
                print("   2. Verifica los permisos IAM de tu usuario")
            else:
                print(f"\n❌ ERROR al verificar bucket: {e}")
            return False

    except ClientError as e:
        print(f"\n❌ ERROR de conexión con AWS: {e}")
        print("\n💡 Verifica:")
        print("   1. Las credenciales AWS son correctas")
        print("   2. El usuario IAM tiene permisos de S3")
        print("   3. Tu conexión a internet funciona")
        return False

    except Exception as e:
        print(f"\n❌ ERROR inesperado: {e}")
        return False

def test_bucket_permissions():
    """Probar permisos de escritura en el bucket"""
    print("\n" + "=" * 60)
    print("PROBANDO PERMISOS DE ESCRITURA")
    print("=" * 60)

    aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
    bucket_name = os.environ.get('AWS_STORAGE_BUCKET_NAME')
    region = 'us-east-2'

    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=region
        )

        # Intentar subir un archivo de prueba
        test_key = 'test/connection_test.txt'
        test_content = 'Test de conexión desde Django'

        print(f"\n🔄 Intentando subir archivo de prueba '{test_key}'...")
        s3_client.put_object(
            Bucket=bucket_name,
            Key=test_key,
            Body=test_content.encode('utf-8'),
            ContentType='text/plain'
        )
        print(f"✅ Archivo subido correctamente")

        # Intentar leer el archivo
        print(f"🔄 Intentando leer el archivo...")
        response = s3_client.get_object(Bucket=bucket_name, Key=test_key)
        content = response['Body'].read().decode('utf-8')
        print(f"✅ Archivo leído correctamente: '{content}'")

        # Intentar eliminar el archivo
        print(f"🔄 Limpiando archivo de prueba...")
        s3_client.delete_object(Bucket=bucket_name, Key=test_key)
        print(f"✅ Archivo eliminado correctamente")

        print("\n🎉 ¡TODOS LOS PERMISOS FUNCIONAN CORRECTAMENTE!")
        return True

    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"\n❌ ERROR de permisos: {error_code}")
        if error_code == 'AccessDenied':
            print("\n💡 Tu usuario IAM necesita los siguientes permisos:")
            print("   - s3:PutObject (para subir archivos)")
            print("   - s3:GetObject (para leer archivos)")
            print("   - s3:DeleteObject (para eliminar archivos)")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False

if __name__ == '__main__':
    print("\n🚀 Iniciando pruebas de AWS S3...\n")

    # Test 1: Conexión básica
    connection_ok = test_aws_connection()

    if connection_ok:
        # Test 2: Permisos de escritura/lectura
        test_bucket_permissions()

    print("\n" + "=" * 60)
    print("PRUEBAS COMPLETADAS")
    print("=" * 60)