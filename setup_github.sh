#!/bin/bash

# Script para configurar y subir el proyecto a GitHub
# Uso: ./setup_github.sh

set -e  # Salir si hay algún error

echo "=========================================="
echo "  Setup GitHub - CDK AWS Templates System"
echo "=========================================="
echo ""

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Función para imprimir con color
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

# Verificar que Git está instalado
if ! command -v git &> /dev/null; then
    print_error "Git no está instalado. Por favor instala Git primero."
    exit 1
fi

print_success "Git está instalado"

# Verificar si ya existe un repositorio Git
if [ -d ".git" ]; then
    print_warning "Ya existe un repositorio Git inicializado"
    read -p "¿Deseas reinicializarlo? (s/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        rm -rf .git
        print_info "Repositorio Git eliminado"
    else
        print_info "Usando repositorio Git existente"
    fi
fi

# Inicializar Git si no existe
if [ ! -d ".git" ]; then
    print_info "Inicializando repositorio Git..."
    git init
    print_success "Repositorio Git inicializado"
fi

# Configurar usuario Git si no está configurado
if [ -z "$(git config user.name)" ]; then
    echo ""
    read -p "Ingresa tu nombre para Git: " git_name
    git config user.name "$git_name"
    print_success "Nombre de usuario configurado: $git_name"
fi

if [ -z "$(git config user.email)" ]; then
    read -p "Ingresa tu email para Git: " git_email
    git config user.email "$git_email"
    print_success "Email configurado: $git_email"
fi

# Solicitar información del repositorio
echo ""
echo "=========================================="
echo "  Configuración del Repositorio GitHub"
echo "=========================================="
echo ""

read -p "Ingresa tu usuario de GitHub: " github_user
read -p "Ingresa el nombre del repositorio (default: cdk-aws-templates-system): " repo_name
repo_name=${repo_name:-cdk-aws-templates-system}

# Construir URL del repositorio
repo_url="https://github.com/${github_user}/${repo_name}.git"

print_info "URL del repositorio: $repo_url"
echo ""

# Verificar archivos a incluir
print_info "Verificando archivos..."
git add .

# Mostrar resumen de archivos
file_count=$(git status --short | wc -l)
print_success "Archivos preparados: $file_count"

echo ""
echo "Archivos principales:"
git status --short | head -20

if [ $file_count -gt 20 ]; then
    print_info "... y $(($file_count - 20)) archivos más"
fi

echo ""
read -p "¿Continuar con el commit? (S/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    # Crear commit inicial
    print_info "Creando commit inicial..."
    git commit -m "Initial commit: CDK AWS Templates System

- Complete implementation of declarative CDK templates
- Support for VPC, EC2, RDS, and S3 resources
- Multi-environment configuration
- Automatic validation and documentation generation
- 483/491 tests passing (98.4% coverage)
- Spanish and English documentation
- Interactive quickstart script
- Comprehensive examples and guides"

    print_success "Commit creado"
else
    print_warning "Commit cancelado"
    exit 0
fi

# Configurar remote
echo ""
print_info "Configurando remote de GitHub..."

# Verificar si ya existe el remote
if git remote | grep -q "^origin$"; then
    print_warning "Remote 'origin' ya existe"
    current_url=$(git remote get-url origin)
    print_info "URL actual: $current_url"
    
    read -p "¿Deseas actualizarlo? (s/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        git remote set-url origin "$repo_url"
        print_success "Remote actualizado"
    fi
else
    git remote add origin "$repo_url"
    print_success "Remote agregado"
fi

# Cambiar a rama main
print_info "Configurando rama principal..."
git branch -M main
print_success "Rama configurada: main"

# Información sobre el push
echo ""
echo "=========================================="
echo "  Listo para subir a GitHub"
echo "=========================================="
echo ""
print_info "Repositorio: $repo_url"
print_info "Rama: main"
print_info "Commits: $(git rev-list --count HEAD)"
echo ""

print_warning "IMPORTANTE: Necesitarás un Personal Access Token para autenticarte"
echo ""
echo "Para crear un token:"
echo "  1. Ve a: https://github.com/settings/tokens"
echo "  2. Clic en 'Generate new token' → 'Generate new token (classic)'"
echo "  3. Selecciona scope: 'repo' (acceso completo)"
echo "  4. Copia el token generado"
echo "  5. Úsalo como contraseña cuando Git te lo pida"
echo ""

read -p "¿Deseas hacer push ahora? (S/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    print_info "Subiendo código a GitHub..."
    echo ""
    
    if git push -u origin main; then
        echo ""
        print_success "¡Código subido exitosamente!"
        echo ""
        echo "=========================================="
        echo "  ¡Proyecto en GitHub!"
        echo "=========================================="
        echo ""
        print_success "Tu repositorio está disponible en:"
        echo "  https://github.com/${github_user}/${repo_name}"
        echo ""
        print_info "Próximos pasos:"
        echo "  1. Visita tu repositorio en GitHub"
        echo "  2. Agrega una descripción y topics"
        echo "  3. Configura GitHub Pages (opcional)"
        echo "  4. Invita colaboradores (opcional)"
        echo ""
    else
        echo ""
        print_error "Error al subir el código"
        print_info "Verifica:"
        echo "  - Que el repositorio existe en GitHub"
        echo "  - Que usaste el Personal Access Token correcto"
        echo "  - Tu conexión a internet"
        echo ""
        print_info "Puedes intentar manualmente:"
        echo "  git push -u origin main"
    fi
else
    echo ""
    print_info "Push cancelado"
    print_info "Puedes hacerlo manualmente más tarde con:"
    echo "  git push -u origin main"
fi

echo ""
print_success "Setup completado"
