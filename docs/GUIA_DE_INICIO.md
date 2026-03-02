# Guía de Inicio - CDK AWS Templates System

## Introducción

El CDK AWS Templates System es un framework en Python que te permite desplegar infraestructura AWS de manera declarativa y estandarizada. Define tu infraestructura en archivos YAML o JSON, y el sistema genera automáticamente código CDK Python siguiendo las mejores prácticas.

## Características Principales

- **Configuración Declarativa**: Define recursos en YAML/JSON en lugar de escribir código
- **Convenciones Automáticas**: Nombres y etiquetas consistentes aplicados automáticamente
- **Validación Previa**: Detecta errores antes del despliegue
- **Gestión de Dependencias**: Resuelve automáticamente las relaciones entre recursos
- **Multi-Entorno**: Gestiona dev, staging y producción con una sola configuración
- **Documentación Automática**: Genera diagramas y documentación de tu infraestructura

## Requisitos Previos

- Python 3.8 o superior
- AWS CDK instalado (`npm install -g aws-cdk`)
- Credenciales AWS configuradas
- Conocimientos básicos de AWS y CDK

## Instalación

1. Clona el repositorio:
```bash
git clone <repository-url>
cd cdk_templates
```

2. Crea un entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. Instala las dependencias:
```bash
pip install -r requirements.txt
```

4. Verifica la instalación:
```bash
python -m pytest tests/ -v
```

## Tu Primera Configuración

### Paso 1: Crear un Archivo de Configuración

Crea un archivo `mi-infraestructura.yaml`:

```yaml
version: '1.0'

metadata:
  project: mi-proyecto
  owner: mi-equipo
  cost_center: ingenieria
  description: Mi primera infraestructura con CDK Templates

environments:
  dev:
    name: dev
    account_id: '123456789012'
    region: us-east-1
    tags: {}
    overrides: {}

resources:
  - logical_id: vpc-principal
    resource_type: vpc
    properties:
      cidr: '10.0.0.0/16'
      availability_zones: 2
      enable_dns_hostnames: true
      enable_flow_logs: true
    tags: {}
    depends_on: []

deployment_rules: []
```

### Paso 2: Validar la Configuración

```bash
python -c "
from cdk_templates.config_loader import ConfigurationLoader
from cdk_templates.schema_validator import SchemaValidator

loader = ConfigurationLoader()
config = loader.load_config(['mi-infraestructura.yaml'])

validator = SchemaValidator()
result = validator.validate(config)

if result.is_valid:
    print('✓ Configuración válida')
else:
    print('✗ Errores encontrados:')
    for error in result.errors:
        print(f'  - {error.field_path}: {error.message}')
"
```

### Paso 3: Generar Código CDK

```python
from cdk_templates.config_loader import ConfigurationLoader
from cdk_templates.template_generator import TemplateGenerator

# Cargar configuración
loader = ConfigurationLoader()
config = loader.load_config(['mi-infraestructura.yaml'])

# Generar código CDK
generator = TemplateGenerator()
result = generator.generate(config, environment='dev')

if result.success:
    print('✓ Código CDK generado exitosamente')
    
    # Guardar archivos generados
    for file_path, content in result.generated_files.items():
        with open(file_path, 'w') as f:
            f.write(content)
        print(f'  Creado: {file_path}')
else:
    print('✗ Errores en la generación:')
    for error in result.errors:
        print(f'  - {error}')
```

### Paso 4: Desplegar con CDK

```bash
# Inicializar CDK (solo la primera vez)
cdk bootstrap

# Sintetizar el stack
cdk synth

# Desplegar
cdk deploy
```

## Ejemplos Comunes

### Ejemplo 1: VPC con Subnets Públicas y Privadas

```yaml
resources:
  - logical_id: vpc-app
    resource_type: vpc
    properties:
      cidr: '10.0.0.0/16'
      availability_zones: 3
      enable_dns_hostnames: true
      enable_dns_support: true
      enable_flow_logs: true
      nat_gateways: 1
    tags:
      Component: networking
```

**Resultado**: VPC con subnets públicas y privadas en 3 zonas de disponibilidad, NAT Gateway, y Flow Logs habilitados.

### Ejemplo 2: Instancia EC2 con Session Manager

```yaml
resources:
  - logical_id: vpc-app
    resource_type: vpc
    properties:
      cidr: '10.0.0.0/16'
      availability_zones: 2

  - logical_id: ec2-web
    resource_type: ec2
    properties:
      instance_type: t3.micro
      vpc_ref: '${resource.vpc-app.id}'
      enable_session_manager: true
      enable_detailed_monitoring: false
      root_volume:
        size: 30
        encrypted: true
        volume_type: gp3
    tags:
      Component: web-server
    depends_on:
      - vpc-app
```

**Resultado**: Instancia EC2 en la VPC, con IAM role para Session Manager, security group configurado, y volumen EBS encriptado.

### Ejemplo 3: Base de Datos RDS con Alta Disponibilidad

```yaml
resources:
  - logical_id: vpc-app
    resource_type: vpc
    properties:
      cidr: '10.0.0.0/16'
      availability_zones: 3

  - logical_id: rds-principal
    resource_type: rds
    properties:
      engine: postgres
      engine_version: '15.3'
      instance_class: db.t3.medium
      allocated_storage: 100
      multi_az: true
      vpc_ref: '${resource.vpc-app.id}'
      backup_retention_days: 7
      encryption_enabled: true
    tags:
      Component: database
    depends_on:
      - vpc-app
```

**Resultado**: Base de datos PostgreSQL Multi-AZ en subnets privadas, con backups automáticos, encriptación, y credenciales en Secrets Manager.

### Ejemplo 4: Bucket S3 con Versionado y Encriptación

```yaml
resources:
  - logical_id: s3-datos
    resource_type: s3
    properties:
      versioning_enabled: true
      encryption: AES256
      block_public_access: true
      lifecycle_rules:
        - id: transition-to-glacier
          enabled: true
          transitions:
            - storage_class: STANDARD_IA
              days: 30
            - storage_class: GLACIER
              days: 90
    tags:
      Component: storage
```

**Resultado**: Bucket S3 con versionado, encriptación, acceso público bloqueado, y reglas de ciclo de vida para optimizar costos.

## Configuración Multi-Entorno

Define diferentes configuraciones para cada entorno:

```yaml
version: '1.0'

metadata:
  project: mi-app
  owner: mi-equipo
  cost_center: ingenieria
  description: Aplicación multi-entorno

environments:
  dev:
    name: dev
    account_id: '111111111111'
    region: us-east-1
    tags:
      Environment: development
    overrides:
      # Configuraciones específicas de dev
      rds-app:
        properties:
          instance_class: db.t3.small
          multi_az: false

  prod:
    name: prod
    account_id: '222222222222'
    region: us-east-1
    tags:
      Environment: production
    overrides:
      # Configuraciones específicas de prod
      rds-app:
        properties:
          instance_class: db.r5.large
          multi_az: true
          backup_retention_days: 30

resources:
  - logical_id: rds-app
    resource_type: rds
    properties:
      engine: postgres
      engine_version: '15.3'
      instance_class: db.t3.medium  # Valor por defecto
      allocated_storage: 100
      multi_az: false  # Valor por defecto
      backup_retention_days: 7  # Valor por defecto
```

Genera código para cada entorno:

```python
# Para desarrollo
result_dev = generator.generate(config, environment='dev')

# Para producción
result_prod = generator.generate(config, environment='prod')
```

## Referencias Entre Recursos

Usa referencias para conectar recursos:

```yaml
resources:
  - logical_id: vpc-app
    resource_type: vpc
    properties:
      cidr: '10.0.0.0/16'

  - logical_id: ec2-web
    resource_type: ec2
    properties:
      instance_type: t3.micro
      vpc_ref: '${resource.vpc-app.id}'  # Referencia a la VPC
    depends_on:
      - vpc-app

  - logical_id: rds-app
    resource_type: rds
    properties:
      engine: postgres
      vpc_ref: '${resource.vpc-app.id}'  # Misma VPC
    depends_on:
      - vpc-app
```

El sistema:
- Valida que las referencias existan
- Detecta dependencias circulares
- Ordena los recursos para despliegue correcto

## Convenciones de Nombres

El sistema aplica automáticamente una convención de nombres:

**Patrón**: `{entorno}-{proyecto}-{tipo}-{propósito}-{región}[-{instancia}]`

**Ejemplos**:
- VPC: `dev-mi-app-vpc-principal-us-east-1`
- EC2: `prod-mi-app-ec2-web-us-east-1-01`
- RDS: `staging-mi-app-rds-principal-eu-west-1`
- S3: `prod-mi-app-s3-datos-us-east-1`

## Etiquetas Obligatorias

Todas las recursos reciben automáticamente estas etiquetas:

- `Environment`: dev, staging, prod
- `Project`: nombre del proyecto
- `Owner`: equipo responsable
- `CostCenter`: centro de costos
- `ManagedBy`: cdk-template-system

Puedes agregar etiquetas adicionales:

```yaml
resources:
  - logical_id: ec2-web
    resource_type: ec2
    properties:
      instance_type: t3.micro
    tags:
      Component: frontend
      Version: v1.2.3
      Team: web-team
```

## Validación de Configuraciones

El sistema valida:

1. **Sintaxis**: YAML/JSON bien formado
2. **Esquema**: Campos requeridos y tipos correctos
3. **Referencias**: Recursos referenciados existen
4. **Dependencias**: No hay ciclos circulares
5. **Límites AWS**: Nombres, tamaños, etc.

Ejemplo de validación:

```python
from cdk_templates.validation_engine import ValidationEngine

engine = ValidationEngine()
result = engine.validate_all(config)

if not result.is_valid:
    print('Errores encontrados:')
    for error in result.errors:
        print(f'  [{error.severity}] {error.field_path}')
        print(f'    {error.message}')
```

## Documentación Automática

Genera documentación de tu infraestructura:

```python
from cdk_templates.documentation_generator import DocumentationGenerator

doc_gen = DocumentationGenerator()

# Generar diagrama Mermaid
diagram = doc_gen.generate_architecture_diagram(config)

# Generar documentación Markdown
markdown = doc_gen.generate_markdown_docs(config)

# Exportar a HTML
html = doc_gen.export_to_html(markdown)

# Guardar
with open('docs/arquitectura.md', 'w') as f:
    f.write(markdown)
```

## Solución de Problemas

### Error: "Missing required field"

**Causa**: Falta un campo obligatorio en la configuración.

**Solución**: Revisa el esquema del recurso en `schemas/{tipo}.json` y agrega el campo faltante.

### Error: "Circular dependency detected"

**Causa**: Dos o más recursos se referencian mutuamente.

**Solución**: Revisa las referencias `${resource.X.Y}` y elimina el ciclo.

### Error: "Invalid resource reference"

**Causa**: Referencia a un recurso que no existe.

**Solución**: Verifica que el `logical_id` referenciado esté definido en `resources`.

### Error: "Syntax error in generated file"

**Causa**: Problema en la generación de código CDK.

**Solución**: Revisa los logs, verifica que las referencias sean válidas, y reporta el issue si persiste.

## Mejores Prácticas

1. **Organiza por Entornos**: Usa archivos separados para cada entorno
2. **Usa Referencias**: Conecta recursos con `${resource.X.Y}` en lugar de valores hardcodeados
3. **Valida Siempre**: Ejecuta validación antes de generar código
4. **Etiqueta Todo**: Agrega etiquetas descriptivas para facilitar gestión
5. **Documenta**: Usa el campo `description` en metadata
6. **Versiona**: Mantén tus configuraciones en Git
7. **Prueba en Dev**: Despliega primero en desarrollo antes de producción
8. **Revisa Código**: Inspecciona el código CDK generado antes de desplegar

## Próximos Pasos

1. **Explora Ejemplos**: Revisa `examples/` para casos de uso más complejos
2. **Lee la Documentación**: Consulta `docs/` para detalles técnicos
3. **Prueba Reglas**: Implementa reglas de despliegue personalizadas
4. **Integra CI/CD**: Automatiza validación y despliegue
5. **Contribuye**: Reporta issues y contribuye mejoras

## Recursos Adicionales

- [Documentación AWS CDK](https://docs.aws.amazon.com/cdk/)
- [Mejores Prácticas AWS](https://aws.amazon.com/architecture/well-architected/)
- [Esquemas JSON](schemas/)
- [Ejemplos Completos](examples/)
- [Guía de CLI](docs/CLI_USAGE.md)

## Soporte

¿Necesitas ayuda? 

- Revisa la documentación en `docs/`
- Consulta los tests en `tests/` para ejemplos
- Abre un issue en el repositorio
- Contacta al equipo de infraestructura

---

**¡Feliz despliegue!** 🚀
