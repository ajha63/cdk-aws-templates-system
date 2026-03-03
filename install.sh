#!/bin/bash

# Script de instalación rápida para CDK AWS Templates System
# Uso: ./install.sh

set -e

echo "=========================================="
echo "  CDK AWS Templates System - Instalación"
echo "=========================================="
echo ""

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Verificar Python
print_info "Verificando Python..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 no está instalado"
    echo "Por favor instala Python 3.8 o superior"
    exit 1
fi

python_version=$(python3 --version | cut -d' ' -f2)
print_success "Python $python_version encontrado"

# Verificar pip
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 no está instalado"
    echo "Por favor instala pip3"
    exit 1
fi

print_success "pip3 encontrado"

# Verificar Node.js
print_info "Verificando Node.js..."
if ! command -v node &> /dev/null; then
    print_warning "Node.js no está instalado"
    print_info "Node.js es necesario para AWS CDK CLI"
    echo ""
    echo "Para instalar Node.js:"
    echo "  macOS:         brew install node"
    echo "  Ubuntu/Debian: curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash - && sudo apt-get install -y nodejs"
    echo "  Windows:       Descarga desde https://nodejs.org/"
    echo ""
else
    node_version=$(node --version)
    print_success "Node.js $node_version encontrado"
fi

# Verificar npm
if command -v npm &> /dev/null; then
    npm_version=$(npm --version)
    print_success "npm $npm_version encontrado"
fi

# Verificar AWS CDK CLI
print_info "Verificando AWS CDK CLI..."
if ! command -v cdk &> /dev/null; then
    print_warning "AWS CDK CLI no está instalado"
    print_info "AWS CDK CLI es necesario para desplegar stacks en AWS"
    echo ""
    if command -v npm &> /dev/null; then
        read -p "¿Deseas instalar AWS CDK CLI ahora? (S/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            print_info "Instalando AWS CDK CLI..."
            npm install -g aws-cdk
            if command -v cdk &> /dev/null; then
                cdk_version=$(cdk --version)
                print_success "AWS CDK CLI $cdk_version instalado"
            else
                print_warning "No se pudo instalar AWS CDK CLI automáticamente"
                echo "Intenta manualmente: npm install -g aws-cdk"
            fi
        fi
    else
        echo "Para instalar AWS CDK CLI:"
        echo "  npm install -g aws-cdk"
        echo ""
    fi
else
    cdk_version=$(cdk --version)
    print_success "AWS CDK CLI $cdk_version encontrado"
fi

# Verificar AWS credentials
print_info "Verificando credenciales de AWS..."
if [ -f "$HOME/.aws/credentials" ] || [ ! -z "$AWS_ACCESS_KEY_ID" ]; then
    print_success "Credenciales de AWS configuradas"
else
    print_warning "No se encontraron credenciales de AWS"
    print_info "Para configurar AWS:"
    echo "  aws configure"
    echo "  O configura variables de entorno:"
    echo "    export AWS_ACCESS_KEY_ID=tu_access_key"
    echo "    export AWS_SECRET_ACCESS_KEY=tu_secret_key"
    echo "    export AWS_DEFAULT_REGION=us-east-1"
    echo ""
fi

# Crear entorno virtual
print_info "Creando entorno virtual..."
if [ -d "venv" ]; then
    print_warning "El entorno virtual ya existe"
    read -p "¿Deseas recrearlo? (s/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        rm -rf venv
        python3 -m venv venv
        print_success "Entorno virtual recreado"
    else
        print_info "Usando entorno virtual existente"
    fi
else
    python3 -m venv venv
    print_success "Entorno virtual creado"
fi

# Activar entorno virtual
print_info "Activando entorno virtual..."
source venv/bin/activate
print_success "Entorno virtual activado"

# Actualizar pip
print_info "Actualizando pip..."
pip install --upgrade pip > /dev/null 2>&1
print_success "pip actualizado"

# Instalar dependencias
print_info "Instalando dependencias..."
echo ""

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    print_success "Dependencias instaladas"
else
    print_error "No se encontró requirements.txt"
    exit 1
fi

# Instalar dependencias de desarrollo (opcional)
echo ""
read -p "¿Deseas instalar dependencias de desarrollo? (S/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    if [ -f "requirements-dev.txt" ]; then
        print_info "Instalando dependencias de desarrollo..."
        pip install -r requirements-dev.txt
        print_success "Dependencias de desarrollo instaladas"
    fi
fi

# Instalar el paquete en modo desarrollo
echo ""
print_info "Instalando paquete en modo desarrollo..."
pip install -e .
print_success "Paquete instalado"

# Verificar instalación
echo ""
print_info "Verificando instalación..."
if python -c "import cdk_templates" 2>/dev/null; then
    print_success "Módulo cdk_templates importado correctamente"
else
    print_warning "No se pudo importar el módulo cdk_templates"
fi

# Ejecutar tests
echo ""
read -p "¿Deseas ejecutar los tests? (S/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    print_info "Ejecutando tests..."
    echo ""
    pytest tests/ -v --tb=short || true
fi

# Resumen
echo ""
echo "=========================================="
echo "  Instalación Completada"
echo "=========================================="
echo ""
print_success "El proyecto está listo para usar"
echo ""
print_info "Para activar el entorno virtual en el futuro:"
echo "  source venv/bin/activate"
echo ""
print_info "Para ejecutar el script de inicio rápido:"
echo "  python quickstart.py"
echo ""
print_info "Para ejecutar tests:"
echo "  pytest tests/ -v"
echo ""
print_info "Para desplegar en AWS (después de generar el código):"
echo "  cd output_directory"
echo "  cdk deploy"
echo ""
print_info "Para hacer bootstrap de CDK (primera vez):"
echo "  cdk bootstrap aws://ACCOUNT-ID/REGION"
echo ""
print_info "Para generar código CDK desde una configuración:"
echo "  python -c \"
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
\""
echo ""
print_success "¡Feliz despliegue! 🚀"
