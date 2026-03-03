# ✅ Solución Completa: Cómo Usar AWS CDK con el Proyecto

## Problema Resuelto

El error `--app is required either in command-line, in cdk.json or in ~/.cdk.json` ocurre porque estabas intentando ejecutar comandos CDK directamente en el directorio del proyecto, pero primero necesitas **generar el código CDK** desde tu configuración YAML.

## Flujo de Trabajo Correcto

### 📋 Paso 1: Generar Código CDK

El proyecto CDK AWS Templates System NO es una aplicación CDK directamente. Es un **generador** que convierte configuraciones YAML en código CDK.

```bash
# Usar el script generador
python generar_cdk.py examples/ejemplo-basico.yaml dev

# O con otro archivo
python generar_cdk.py mi-configuracion.yaml dev
```

Este comando:
- ✅ Carga tu configuración YAML
- ✅ Valida la configuración
- ✅ Genera código CDK Python
- ✅ Crea archivos en `cdk-output/`

### 📋 Paso 2: Navegar al Directorio Generado

```bash
cd cdk-output
```

Ahora estás en una aplicación CDK real con:
- `app.py` - Punto de entrada de CDK
- `cdk.json` - Configuración de CDK
- `requirements.txt` - Dependencias
- `stacks/` - Definiciones de stacks

### 📋 Paso 3: Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 📋 Paso 4: Configurar Credenciales AWS

Antes de desplegar, necesitas credenciales válidas:

```bash
# Opción 1: AWS CLI
aws configure

# Opción 2: Variables de entorno
export AWS_ACCESS_KEY_ID=tu_access_key
export AWS_SECRET_ACCESS_KEY=tu_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

### 📋 Paso 5: Usar Comandos CDK

Ahora sí puedes usar comandos CDK:

```bash
# Sintetizar (generar CloudFormation)
cdk synth

# Ver diferencias
cdk diff

# Listar stacks
cdk list

# Desplegar
cdk deploy --all

# Destruir
cdk destroy --all
```

## Script Generador Creado

He creado `generar_cdk.py` que facilita todo el proceso:

```python
# Uso básico
python generar_cdk.py

# Con archivo específico
python generar_cdk.py examples/ejemplo-basico.yaml dev

# Con directorio de salida personalizado
python generar_cdk.py mi-config.yaml prod mi-output
```

### Características del Script

- ✅ Carga y valida configuración
- ✅ Genera código CDK
- ✅ Crea estructura de directorios
- ✅ Muestra instrucciones siguientes
- ✅ Manejo de errores claro

## Archivos Generados

Cuando ejecutas el generador, crea:

```
cdk-output/
├── app.py                    # Punto de entrada CDK
├── cdk.json                  # Configuración CDK
├── requirements.txt          # Dependencias Python
├── stacks/
│   ├── __init__.py
│   └── ejemplo_basico_stack.py  # Tu stack
└── docs/
    ├── architecture.md       # Documentación
    └── architecture.html     # Documentación HTML
```

## Ejemplo Completo de Uso

```bash
# 1. Desde el directorio raíz del proyecto
cd /Users/alvarohernandez/src/cdk_templates

# 2. Activar entorno virtual (si no está activado)
source venv/bin/activate

# 3. Generar código CDK
python generar_cdk.py examples/ejemplo-basico.yaml dev

# 4. Navegar al código generado
cd cdk-output

# 5. Instalar dependencias
pip install -r requirements.txt

# 6. Configurar AWS (si no está configurado)
aws configure

# 7. Sintetizar para verificar
cdk synth

# 8. Ver qué se va a crear
cdk diff

# 9. Desplegar en AWS
cdk deploy --all
```

## Advertencias Comunes (No son Errores)

### 1. Node.js v25.2.1 No Probado

```
This software has not been tested with node v25.2.1
```

**Solución**: Puedes ignorar esta advertencia o silenciarla:

```bash
export JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1
```

O instalar una versión LTS de Node.js (20.x, 22.x, o 24.x):

```bash
# macOS con Homebrew
brew install node@22

# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### 2. Credenciales AWS Expiradas

```
There are expired AWS credentials in your environment
```

**Solución**: Renovar credenciales:

```bash
aws configure
# O renovar token de sesión si usas credenciales temporales
```

### 3. Need to Perform AWS Calls

```
Need to perform AWS calls for account 123456789012, but no credentials have been configured
```

**Solución**: Configurar credenciales válidas (ver Paso 4 arriba)

## Comandos CDK Útiles

Una vez en el directorio `cdk-output/`:

```bash
# Ver ayuda
cdk --help

# Listar todos los stacks
cdk list

# Sintetizar un stack específico
cdk synth MiStack

# Ver diferencias antes de desplegar
cdk diff

# Desplegar con confirmación
cdk deploy

# Desplegar sin confirmación (CI/CD)
cdk deploy --all --require-approval never

# Ver metadata de un stack
cdk metadata

# Destruir recursos
cdk destroy --all

# Ver contexto
cdk context

# Limpiar contexto
cdk context --clear
```

## Bootstrap de CDK (Primera Vez)

Si es la primera vez que usas CDK en tu cuenta:

```bash
# Obtener Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Bootstrap
cdk bootstrap aws://${ACCOUNT_ID}/us-east-1

# O manualmente
cdk bootstrap aws://123456789012/us-east-1
```

## Estructura del Proyecto

```
cdk-aws-templates-system/          # Proyecto raíz
├── generar_cdk.py                  # ← Script generador (NUEVO)
├── examples/                       # Configuraciones de ejemplo
│   ├── ejemplo-basico.yaml
│   └── aplicacion-web-completa.yaml
├── cdk_templates/                  # Código del generador
│   ├── config_loader.py
│   ├── template_generator.py
│   └── ...
└── cdk-output/                     # ← Código CDK generado
    ├── app.py                      # Aplicación CDK
    ├── cdk.json                    # Configuración CDK
    └── stacks/                     # Stacks CDK
```

## Diferencia Clave

| Directorio | Propósito | Comandos CDK |
|------------|-----------|--------------|
| `cdk-aws-templates-system/` | Generador de código | ❌ No funciona |
| `cdk-output/` | Aplicación CDK | ✅ Funciona |

## Solución de Problemas

### Error: "command not found: cdk"

```bash
npm install -g aws-cdk
cdk --version
```

### Error: "--app is required"

Estás en el directorio equivocado. Debes estar en `cdk-output/`:

```bash
cd cdk-output
cdk synth
```

### Error: "No se encuentra app.py"

No has generado el código CDK:

```bash
cd ..  # Volver al directorio raíz
python generar_cdk.py examples/ejemplo-basico.yaml dev
cd cdk-output
```

### Error: "ModuleNotFoundError: No module named 'aws_cdk'"

No has instalado las dependencias:

```bash
pip install -r requirements.txt
```

## Mejores Prácticas

1. **Siempre genera código nuevo** cuando cambies tu configuración YAML
2. **Usa control de versiones** para tu configuración YAML
3. **No edites manualmente** el código en `cdk-output/` (se regenera)
4. **Ejecuta `cdk diff`** antes de `cdk deploy`
5. **Usa tags** para organizar recursos
6. **Documenta** tus configuraciones YAML

## Próximos Pasos

1. ✅ Configurar credenciales AWS válidas
2. ✅ Ejecutar `cdk bootstrap` (primera vez)
3. ✅ Generar código CDK con `generar_cdk.py`
4. ✅ Navegar a `cdk-output/`
5. ✅ Ejecutar `cdk synth` para verificar
6. ✅ Ejecutar `cdk deploy` para desplegar

## Recursos

- [Guía de Inicio](docs/GUIA_DE_INICIO.md)
- [Setup de AWS CDK](docs/AWS_CDK_SETUP.md)
- [Ejemplos](examples/)
- [Documentación AWS CDK](https://docs.aws.amazon.com/cdk/)

---

**¿Listo para desplegar?** Configura tus credenciales AWS y ejecuta:

```bash
python generar_cdk.py examples/ejemplo-basico.yaml dev
cd cdk-output
pip install -r requirements.txt
cdk deploy --all
```
