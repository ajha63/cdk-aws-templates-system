# Ejemplos de Configuración

Esta carpeta contiene ejemplos prácticos de configuraciones para el CDK AWS Templates System.

## Ejemplos Disponibles

### 1. Ejemplo Básico (`ejemplo-basico.yaml`)

**Descripción**: VPC simple con subnets públicas y privadas.

**Recursos**:
- 1 VPC con CIDR 10.0.0.0/16
- Subnets en 2 zonas de disponibilidad
- NAT Gateway para subnets privadas
- VPC Flow Logs habilitados

**Uso**:
```bash
python -c "
from cdk_templates.config_loader import ConfigurationLoader
from cdk_templates.template_generator import TemplateGenerator

loader = ConfigurationLoader()
config = loader.load_config(['examples/ejemplo-basico.yaml'])

generator = TemplateGenerator()
result = generator.generate(config, environment='dev')

for file_path, content in result.generated_files.items():
    with open(file_path, 'w') as f:
        f.write(content)
    print(f'Creado: {file_path}')
"
```

### 2. Aplicación Web Completa (`aplicacion-web-completa.yaml`)

**Descripción**: Arquitectura completa para una aplicación web con base de datos.

**Recursos**:
- 1 VPC con 3 zonas de disponibilidad
- 1 Instancia EC2 con Session Manager
- 1 Base de datos RDS PostgreSQL
- 2 Buckets S3 (assets y backups)

**Características**:
- Configuración multi-entorno (dev/prod)
- Referencias entre recursos
- User data para configuración automática
- Lifecycle rules para optimización de costos
- Alta disponibilidad en producción

**Uso**:
```bash
# Para desarrollo
python -c "
from cdk_templates.config_loader import ConfigurationLoader
from cdk_templates.template_generator import TemplateGenerator

loader = ConfigurationLoader()
config = loader.load_config(['examples/aplicacion-web-completa.yaml'])

generator = TemplateGenerator()
result = generator.generate(config, environment='dev')

for file_path, content in result.generated_files.items():
    with open(file_path, 'w') as f:
        f.write(content)
"

# Para producción
python -c "
from cdk_templates.config_loader import ConfigurationLoader
from cdk_templates.template_generator import TemplateGenerator

loader = ConfigurationLoader()
config = loader.load_config(['examples/aplicacion-web-completa.yaml'])

generator = TemplateGenerator()
result = generator.generate(config, environment='prod')

for file_path, content in result.generated_files.items():
    with open(f'prod-{file_path}', 'w') as f:
        f.write(content)
"
```

## Cómo Usar los Ejemplos

### Paso 1: Validar la Configuración

```python
from cdk_templates.config_loader import ConfigurationLoader
from cdk_templates.schema_validator import SchemaValidator

loader = ConfigurationLoader()
config = loader.load_config(['examples/ejemplo-basico.yaml'])

validator = SchemaValidator()
result = validator.validate(config)

if result.is_valid:
    print('✓ Configuración válida')
else:
    for error in result.errors:
        print(f'✗ {error.field_path}: {error.message}')
```

### Paso 2: Generar Código CDK

```python
from cdk_templates.template_generator import TemplateGenerator

generator = TemplateGenerator()
result = generator.generate(config, environment='dev')

if result.success:
    for file_path, content in result.generated_files.items():
        with open(file_path, 'w') as f:
            f.write(content)
        print(f'Creado: {file_path}')
```

### Paso 3: Generar Documentación

```python
from cdk_templates.documentation_generator import DocumentationGenerator

doc_gen = DocumentationGenerator()
markdown = doc_gen.generate_markdown_docs(config)

with open('docs/arquitectura.md', 'w') as f:
    f.write(markdown)
```

### Paso 4: Desplegar con CDK

```bash
# Sintetizar
cdk synth

# Revisar cambios
cdk diff

# Desplegar
cdk deploy
```

## Personalización

Puedes personalizar estos ejemplos:

1. **Cambiar Regiones**: Modifica el campo `region` en `environments`
2. **Ajustar Tamaños**: Cambia `instance_type`, `instance_class`, etc.
3. **Agregar Recursos**: Añade más recursos a la lista
4. **Modificar Tags**: Agrega etiquetas personalizadas
5. **Configurar Entornos**: Define overrides específicos por entorno

## Estructura de Archivos Generados

Después de generar el código, tendrás:

```
.
├── app.py                    # Punto de entrada CDK
├── stacks/
│   ├── __init__.py
│   └── {stack_name}_stack.py # Stack CDK generado
└── docs/
    ├── architecture.md       # Documentación Markdown
    └── architecture.html     # Documentación HTML
```

## Consejos

1. **Empieza Simple**: Usa `ejemplo-basico.yaml` para familiarizarte
2. **Valida Siempre**: Ejecuta validación antes de generar código
3. **Revisa el Código**: Inspecciona el código CDK generado
4. **Prueba en Dev**: Despliega primero en desarrollo
5. **Documenta**: Genera documentación para tu equipo

## Recursos Adicionales

- [Guía de Inicio](../docs/GUIA_DE_INICIO.md)
- [Documentación de Esquemas](../schemas/)
- [Tests de Integración](../tests/integration/)

---

¿Tienes dudas? Consulta la [Guía de Inicio](../docs/GUIA_DE_INICIO.md) o revisa los tests en `tests/` para más ejemplos.
