#!/usr/bin/env python3
"""
Script de Inicio Rápido - CDK AWS Templates System

Este script te guía paso a paso para crear tu primera infraestructura.
"""

import sys
import os
from pathlib import Path

def print_header(text):
    """Imprime un encabezado formateado."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")

def print_step(number, text):
    """Imprime un paso numerado."""
    print(f"\n[Paso {number}] {text}")
    print("-" * 70)

def print_success(text):
    """Imprime un mensaje de éxito."""
    print(f"✓ {text}")

def print_error(text):
    """Imprime un mensaje de error."""
    print(f"✗ {text}")

def print_info(text):
    """Imprime información."""
    print(f"ℹ {text}")

def main():
    print_header("Bienvenido al CDK AWS Templates System")
    print("Este script te ayudará a crear tu primera infraestructura AWS")
    print("usando configuración declarativa.\n")
    
    # Verificar que estamos en el directorio correcto
    if not Path("cdk_templates").exists():
        print_error("Error: Debes ejecutar este script desde el directorio raíz del proyecto")
        sys.exit(1)
    
    # Paso 1: Verificar instalación
    print_step(1, "Verificando instalación")
    
    try:
        from cdk_templates.config_loader import ConfigurationLoader
        from cdk_templates.schema_validator import SchemaValidator
        from cdk_templates.template_generator import TemplateGenerator
        from cdk_templates.documentation_generator import DocumentationGenerator
        print_success("Todos los módulos están instalados correctamente")
    except ImportError as e:
        print_error(f"Error al importar módulos: {e}")
        print_info("Ejecuta: pip install -r requirements.txt")
        sys.exit(1)
    
    # Paso 2: Seleccionar ejemplo
    print_step(2, "Seleccionar ejemplo")
    print("\nEjemplos disponibles:")
    print("  1. Ejemplo Básico - VPC simple")
    print("  2. Aplicación Web Completa - VPC + EC2 + RDS + S3")
    print("  3. Crear configuración personalizada")
    
    choice = input("\nSelecciona una opción (1-3): ").strip()
    
    if choice == "1":
        config_file = "examples/ejemplo-basico.yaml"
        print_info(f"Usando: {config_file}")
    elif choice == "2":
        config_file = "examples/aplicacion-web-completa.yaml"
        print_info(f"Usando: {config_file}")
    elif choice == "3":
        print_info("Creando configuración personalizada...")
        config_file = create_custom_config()
    else:
        print_error("Opción inválida")
        sys.exit(1)
    
    # Paso 3: Cargar configuración
    print_step(3, "Cargando configuración")
    
    try:
        loader = ConfigurationLoader()
        config = loader.load_config([config_file])
        print_success(f"Configuración cargada: {config.metadata.project}")
        print_info(f"  Proyecto: {config.metadata.project}")
        print_info(f"  Owner: {config.metadata.owner}")
        print_info(f"  Recursos: {len(config.resources)}")
    except Exception as e:
        print_error(f"Error al cargar configuración: {e}")
        sys.exit(1)
    
    # Paso 4: Validar configuración
    print_step(4, "Validando configuración")
    
    try:
        validator = SchemaValidator()
        result = validator.validate(config)
        
        if result.is_valid:
            print_success("Configuración válida")
        else:
            print_error("Se encontraron errores de validación:")
            for error in result.errors:
                print(f"  - {error.field_path}: {error.message}")
            sys.exit(1)
    except Exception as e:
        print_error(f"Error en validación: {e}")
        sys.exit(1)
    
    # Paso 5: Seleccionar entorno
    print_step(5, "Seleccionar entorno")
    
    environments = list(config.environments.keys())
    print("\nEntornos disponibles:")
    for i, env in enumerate(environments, 1):
        print(f"  {i}. {env}")
    
    env_choice = input(f"\nSelecciona un entorno (1-{len(environments)}): ").strip()
    
    try:
        env_index = int(env_choice) - 1
        if 0 <= env_index < len(environments):
            environment = environments[env_index]
            print_info(f"Entorno seleccionado: {environment}")
        else:
            print_error("Opción inválida")
            sys.exit(1)
    except ValueError:
        print_error("Opción inválida")
        sys.exit(1)
    
    # Paso 6: Generar código CDK
    print_step(6, "Generando código CDK")
    
    try:
        generator = TemplateGenerator()
        result = generator.generate(config, environment=environment)
        
        if result.success:
            print_success("Código CDK generado exitosamente")
            
            # Crear directorio de salida
            output_dir = Path(f"generated/{config.metadata.project}-{environment}")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Guardar archivos
            for file_path, content in result.generated_files.items():
                full_path = output_dir / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(full_path, 'w') as f:
                    f.write(content)
                
                print_info(f"  Creado: {full_path}")
            
            print_success(f"Archivos guardados en: {output_dir}")
        else:
            print_error("Errores en la generación:")
            for error in result.errors:
                print(f"  - {error}")
            sys.exit(1)
    except Exception as e:
        print_error(f"Error al generar código: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Paso 7: Generar documentación
    print_step(7, "Generando documentación")
    
    try:
        doc_gen = DocumentationGenerator()
        
        # Generar Markdown
        markdown = doc_gen.generate_markdown_docs(config)
        markdown_path = output_dir / "docs" / "arquitectura.md"
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(markdown_path, 'w') as f:
            f.write(markdown)
        
        print_success(f"Documentación Markdown: {markdown_path}")
        
        # Generar HTML
        html = doc_gen.export_to_html(markdown)
        html_path = output_dir / "docs" / "arquitectura.html"
        
        with open(html_path, 'w') as f:
            f.write(html)
        
        print_success(f"Documentación HTML: {html_path}")
    except Exception as e:
        print_error(f"Error al generar documentación: {e}")
        # No es crítico, continuamos
    
    # Paso 8: Próximos pasos
    print_step(8, "Próximos pasos")
    
    print("\n¡Listo! Tu infraestructura está configurada.")
    print("\nPara desplegar con CDK:")
    print(f"  1. cd {output_dir}")
    print("  2. cdk bootstrap  # Solo la primera vez")
    print("  3. cdk synth      # Sintetizar el stack")
    print("  4. cdk diff       # Ver cambios")
    print("  5. cdk deploy     # Desplegar")
    
    print("\nRecursos útiles:")
    print("  - Guía de Inicio: docs/GUIA_DE_INICIO.md")
    print("  - Ejemplos: examples/")
    print("  - Documentación: docs/")
    
    print_header("¡Gracias por usar CDK AWS Templates System!")

def create_custom_config():
    """Crea una configuración personalizada interactivamente."""
    print("\nCreando configuración personalizada...")
    
    project = input("Nombre del proyecto: ").strip()
    owner = input("Owner/Equipo: ").strip()
    cost_center = input("Centro de costos: ").strip()
    account_id = input("AWS Account ID: ").strip()
    region = input("Región AWS (ej: us-east-1): ").strip()
    
    config_content = f"""version: '1.0'

metadata:
  project: {project}
  owner: {owner}
  cost_center: {cost_center}
  description: Configuración personalizada

environments:
  dev:
    name: dev
    account_id: '{account_id}'
    region: {region}
    tags: {{}}
    overrides: {{}}

resources:
  - logical_id: vpc-{project}
    resource_type: vpc
    properties:
      cidr: '10.0.0.0/16'
      availability_zones: 2
      enable_dns_hostnames: true
      enable_flow_logs: true
    tags:
      Component: networking
    depends_on: []

deployment_rules: []
"""
    
    config_file = f"mi-config-{project}.yaml"
    with open(config_file, 'w') as f:
        f.write(config_content)
    
    print_success(f"Configuración creada: {config_file}")
    return config_file

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrumpido por el usuario")
        sys.exit(0)
    except Exception as e:
        print_error(f"Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
