# Instrucciones de AWS CDK Toolkit

## 📋 Resumen de Cambios

He agregado instrucciones completas para instalar y configurar AWS CDK Toolkit en toda la documentación del proyecto.

## 🆕 Archivos Actualizados

### 1. **INSTALACION.md**
- ✅ Agregada sección de requisitos de Node.js y npm
- ✅ Instrucciones de instalación de AWS CDK CLI
- ✅ Configuración de credenciales AWS (3 opciones)
- ✅ Instrucciones de bootstrap de CDK
- ✅ Solución de problemas para errores comunes de CDK

### 2. **install.sh**
- ✅ Verificación automática de Node.js
- ✅ Verificación automática de npm
- ✅ Verificación automática de AWS CDK CLI
- ✅ Opción para instalar AWS CDK CLI durante la instalación
- ✅ Verificación de credenciales AWS
- ✅ Mensajes informativos sobre cómo instalar componentes faltantes

### 3. **docs/GUIA_DE_INICIO.md**
- ✅ Sección expandida de "Requisitos Previos" con todos los componentes
- ✅ Instrucciones detalladas de configuración de credenciales AWS
- ✅ Explicación del proceso de bootstrap de CDK
- ✅ Pasos detallados de despliegue (10 pasos completos):
  1. Crear configuración YAML
  2. Validar configuración
  3. Generar código CDK
  4. Revisar código generado
  5. Instalar dependencias CDK
  6. Sintetizar stack (verificación)
  7. Ver cambios (diff)
  8. Desplegar en AWS
  9. Verificar despliegue
  10. Destruir recursos (cleanup)

### 4. **README.md** (Inglés)
- ✅ Sección de Prerequisites con Node.js y AWS CDK CLI
- ✅ Instrucciones de bootstrap
- ✅ Ejemplo completo de despliegue con comandos CDK

### 5. **README.es.md** (Español)
- ✅ Sección de Requisitos Previos con Node.js y AWS CDK CLI
- ✅ Instrucciones de bootstrap
- ✅ Ejemplo completo de despliegue con comandos CDK

### 6. **docs/AWS_CDK_SETUP.md** (NUEVO)
Guía completa y exhaustiva que cubre:
- ✅ Qué es AWS CDK y por qué es necesario
- ✅ Instalación de Node.js en macOS, Linux y Windows
- ✅ Instalación de AWS CLI (opcional)
- ✅ Instalación de AWS CDK CLI
- ✅ Solución de problemas de instalación
- ✅ Configuración de credenciales AWS (3 métodos)
- ✅ Proceso de bootstrap explicado en detalle
- ✅ Bootstrap para múltiples regiones
- ✅ Comandos básicos de CDK con ejemplos
- ✅ Integración con CDK AWS Templates System
- ✅ Solución de problemas comunes (10+ escenarios)
- ✅ Mejores prácticas
- ✅ Enlaces a recursos adicionales

## 🚀 Cómo Usar las Nuevas Instrucciones

### Para Instalación Inicial

```bash
# 1. Ejecutar el script de instalación mejorado
./install.sh

# El script ahora:
# - Verifica Node.js y npm
# - Verifica AWS CDK CLI
# - Ofrece instalar AWS CDK CLI si no está presente
# - Verifica credenciales AWS
# - Proporciona instrucciones claras para componentes faltantes
```

### Para Configurar AWS CDK por Primera Vez

```bash
# 1. Instalar Node.js (si no está instalado)
# macOS:
brew install node

# Ubuntu/Debian:
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# 2. Instalar AWS CDK CLI
npm install -g aws-cdk

# 3. Configurar credenciales AWS
aws configure

# 4. Bootstrap de CDK (reemplaza con tu Account ID)
cdk bootstrap aws://123456789012/us-east-1
```

### Para Desplegar Infraestructura

```bash
# 1. Generar código CDK (desde tu configuración YAML)
python -c "
from cdk_templates.config_loader import ConfigurationLoader
from cdk_templates.template_generator import TemplateGenerator
import os

loader = ConfigurationLoader()
config = loader.load_config(['mi-infraestructura.yaml'])

generator = TemplateGenerator()
result = generator.generate(config, environment='dev')

output_dir = 'cdk-output'
os.makedirs(output_dir, exist_ok=True)

for file_path, content in result.generated_files.items():
    full_path = os.path.join(output_dir, file_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w') as f:
        f.write(content)
    print(f'Creado: {full_path}')
"

# 2. Navegar al directorio de salida
cd cdk-output

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Verificar el código generado
cdk synth

# 5. Ver qué se va a crear
cdk diff

# 6. Desplegar en AWS
cdk deploy --all
```

## 📚 Documentación Disponible

### Para Usuarios Nuevos
1. **INSTALACION.md** - Guía de instalación completa
2. **docs/AWS_CDK_SETUP.md** - Guía detallada de AWS CDK
3. **docs/GUIA_DE_INICIO.md** - Tutorial paso a paso

### Para Referencia Rápida
- **README.md** / **README.es.md** - Inicio rápido
- **install.sh** - Script automatizado con verificaciones

## 🔧 Verificación de Instalación

Después de seguir las instrucciones, verifica que todo esté instalado:

```bash
# Verificar Python
python3 --version  # Debe ser 3.8+

# Verificar Node.js
node --version     # Debe ser 14.x+

# Verificar npm
npm --version      # Debe ser 6.x+

# Verificar AWS CDK CLI
cdk --version      # Debe ser 2.x.x

# Verificar credenciales AWS
aws sts get-caller-identity

# Verificar bootstrap de CDK
aws cloudformation describe-stacks --stack-name CDKToolkit
```

## ⚠️ Problemas Comunes y Soluciones

### "cdk: command not found"
```bash
npm install -g aws-cdk
# Reinicia tu terminal
```

### "Unable to resolve AWS account"
```bash
aws configure
# Ingresa tus credenciales
```

### "This stack uses assets, so the toolkit stack must be deployed"
```bash
cdk bootstrap aws://ACCOUNT-ID/REGION
```

### Error de permisos al instalar CDK (macOS/Linux)
```bash
# Opción 1: Configurar npm para instalar sin sudo
mkdir ~/.npm-global
npm config set prefix '~/.npm-global'
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
npm install -g aws-cdk

# Opción 2: Usar sudo (menos recomendado)
sudo npm install -g aws-cdk
```

## 📖 Recursos Adicionales

- **Documentación Oficial AWS CDK**: https://docs.aws.amazon.com/cdk/
- **AWS CDK Workshop**: https://cdkworkshop.com/
- **Node.js**: https://nodejs.org/
- **AWS CLI**: https://aws.amazon.com/cli/

## ✅ Checklist de Instalación

Usa este checklist para asegurarte de que todo está configurado:

- [ ] Python 3.8+ instalado
- [ ] Node.js 14+ instalado
- [ ] npm 6+ instalado
- [ ] AWS CDK CLI 2.x instalado
- [ ] Credenciales AWS configuradas
- [ ] Bootstrap de CDK ejecutado
- [ ] Entorno virtual Python creado
- [ ] Dependencias del proyecto instaladas
- [ ] Tests ejecutados exitosamente

## 🎯 Próximos Pasos

1. Lee la [Guía de Inicio](docs/GUIA_DE_INICIO.md) completa
2. Prueba con los [ejemplos incluidos](examples/)
3. Crea tu primera configuración YAML
4. Genera y despliega tu infraestructura

---

**¿Necesitas ayuda?** Consulta [docs/AWS_CDK_SETUP.md](docs/AWS_CDK_SETUP.md) para una guía detallada o abre un issue en GitHub.

## 📝 Notas de Versión

**Versión**: 1.0.0  
**Fecha**: 2 de Marzo, 2026  
**Cambios**: Agregadas instrucciones completas de AWS CDK Toolkit

Todos los cambios han sido subidos a GitHub:
https://github.com/ajha63/cdk-aws-templates-system
