# PetroFlow v3.0.0 - Notas de Lanzamiento

**Fecha:** 2 de Junio de 2026  
**Versión:** 3.0.0 - Lista para Producción  
**Cambios Principales:** Sin Docker + Desarrollo Local + Despliegue Cloud

---

## ✅ Lo Nuevo

### 1. Sin Docker - Desarrollo Local Simplificado
- **Eliminado:** Docker y Docker Compose
- **Beneficio:** Ya no necesitas Docker Desktop instalado en Windows
- **Cómo funciona:** Backend (Python) + Frontend (Node.js) corren directamente
- **Ubicación:** Cambios archivados en `.archived_docker/` para referencia

### 2. Lanzamiento Local
Ejecuta ambos servicios con un solo comando:
```batch
.\start_local_dev.bat
```

**Esto inicia:**
- Backend en: `http://localhost:8000`
  - Health check: `http://localhost:8000/health`
  - API Docs: `http://localhost:8000/docs`
- Frontend en: `http://localhost:3000`

**Requisitos:**
- Python 3.14+ instalado
- Node.js v26+ instalado
- npm 11+

### 3. Despliegue Cloud Multiplatforma
Ahora puedes desplegar en:

#### Heroku (5 minutos)
```bash
heroku create petroflow-v3
git push heroku main
```

#### AWS (15 minutos, ~$5-15/mes)
```bash
sam build
sam deploy --guided
```

#### Google Cloud Run (10 minutos, gratis con límites)
```bash
gcloud run deploy petroflow-backend --source .
```

**Ver:** `DEPLOYMENT_GUIDE.md` para instrucciones completas

### 4. Documentación Mejorada
- `README.md` - Guía rápida y diagrama de arquitectura
- `DEPLOYMENT_GUIDE.md` - Paso a paso para cada plataforma
- `.env.example` - Todas las variables de configuración
- `CHANGELOG.md` - Historial de cambios detallado

---

## 🔧 Configuración

### Variables de Entorno
Copia `.env.example` a `.env` y personaliza:
```bash
cp .env.example .env
```

### Base de Datos Localista (desarrollo)
- SQLite: `./storage/petroflow.db`
- Se crea automáticamente

### Base de Datos Cloud (producción)
- PostgreSQL (Heroku/AWS/GCP)
- Conexión automática vía `DATABASE_URL`

---

## 📊 Requisitos del Sistema

### Para Desarrollo Local
- **Windows 10/11** (probado ✅)
- **Python 3.14+**
- **Node.js v26+**
- **npm 11+**
- **Git**
- ~500MB disco libre
- *NO requiere Docker Desktop*

### Para Producción Cloud
- Cuenta en Heroku, AWS, o Google Cloud
- Variables de entorno configuradas
- PostgreSQL (automático en cloud)

---

## ✨ Cambios Principales

| Aspecto | v2.0 | v3.0 |
|---------|------|------|
| Docker | ✅ Requerido | ❌ Eliminado |
| Desarrollo Local | Lento (containers) | Rápido (directo) |
| Cloud Support | Limitado | Heroku + AWS + GCP |
| Documentación | Básica | Completa |
| Dependencias | Pesadas (Docker) | Ligeras (pip + npm) |

---

## 🚀 Inicio Rápido

### 1. Clonar y Configurar
```bash
cd C:\Users\Userr\OneDrive\Documentos\Software\PetroFlow_Design
```

### 2. Crear Variables de Entorno
```bash
copy .env.example .env
# Editar .env si es necesario
```

### 3. Iniciar Servicios
```bash
.\start_local_dev.bat
```

Verás dos ventanas:
- **Ventana 1 (Backend):** `Backend running on http://localhost:8000`
- **Ventana 2 (Frontend):** `Compiled successfully!`

### 4. Acceder a la Aplicación
- Interfaz: `http://localhost:3000`
- API Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

---

## 📝 Migrando desde v2.0

Si estás usando v2.0 con Docker:

1. **Respalda tu base de datos**
   ```bash
   # Tus datos están en: ./storage/petroflow.db
   cp storage/petroflow.db storage/petroflow.db.backup
   ```

2. **Copia configuración**
   ```bash
   # Si tienes .env personalizado
   cp .env .env.backup
   ```

3. **Actualiza a v3.0**
   ```bash
   git fetch
   git checkout v3.0.0
   ```

4. **Instala dependencias**
   - Backend: Se instalan con `start_local_dev.bat`
   - Frontend: `npm install --legacy-peer-deps` (ya hecho)

5. **Prueba**
   ```bash
   .\start_local_dev.bat
   ```

---

## 🐛 Solución de Problemas

### "Module not found" en Backend
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate.bat
pip install -r requirements.txt
```

### Frontend no compila
```bash
cd frontend
npm install --legacy-peer-deps
npm start
```

### Puerto 3000 o 8000 en uso
- Detén otras aplicaciones usando esos puertos
- O edita `start_local_dev.bat` para usar otros puertos

---

## 📞 Soporte

- **Bug Report:** Crea un issue en GitHub
- **Documentación:** Ver `DEPLOYMENT_GUIDE.md`
- **Migración de Docker:** Ver `.archived_docker/README_DOCKER_REMOVAL.md`

---

## 🎯 Estado

- ✅ Código compilado y testeado
- ✅ Local development funcional
- ✅ Cloud deployment configurado
- ✅ Documentación completa
- ✅ Listo para producción

**Versión Recomendada:** 3.0.0  
**Próxima Revisión:** Cuando haya feedback de usuarios
