# ✅ AWS CDK CLI Instalado Correctamente

## Estado Actual

### ✅ Instalado Correctamente
- **Node.js**: v25.2.1 ✓
- **npm**: 11.8.0 ✓
- **AWS CDK CLI**: 2.1108.0 ✓

### ⚠️ Requiere Atención
- **Credenciales AWS**: Token expirado

## Próximos Pasos

### 1. Renovar Credenciales de AWS

Tus credenciales de AWS están expiradas. Necesitas renovarlas:

```bash
# Opción 1: Reconfigurar con AWS CLI
aws configure

# Te pedirá:
# - AWS Access Key ID: [tu access key]
# - AWS Secret Access Key: [tu secret key]
# - Default region name: [por ejemplo: us-east-1]
# - Default output format: [json]
```

### 2. Verificar Credenciales

Después de configurar, verifica que funcionen:

```bash
aws sts get-caller-identity

# Deberías ver algo como:
# {
#     "UserId": "AIDAXXXXXXXXXXXXXXXXX",
#     "Account": "123456789012",
#     "Arn": "arn:aws:iam::123456789012:user/tu-usuario"
# }
```

### 3. Hacer Bootstrap de CDK

Una vez que tus credenciales funcionen, ejecuta el bootstrap:

```bash
# Obtener tu Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Obtener tu región por defecto
REGION=$(aws configure get region)

# Hacer bootstrap
cdk bootstrap aws://${ACCOUNT_ID}/${REGION}

# O especificar manualmente:
cdk bootstrap aws://123456789012/us-east-1
```

## Comandos Útiles de CDK

Ahora que CDK está instalado, estos son los comandos principales:

```bash
# Ver versión
cdk --version

# Ver ayuda
cdk --help

# Listar stacks en una aplicación CDK
cdk list

# Sintetizar (generar CloudFormation)
cdk synth

# Ver diferencias antes de desplegar
cdk diff

# Desplegar
cdk deploy

# Destruir recursos
cdk destroy
```

## Solución de Problemas

### Si las credenciales siguen expiradas

Si estás usando credenciales temporales (como AWS SSO o roles asumidos), necesitas:

1. **AWS SSO**:
   ```bash
   aws sso login --profile tu-perfil
   export AWS_PROFILE=tu-perfil
   ```

2. **Credenciales Temporales**:
   ```bash
   # Renovar el token de sesión
   aws sts get-session-token
   ```

3. **Credenciales Permanentes**:
   ```bash
   # Usar access keys permanentes
   aws configure
   # Ingresa tus access keys permanentes
   ```

### Verificar configuración de AWS

```bash
# Ver configuración actual
aws configure list

# Ver todas las configuraciones
cat ~/.aws/credentials
cat ~/.aws/config
```

## Integración con el Proyecto

Una vez que tengas las credenciales configuradas, puedes:

### 1. Generar Código CDK

```python
from cdk_templates.config_loader import ConfigurationLoader
from cdk_templates.template_generator import TemplateGenerator
import os

loader = ConfigurationLoader()
config = loader.load_config(['examples/ejemplo-basico.yaml'])

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
```

### 2. Desplegar en AWS

```bash
cd cdk-output
pip install -r requirements.txt
cdk synth
cdk diff
cdk deploy --all
```

## Checklist de Verificación

- [x] Node.js instalado (v25.2.1)
- [x] npm instalado (11.8.0)
- [x] AWS CDK CLI instalado (2.1108.0)
- [ ] Credenciales AWS configuradas y válidas
- [ ] Bootstrap de CDK ejecutado
- [ ] Listo para desplegar

## Recursos

- [Documentación AWS CDK](https://docs.aws.amazon.com/cdk/)
- [Configurar Credenciales AWS](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)
- [Guía de Inicio del Proyecto](docs/GUIA_DE_INICIO.md)
- [Setup Completo de AWS CDK](docs/AWS_CDK_SETUP.md)

---

**Siguiente paso**: Configura tus credenciales de AWS con `aws configure` y luego ejecuta `cdk bootstrap`.
