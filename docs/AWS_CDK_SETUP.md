# Configuración de AWS CDK Toolkit

Esta guía te ayudará a instalar y configurar AWS CDK CLI para usar con el CDK AWS Templates System.

## ¿Qué es AWS CDK?

AWS Cloud Development Kit (CDK) es un framework de desarrollo de software para definir infraestructura de nube usando lenguajes de programación familiares. El CDK AWS Templates System genera código CDK Python que luego se despliega usando el AWS CDK CLI.

## Requisitos Previos

### 1. Node.js y npm

AWS CDK CLI está escrito en TypeScript y se distribuye a través de npm (Node Package Manager).

#### Verificar si está instalado

```bash
node --version  # Debe ser 14.x o superior
npm --version   # Debe ser 6.x o superior
```

#### Instalar Node.js

**macOS (con Homebrew):**
```bash
brew install node
```

**Ubuntu/Debian:**
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

**Windows:**
- Descarga el instalador desde: https://nodejs.org/
- Ejecuta el instalador y sigue las instrucciones
- Reinicia tu terminal después de la instalación

**Verificar instalación:**
```bash
node --version
npm --version
```

### 2. AWS CLI (Opcional pero Recomendado)

AWS CLI facilita la configuración de credenciales.

#### Instalar AWS CLI

**macOS:**
```bash
brew install awscli
```

**Ubuntu/Debian:**
```bash
sudo apt-get install awscli
```

**Windows:**
- Descarga desde: https://aws.amazon.com/cli/
- Ejecuta el instalador MSI

**Verificar instalación:**
```bash
aws --version
```

## Instalación de AWS CDK CLI

### Instalación Global (Recomendado)

```bash
# Instalar AWS CDK CLI globalmente
npm install -g aws-cdk

# Verificar instalación
cdk --version
```

Deberías ver algo como: `2.x.x (build xxxxxx)`

### Solución de Problemas de Instalación

#### Error de Permisos en macOS/Linux

Si obtienes un error de permisos:

```bash
# Opción 1: Usar sudo (no recomendado)
sudo npm install -g aws-cdk

# Opción 2: Configurar npm para instalar globalmente sin sudo (recomendado)
mkdir ~/.npm-global
npm config set prefix '~/.npm-global'
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
npm install -g aws-cdk
```

#### Error en Windows

Si obtienes errores en Windows, ejecuta PowerShell como Administrador:

```powershell
npm install -g aws-cdk
```

## Configuración de Credenciales AWS

AWS CDK necesita credenciales para acceder a tu cuenta de AWS.

### Opción 1: Usar AWS CLI (Recomendado)

```bash
aws configure
```

Te pedirá:
- **AWS Access Key ID**: Tu access key
- **AWS Secret Access Key**: Tu secret key
- **Default region name**: Por ejemplo, `us-east-1`
- **Default output format**: Puedes dejar en blanco o usar `json`

### Opción 2: Variables de Entorno

```bash
# Linux/macOS
export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
export AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
export AWS_DEFAULT_REGION=us-east-1

# Windows PowerShell
$env:AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
$env:AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
$env:AWS_DEFAULT_REGION="us-east-1"
```

### Opción 3: Archivo de Credenciales

Crea o edita `~/.aws/credentials`:

```ini
[default]
aws_access_key_id = AKIAIOSFODNN7EXAMPLE
aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

Y `~/.aws/config`:

```ini
[default]
region = us-east-1
output = json
```

### Verificar Credenciales

```bash
# Con AWS CLI
aws sts get-caller-identity

# Deberías ver tu Account ID, User ID y ARN
```

## Bootstrap del Entorno CDK

Antes de desplegar tu primer stack CDK, necesitas hacer "bootstrap" de tu entorno AWS.

### ¿Qué hace el Bootstrap?

El bootstrap crea recursos en tu cuenta de AWS necesarios para CDK:
- Un bucket S3 para almacenar assets (archivos, imágenes Docker, etc.)
- Roles IAM para el despliegue
- Otros recursos de infraestructura

### Ejecutar Bootstrap

```bash
# Bootstrap para una región específica
cdk bootstrap aws://ACCOUNT-ID/REGION

# Ejemplo:
cdk bootstrap aws://123456789012/us-east-1
```

Para obtener tu Account ID:

```bash
aws sts get-caller-identity --query Account --output text
```

### Bootstrap para Múltiples Regiones

Si vas a desplegar en múltiples regiones:

```bash
cdk bootstrap aws://123456789012/us-east-1
cdk bootstrap aws://123456789012/us-west-2
cdk bootstrap aws://123456789012/eu-west-1
```

### Verificar Bootstrap

```bash
# Listar stacks de CloudFormation
aws cloudformation list-stacks --query "StackSummaries[?StackName=='CDKToolkit'].StackName"

# Deberías ver: ["CDKToolkit"]
```

## Comandos Básicos de CDK

Una vez instalado y configurado, estos son los comandos más comunes:

### Sintetizar (Generar CloudFormation)

```bash
cdk synth

# Genera el template CloudFormation sin desplegarlo
# Útil para verificar qué se va a crear
```

### Ver Diferencias (Diff)

```bash
cdk diff

# Muestra qué recursos se crearán, modificarán o eliminarán
# Ejecuta esto antes de deploy para ver los cambios
```

### Desplegar

```bash
# Desplegar todos los stacks
cdk deploy --all

# Desplegar un stack específico
cdk deploy MyStack

# Desplegar sin confirmación (útil para CI/CD)
cdk deploy --all --require-approval never
```

### Listar Stacks

```bash
cdk list

# Muestra todos los stacks en tu aplicación CDK
```

### Destruir Recursos

```bash
# Destruir todos los stacks
cdk destroy --all

# Destruir un stack específico
cdk destroy MyStack

# Destruir sin confirmación
cdk destroy --all --force
```

### Ver Metadata

```bash
# Ver información sobre un stack
cdk metadata MyStack

# Ver el contexto de CDK
cdk context
```

## Integración con CDK AWS Templates System

### Flujo de Trabajo Completo

1. **Crear configuración YAML:**
   ```yaml
   # mi-infraestructura.yaml
   version: '1.0'
   metadata:
     project: mi-proyecto
   # ... resto de la configuración
   ```

2. **Generar código CDK:**
   ```python
   from cdk_templates.config_loader import ConfigurationLoader
   from cdk_templates.template_generator import TemplateGenerator
   
   loader = ConfigurationLoader()
   config = loader.load_config(['mi-infraestructura.yaml'])
   
   generator = TemplateGenerator()
   result = generator.generate(config, environment='dev')
   
   # Guardar en directorio cdk-output/
   ```

3. **Navegar al directorio de salida:**
   ```bash
   cd cdk-output
   ```

4. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Sintetizar y verificar:**
   ```bash
   cdk synth
   cdk diff
   ```

6. **Desplegar:**
   ```bash
   cdk deploy --all
   ```

## Solución de Problemas Comunes

### Error: "cdk: command not found"

**Causa**: CDK CLI no está instalado o no está en el PATH.

**Solución**:
```bash
npm install -g aws-cdk
# Reinicia tu terminal
cdk --version
```

### Error: "Unable to resolve AWS account to use"

**Causa**: Credenciales AWS no configuradas.

**Solución**:
```bash
aws configure
# O configura variables de entorno
```

### Error: "This stack uses assets, so the toolkit stack must be deployed"

**Causa**: No se ha ejecutado bootstrap.

**Solución**:
```bash
cdk bootstrap aws://ACCOUNT-ID/REGION
```

### Error: "Need to perform AWS calls for account XXX, but no credentials found"

**Causa**: Credenciales inválidas o expiradas.

**Solución**:
```bash
# Verificar credenciales
aws sts get-caller-identity

# Reconfigurar si es necesario
aws configure
```

### Error: "Stack XXX already exists"

**Causa**: Intentando crear un stack que ya existe.

**Solución**:
```bash
# Ver el stack existente
aws cloudformation describe-stacks --stack-name XXX

# Actualizar en lugar de crear
cdk deploy XXX

# O destruir y recrear
cdk destroy XXX
cdk deploy XXX
```

### Error de Permisos IAM

**Causa**: Tu usuario IAM no tiene permisos suficientes.

**Solución**: Asegúrate de que tu usuario tenga los permisos necesarios:
- CloudFormation: Full access
- IAM: Permisos para crear roles
- Servicios específicos: EC2, RDS, S3, etc.

Política mínima recomendada para desarrollo:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:*",
        "s3:*",
        "iam:*",
        "ec2:*",
        "rds:*",
        "logs:*"
      ],
      "Resource": "*"
    }
  ]
}
```

## Mejores Prácticas

### 1. Usar Perfiles de AWS

Si trabajas con múltiples cuentas:

```bash
# Configurar perfiles
aws configure --profile dev
aws configure --profile prod

# Usar con CDK
export AWS_PROFILE=dev
cdk deploy

# O especificar en el comando
AWS_PROFILE=prod cdk deploy
```

### 2. Usar Variables de Entorno para Configuración

```bash
# Configurar región
export AWS_REGION=us-east-1

# Configurar account ID
export CDK_DEFAULT_ACCOUNT=123456789012
export CDK_DEFAULT_REGION=us-east-1
```

### 3. Revisar Cambios Antes de Desplegar

```bash
# Siempre ejecuta diff antes de deploy
cdk diff
cdk deploy
```

### 4. Usar Tags para Organización

Los tags se aplican automáticamente con CDK AWS Templates System, pero puedes agregar más:

```bash
cdk deploy --tags Environment=dev --tags CostCenter=engineering
```

### 5. Limpiar Recursos No Usados

```bash
# Destruir stacks que ya no necesitas
cdk destroy --all

# Limpiar assets antiguos del bucket de CDK
aws s3 rm s3://cdk-XXXXX-assets-ACCOUNT-REGION --recursive
```

## Recursos Adicionales

- [Documentación Oficial de AWS CDK](https://docs.aws.amazon.com/cdk/)
- [AWS CDK Workshop](https://cdkworkshop.com/)
- [AWS CDK Examples](https://github.com/aws-samples/aws-cdk-examples)
- [CDK API Reference](https://docs.aws.amazon.com/cdk/api/v2/)
- [Guía de Inicio del Sistema](GUIA_DE_INICIO.md)

## Soporte

Si encuentras problemas:

1. Verifica que todas las herramientas estén instaladas correctamente
2. Revisa los logs de error completos
3. Consulta la documentación oficial de AWS CDK
4. Abre un issue en el repositorio del proyecto

---

**¿Listo para empezar?** Continúa con la [Guía de Inicio](GUIA_DE_INICIO.md) para crear tu primera infraestructura.
