# Sazón Escolar 

**Sistema web para la administración de una cooperativa escolar.**

Sazón Escolar es una aplicación web creada para facilitar la compra de alimentos y bebidas dentro de una escuela. Permite que los alumnos consulten el menú y realicen pedidos, que los cocineros administren su preparación y que los administradores supervisen el funcionamiento del sistema.

## 1. Funcionalidades principales

- Registro e inicio de sesión.
- Tres tipos de usuarios: administrador, cocinero y alumno.
- Consulta del menú de alimentos, bebidas y postres.
- Creación y cancelación de pedidos.
- Seguimiento del estado de los pedidos.
- Administración de productos: agregar, consultar, modificar y eliminar.
- Administración de usuarios y roles.
- Registro de actividades mediante SQLite.
- Almacenamiento de usuarios, productos y pedidos mediante MongoDB.
- Diseño adaptable a computadoras, tabletas y teléfonos.
- Lectura de voz en español para anunciar páginas, botones, enlaces, controles y mensajes del sistema.

## 2. Tecnologías utilizadas

| Tecnología | Uso |
|---|---|
| Python | Lenguaje principal |
| Flask | Desarrollo del servidor web |
| HTML5 | Estructura de las páginas |
| CSS3 | Diseño y adaptación a dispositivos |
| JavaScript | Interactividad y lectura de voz |
| MongoDB | Almacenamiento principal de información |
| SQLite | Registro de actividades |
| Flask-Login | Administración de sesiones |
| Flask-WTF | Protección de formularios |

## 3. Requisitos para instalar el proyecto

Antes de comenzar, se necesita:

- Python 3.10 o una versión posterior.
- Visual Studio Code.
- Una cuenta de MongoDB Atlas.
- Conexión a Internet para instalar las dependencias y conectar con MongoDB.

Descarga Python desde:
https://www.python.org/downloads/

Crea una cuenta de MongoDB Atlas:
https://www.mongodb.com/cloud/atlas

## 4. Instalación en Windows

Abre la carpeta del proyecto en Visual Studio Code.

Abre una terminal desde **Terminal → New Terminal**.

Comprueba que Python esté instalado:

```powershell
py --version
```

Crea el entorno virtual:

```powershell
py -m venv .venv
```

Actívalo:

```powershell
.venv\Scripts\Activate.ps1
```

Instala las dependencias:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Si PowerShell no permite activar el entorno virtual, ejecuta:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Después vuelve a ejecutar:

```powershell
.venv\Scripts\Activate.ps1
```
## 5. Configuración de MongoDB

MongoDB almacena la información principal de la aplicación.

Para configurarlo:

1. Entra a MongoDB Atlas.
2. Crea un proyecto y un clúster.
3. En Database Access crea un usuario de base de datos.
4. En Network Access autoriza la conexión de tu computadora.
5. En Database selecciona Connect.
6. Selecciona Drivers y copia la cadena de conexión para Python.

En la carpeta principal del proyecto crea un archivo llamado `.env`, al mismo nivel que `app.py`.

Escribe dentro:

```env
MONGO_URI=PEGA_AQUI_TU_CADENA_DE_CONEXION
MONGO_DB=sazon_escolar
SECRET_KEY=escribe_una_clave_privada_y_segura
PORT=5000
FLASK_DEBUG=1
```

Reemplaza el texto de `MONGO_URI` por la cadena real que te proporciona MongoDB Atlas.


## 6. Ejecutar Sazón Escolar

Una vez instalado todo y configurado MongoDB, ejecuta:

```powershell
python app.py
```

Abre el navegador y entra a:

http://127.0.0.1:5000/

Para detener el servidor, regresa a la terminal y presiona `Ctrl + C`.

La terminal debe permanecer abierta mientras estés utilizando la aplicación.

## 7. Cuentas de demostración

Cuando la base de datos de usuarios está vacía, el sistema crea estas cuentas de demostración:

CUENTAS DE DEMOSTRACION
=======================

Administrador:
Usuario: administrador
Contraseña: Admin123!

Cocinero:
Usuario: cocinero
Contraseña: Cocina123!

Alumno:
Usuario: alumno
Contraseña: Alumno123!


Estas cuentas sirven para probar los diferentes tipos de acceso.

El registro de nuevos usuarios permite crear cuentas de alumnos.

## 8. Uso de las bases de datos

### MongoDB

Se utiliza como base de datos principal para guardar:

- Usuarios y contraseñas protegidas.
- Productos del menú.
- Pedidos de los alumnos.
- Cantidades, precios y estados de los pedidos.

### SQLite

Se utiliza para guardar una bitácora de actividades del sistema.

El archivo de la base de datos se crea automáticamente dentro de la carpeta `instance`.

Esto permite demostrar el uso de dos tipos de bases de datos en el mismo proyecto.


## 9. Lectura de voz

Sazón Escolar incorpora una función de accesibilidad mediante la síntesis de voz del navegador.

Para utilizarla:

1. Abre la aplicación.
2. Activa el botón de lectura de voz.
3. Navega por los botones, enlaces y controles.
4. La aplicación anunciará las acciones y mensajes que reconoce.
5. Puedes desactivar la lectura cuando lo desees.

La voz depende del navegador y de las voces instaladas en el dispositivo.

## 10. Estructura del proyecto

```text
sazon_flask_mongo/
│
├── app.py
├── requirements.txt
├── README.md
├── .env
├── .gitignore
├── integrantes.txt
│
├── templates/
│   ├── plantilla_base.html
│   ├── inicio.html
│   ├── acceso.html
│   ├── panel_alumno.html
│   ├── panel_personal.html
│   └── error.html
│
├── static/
│   ├── styles.css
│   └── app.js
│
├── instance/
│   └── sazon_escolar.sqlite3
│
│
└── Docs/
    ├── Sazon_Escolar.docx
    ├── Sazon_Escolar.pdf
    └── SAZÓN ESCOLAR.pptx
```

## 11. Solución de problemas

**Error: `ModuleNotFoundError`**

Activa el entorno virtual e instala nuevamente las dependencias:

```powershell
pip install -r requirements.txt
```

**Error: `MONGO_URI no está configurada`**

Comprueba que el archivo `.env` exista y esté en la misma carpeta que `app.py`.

**Error: `DNS query name does not exist`**

Revisa que la dirección de MongoDB esté copiada correctamente desde Atlas. No dejes los datos de ejemplo de la cadena de conexión.

**Error: `Authentication failed`**

Comprueba el usuario y contraseña creados en Database Access de MongoDB Atlas.

**La aplicación no abre**

Comprueba que el servidor esté ejecutándose y que la terminal no se haya cerrado.

**La lectura de voz no funciona**

Activa la lectura desde el botón de la aplicación, revisa el volumen y comprueba que el navegador tenga una voz
disponible.
