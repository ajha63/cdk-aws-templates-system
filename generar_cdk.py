#!/usr/bin/env python3
"""
Script para generar código CDK desde una configuración YAML.
Uso: python generar_cdk.py [archivo_config.yaml] [environment]
"""

import sys
import os
from pathlib import Path

# Agregar el directorio actual al path
sys.path.insert(0, str(Path(__file__).parent))

from cdk_templates.config_loader import ConfigurationLoader
from cdk_templates.template_generator import TemplateGenerator


def main():
    # Configuración por defecto
    config_file = 'examples/ejemplo-basico.yaml'
    environment = 'dev'
    output_dir = 'cdk-output'
    
    # Permitir argumentos de línea de comandos
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    if len(sys.argv) > 2:
        environment = sys.argv[2]
    if len(sys.argv) > 3:
        output_dir = sys.argv[3]
    
    print("=" * 60)
    print("  Generador de Código CDK")
    print("=" * 60)
    print(f"\n📄 Archivo de configuración: {config_file}")
    print(f"🌍 Entorno: {environment}")
    print(f"📁 Directorio de salida: {output_dir}\n")
    
    # Verificar que el archivo existe
    if not os.path.exists(config_file):
        print(f"❌ Error: El archivo '{config_file}' no existe")
        print("\nArchivos disponibles en examples/:")
        if os.path.exists('examples'):
            for f in os.listdir('examples'):
                if f.endswith('.yaml'):
                    print(f"  - examples/{f}")
        sys.exit(1)
    
    try:
        # Cargar configuración
        print("⏳ Cargando configuración...")
        loader = ConfigurationLoader()
        config = loader.load_config([config_file])
        print(f"✅ Configuración cargada: {len(config.resources)} recursos")
        
        # Validar configuración
        print("\n⏳ Validando configuración...")
        from cdk_templates.schema_validator import SchemaValidator
        validator = SchemaValidator()
        validation_result = validator.validate(config)
        
        if not validation_result.is_valid:
            print("❌ Errores de validación encontrados:")
            for error in validation_result.errors:
                print(f"  - {error.field_path}: {error.message}")
            sys.exit(1)
        
        print("✅ Configuración válida")
        
        # Generar código CDK
        print(f"\n⏳ Generando código CDK para entorno '{environment}'...")
        generator = TemplateGenerator()
        result = generator.generate(config, environment=environment)
        
        if not result.success:
            print("❌ Errores en la generación:")
            for error in result.errors:
                print(f"  - {error}")
            sys.exit(1)
        
        # Crear directorio de salida
        os.makedirs(output_dir, exist_ok=True)
        
        # Guardar archivos generados
        print(f"\n📝 Guardando archivos en '{output_dir}/'...")
        for file_path, content in result.generated_files.items():
            full_path = os.path.join(output_dir, file_path)
            
            # Crear subdirectorios si es necesario
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Guardar archivo
            with open(full_path, 'w') as f:
                f.write(content)
            
            print(f"  ✅ {full_path}")
        
        print("\n" + "=" * 60)
        print("  ✅ Código CDK generado exitosamente")
        print("=" * 60)
        
        # Instrucciones siguientes
        print("\n📋 Próximos pasos:")
        print(f"\n1. Navegar al directorio de salida:")
        print(f"   cd {output_dir}")
        print("\n2. Instalar dependencias de CDK:")
        print("   pip install -r requirements.txt")
        print("\n3. Verificar el código generado:")
        print("   cdk synth")
        print("\n4. Ver qué se va a crear:")
        print("   cdk diff")
        print("\n5. Desplegar en AWS:")
        print("   cdk deploy --all")
        print("\n6. (Opcional) Destruir recursos:")
        print("   cdk destroy --all")
        print()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
