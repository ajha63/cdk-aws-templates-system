# CDK AWS Templates System

Sistema de plantillas declarativas para AWS CDK que permite desplegar infraestructura AWS de manera homogénea y consistente usando archivos de configuración YAML/JSON.

## 🚀 Inicio Rápido

```bash
# 1. Clonar el repositorio
git clone <repository-url>
cd cdk_templates

# 2. Instalar dependencias
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Ejecutar el script de inicio rápido
python quickstart.py
```

## ✨ Características

- **Configuración Declarativa**: Define infraestructura en YAML/JSON en lugar de código
- **Convenciones Automáticas**: Nombres y etiquetas consistentes aplicados automáticamente
- **Validación Previa**: Detecta errores antes del despliegue
- **Multi-Entorno**: Gestiona dev, staging y producción con una sola configuración
- **Gestión de Dependencias**: Resuelve automáticamente las relaciones entre recursos
- **Documentación Automática**: Genera diagramas y documentación de tu infraestructura
- **Reglas de Despliegue**: Aplica políticas corporativas automáticamente

## 📋 Recursos Soportados

- **VPC**: Redes privadas virtuales con subnets públicas y privadas
- **EC2**: Instancias con Session Manager, IAM roles y security groups
- **RDS**: Bases de datos con Multi-AZ, backups y encriptación
- **S3**: Buckets con versionado, encriptación y lifecycle rules

## 📖 Documentación

- [Guía de Inicio](docs/GUIA_DE_INICIO.md) - Tutorial completo paso a paso
- [Ejemplos](examples/) - Configuraciones de ejemplo listas para usar
- [Uso del CLI](docs/CLI_USAGE.md) - Referencia de comandos
- [Motor de Validación](docs/VALIDATION_ENGINE_USAGE.md) - Validación de configuraciones

## 🎯 Ejemplo Rápido

Crea un archivo `mi-vpc.yaml`:

```yaml
version: '1.0'

metadata:
  project: mi-proyecto
  owner: mi-equipo
  cost_center: ingenieria
  description: Mi primera VPC

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

Genera el código CDK:

```python
from cdk_templates.config_loader import ConfigurationLoader
from cdk_templates.template_generator import TemplateGenerator

# Cargar y generar
loader = ConfigurationLoader()
config = loader.load_config(['mi-vpc.yaml'])

generator = TemplateGenerator()
result = generator.generate(config, environment='dev')

# Guardar archivos
for file_path, content in result.generated_files.items():
    with open(file_path, 'w') as f:
        f.write(content)
```

Despliega con CDK:

```bash
cdk synth
cdk deploy
```

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    Usuario / DevOps                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ YAML/JSON Config
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Configuration Loader                            │
│  • Parsea YAML/JSON                                         │
│  • Combina múltiples archivos                               │
│  • Resuelve variables de entorno                            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Schema Validator                                │
│  • Valida estructura                                        │
│  • Verifica tipos de datos                                  │
│  • Aplica valores por defecto                               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Resource Link Resolver                          │
│  • Construye grafo de dependencias                          │
│  • Detecta ciclos circulares                                │
│  • Ordena recursos para despliegue                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Deployment Rules Engine                         │
│  • Aplica políticas corporativas                            │
│  • Fuerza encriptación                                      │
│  • Valida etiquetas obligatorias                            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Template Generator                              │
│  • Genera código CDK Python                                 │
│  • Aplica convenciones de nombres                           │
│  • Agrega etiquetas obligatorias                            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Código CDK Python + Documentación               │
│  • app.py                                                   │
│  • stacks/*.py                                              │
│  • docs/arquitectura.md                                     │
└─────────────────────────────────────────────────────────────┘
```

## 🧪 Testing

El proyecto incluye una suite completa de tests:

```bash
# Ejecutar todos los tests
pytest tests/ -v

# Tests unitarios
pytest tests/unit/ -v

# Tests de integración
pytest tests/integration/ -v

# Tests basados en propiedades
pytest tests/property/ -v

# Con cobertura
pytest tests/ --cov=cdk_templates --cov-report=html
```

**Cobertura actual**: 81% (483 de 491 tests pasando)

## 📊 Convenciones

### Nombres de Recursos

Patrón: `{entorno}-{proyecto}-{tipo}-{propósito}-{región}[-{instancia}]`

Ejemplos:
- `dev-mi-app-vpc-principal-us-east-1`
- `prod-mi-app-ec2-web-us-east-1-01`
- `staging-mi-app-rds-principal-eu-west-1`

### Etiquetas Obligatorias

Todos los recursos reciben automáticamente:
- `Environment`: dev, staging, prod
- `Project`: nombre del proyecto
- `Owner`: equipo responsable
- `CostCenter`: centro de costos
- `ManagedBy`: cdk-template-system

## 🔧 Configuración Avanzada

### Multi-Entorno

```yaml
environments:
  dev:
    name: dev
    account_id: '111111111111'
    region: us-east-1
    overrides:
      ec2-web:
        properties:
          instance_type: t3.micro

  prod:
    name: prod
    account_id: '222222222222'
    region: us-east-1
    overrides:
      ec2-web:
        properties:
          instance_type: t3.large
          enable_detailed_monitoring: true
```

### Referencias Entre Recursos

```yaml
resources:
  - logical_id: vpc-app
    resource_type: vpc
    properties:
      cidr: '10.0.0.0/16'

  - logical_id: ec2-web
    resource_type: ec2
    properties:
      vpc_ref: '${resource.vpc-app.id}'  # Referencia a la VPC
    depends_on:
      - vpc-app
```

### Referencias Cross-Stack

```yaml
resources:
  - logical_id: ec2-app
    resource_type: ec2
    properties:
      vpc_ref: '${import.NetworkStack-VpcId}'  # Importa de otro stack
```

## 🛠️ Desarrollo

### Estructura del Proyecto

```
cdk_templates/
├── cdk_templates/          # Código fuente principal
│   ├── config_loader.py    # Carga de configuraciones
│   ├── schema_validator.py # Validación de esquemas
│   ├── template_generator.py # Generación de código CDK
│   ├── templates/          # Plantillas por tipo de recurso
│   │   ├── vpc_template.py
│   │   ├── ec2_template.py
│   │   ├── rds_template.py
│   │   └── s3_template.py
│   └── ...
├── schemas/                # Esquemas JSON Schema
├── tests/                  # Suite de tests
├── examples/               # Ejemplos de configuración
├── docs/                   # Documentación
└── quickstart.py          # Script de inicio rápido
```

### Agregar un Nuevo Tipo de Recurso

1. Crear esquema JSON en `schemas/{tipo}.json`
2. Crear plantilla en `cdk_templates/templates/{tipo}_template.py`
3. Implementar la interfaz `ResourceTemplate`
4. Agregar tests en `tests/unit/templates/test_{tipo}_template.py`
5. Actualizar documentación

## 🤝 Contribuir

Las contribuciones son bienvenidas! Por favor:

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agrega nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 🙏 Agradecimientos

- AWS CDK Team por el excelente framework
- Comunidad de Python por las herramientas de testing
- Todos los contribuidores del proyecto

## 📞 Soporte

- 📖 [Documentación Completa](docs/)
- 💬 [Issues](https://github.com/tu-repo/issues)
- 📧 Email: tu-email@ejemplo.com

---

**¡Feliz despliegue!** 🚀

Hecho con ❤️ por el equipo de infraestructura
