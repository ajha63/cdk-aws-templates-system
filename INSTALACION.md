# 📦 Guía de Instalación

## ✅ Archivos Creados

He agregado los siguientes archivos para facilitar la instalación:

1. **requirements.txt** - Dependencias principales del proyecto
2. **requirements-dev.txt** - Dependencias de desarrollo
3. **install.sh** - Script de instalación automatizada
4. **fix_git_email.sh** - Script para solucionar problemas de email con GitHub

## 🚀 Instalación Rápida

### Opción 1: Script Automatizado (Recomendado)

```bash
./install.sh
```

Este script:
- ✓ Verifica que Python 3.8+ esté instalado
- ✓ Crea el entorno virtual
- ✓ Instala todas las dependencias
- ✓ Instala el paquete en modo desarrollo
- ✓ Ejecuta los tests (opcional)

### Opción 2: Instalación Manual

```bash
# 1. Crear entorno virtual
python3 -m venv venv

# 2. Activar entorno virtual
source venv/bin/activate  # En Windows: venv\Scripts\activate

# 3. Actualizar pip
pip install --upgrade pip

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Instalar el paquete en modo desarrollo
pip install -e .

# 6. Verificar instalación
pytest tests/ -v
```

## 📋 Dependencias Principales

### Core (requirements.txt)

```
pyyaml>=6.0              # Parseo de archivos YAML
jsonschema>=4.17.0       # Validación de esquemas JSON
click>=8.0.0             # CLI framework
rich>=13.0.0             # Output formateado en terminal
aws-cdk-lib>=2.0.0       # AWS CDK library
constructs>=10.0.0       # CDK constructs
pytest>=7.0.0            # Framework de testing
hypothesis>=6.0.0        # Property-based testing
pytest-cov>=4.0.0        # Cobertura de tests
black>=23.0.0            # Formateo de código
mypy>=1.0.0              # Type checking
python-dateutil>=2.8.0   # Utilidades de fecha
```

### Desarrollo (requirements-dev.txt)

```
flake8>=6.0.0            # Linting
pylint>=2.17.0           # Análisis estático
isort>=5.12.0            # Ordenamiento de imports
pre-commit>=3.0.0        # Git hooks
sphinx>=6.0.0            # Documentación
sphinx-rtd-theme>=1.2.0  # Tema de documentación
types-PyYAML>=6.0.0      # Type hints para PyYAML
types-jsonschema>=4.17.0 # Type hints para jsonschema
```

## 🔧 Requisitos del Sistema

- **Python**: 3.8 o superior
- **pip**: Última versión
- **Git**: Para clonar el repositorio
- **Node.js**: 14.x o superior (para AWS CDK CLI)
- **npm**: 6.x o superior (incluido con Node.js)
- **AWS CDK Toolkit**: 2.x (se instala con npm)
- **Sistema Operativo**: Linux, macOS, o Windows

### Verificar Requisitos

```bash
# Verificar Python
python3 --version  # Debe ser 3.8 o superior

# Verificar pip
pip3 --version

# Verificar Git
git --version

# Verificar Node.js
node --version  # Debe ser 14.x o superior

# Verificar npm
npm --version  # Debe ser 6.x o superior
```

## 🛠️ Instalar AWS CDK Toolkit

El AWS CDK Toolkit es necesario para desplegar los stacks generados en AWS.

### Instalar Node.js (si no está instalado)

```bash
# macOS (con Homebrew)
brew install node

# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Windows
# Descarga desde: https://nodejs.org/
```

### Instalar AWS CDK CLI Globalmente

```bash
# Instalar AWS CDK CLI
npm install -g aws-cdk

# Verificar instalación
cdk --version  # Debe mostrar 2.x.x
```

### Configurar AWS Credentials

Antes de usar CDK, necesitas configurar tus credenciales de AWS:

```bash
# Opción 1: Usar AWS CLI
aws configure

# Opción 2: Variables de entorno
export AWS_ACCESS_KEY_ID=tu_access_key
export AWS_SECRET_ACCESS_KEY=tu_secret_key
export AWS_DEFAULT_REGION=us-east-1

# Opción 3: Archivo de credenciales (~/.aws/credentials)
[default]
aws_access_key_id = tu_access_key
aws_secret_access_key = tu_secret_key
```

### Bootstrap del Entorno CDK (Primera vez)

Si es la primera vez que usas CDK en tu cuenta de AWS:

```bash
# Bootstrap para una región específica
cdk bootstrap aws://ACCOUNT-ID/REGION

# Ejemplo:
cdk bootstrap aws://123456789012/us-east-1
```

El bootstrap crea los recursos necesarios en tu cuenta de AWS para que CDK pueda desplegar stacks.

## 📖 Después de la Instalación

### 1. Verificar que todo funciona

```bash
# Activar entorno virtual (si no está activado)
source venv/bin/activate

# Ejecutar tests
pytest tests/ -v

# Debería mostrar: 483/491 tests passing
```

### 2. Probar el script de inicio rápido

```bash
python quickstart.py
```

### 3. Probar con un ejemplo

```bash
python -c "
from cdk_templates.config_loader import ConfigurationLoader
from cdk_templates.template_generator import TemplateGenerator

loader = ConfigurationLoader()
config = loader.load_config(['examples/ejemplo-basico.yaml'])

generator = TemplateGenerator()
result = generator.generate(config, environment='dev')

print(f'✓ Generación exitosa: {len(result.generated_files)} archivos')
"
```

## 🆘 Solución de Problemas

### Error: "python3: command not found"

**Solución**: Instala Python 3.8 o superior

```bash
# macOS (con Homebrew)
brew install python@3.11

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3.11

# Windows
# Descarga desde: https://www.python.org/downloads/
```

### Error: "node: command not found" o "npm: command not found"

**Solución**: Instala Node.js y npm

```bash
# macOS (con Homebrew)
brew install node

# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Windows
# Descarga desde: https://nodejs.org/
```

### Error: "cdk: command not found"

**Solución**: Instala AWS CDK CLI

```bash
npm install -g aws-cdk

# Si tienes problemas de permisos en macOS/Linux:
sudo npm install -g aws-cdk

# Verificar instalación
cdk --version
```

### Error: "Unable to resolve AWS account to use"

**Solución**: Configura tus credenciales de AWS

```bash
# Opción 1: Usar AWS CLI
aws configure

# Opción 2: Variables de entorno
export AWS_ACCESS_KEY_ID=tu_access_key
export AWS_SECRET_ACCESS_KEY=tu_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

### Error: "This stack uses assets, so the toolkit stack must be deployed"

**Solución**: Ejecuta bootstrap de CDK

```bash
cdk bootstrap aws://ACCOUNT-ID/REGION

# Ejemplo:
cdk bootstrap aws://123456789012/us-east-1
```

### Error: "pip: command not found"

**Solución**: Instala pip

```bash
# macOS/Linux
python3 -m ensurepip --upgrade

# Ubuntu/Debian
sudo apt-get install python3-pip
```

### Error: "No module named 'venv'"

**Solución**: Instala el módulo venv

```bash
# Ubuntu/Debian
sudo apt-get install python3-venv
```

### Error al instalar dependencias

**Solución**: Actualiza pip y setuptools

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### Error: "Permission denied: ./install.sh"

**Solución**: Dale permisos de ejecución

```bash
chmod +x install.sh
./install.sh
```

## 🔄 Actualizar Dependencias

Para actualizar todas las dependencias a sus últimas versiones:

```bash
# Activar entorno virtual
source venv/bin/activate

# Actualizar pip
pip install --upgrade pip

# Actualizar todas las dependencias
pip install --upgrade -r requirements.txt

# Verificar que todo funciona
pytest tests/ -v
```

## 🧹 Desinstalación

Para eliminar completamente el entorno:

```bash
# Desactivar entorno virtual
deactivate

# Eliminar directorio del entorno virtual
rm -rf venv/

# Eliminar archivos de caché
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type d -name ".pytest_cache" -exec rm -rf {} +
find . -type d -name ".hypothesis" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

## 📚 Recursos Adicionales

- [Guía de Inicio Completa](docs/GUIA_DE_INICIO.md)
- [Documentación de Python Virtual Environments](https://docs.python.org/3/library/venv.html)
- [Documentación de pip](https://pip.pypa.io/en/stable/)
- [Ejemplos de Uso](examples/)

## 💡 Consejos

1. **Siempre activa el entorno virtual** antes de trabajar:
   ```bash
   source venv/bin/activate
   ```

2. **Mantén las dependencias actualizadas**:
   ```bash
   pip list --outdated
   ```

3. **Usa requirements-dev.txt** para desarrollo:
   ```bash
   pip install -r requirements-dev.txt
   ```

4. **Ejecuta los tests** antes de hacer commits:
   ```bash
   pytest tests/ -v
   ```

---

**¿Necesitas ayuda?** Consulta la [Guía de Inicio](docs/GUIA_DE_INICIO.md) o abre un issue en GitHub.
