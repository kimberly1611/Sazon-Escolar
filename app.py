
import os
import math
import sqlite3

from pathlib import Path
from datetime import datetime, timezone
from functools import wraps
from contextlib import contextmanager

from bson import ObjectId
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from flask_wtf.csrf import CSRFProtect
from pymongo import MongoClient, DESCENDING
from pymongo.errors import PyMongoError, DuplicateKeyError
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix

load_dotenv()

# CONFIGURACIÓN GENERAL


app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

app.config['SECRET_KEY'] = os.getenv(
    'SECRET_KEY',
    'cambia-esta-clave-antes-de-publicar-sazon-escolar'
)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / 'instance'
INSTANCE_DIR.mkdir(exist_ok=True)

SQLITE_PATH = Path(
    os.getenv('SQLITE_PATH', str(INSTANCE_DIR / 'sazon_escolar.sqlite3'))
).expanduser()

SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)

csrf = CSRFProtect(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Inicia sesión para continuar.'
login_manager.login_message_category = 'info'


# CONEXIÓN CON MONGODB

MONGO_URI = os.getenv('MONGO_URI', '').strip()
DB_NAME = os.getenv('MONGO_DB', 'sazon_escolar')

client = None
db = None

if MONGO_URI:
    try:
        client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=5000
        )
        db = client[DB_NAME]
    except PyMongoError as exc:
        app.logger.error('Error al configurar MongoDB: %s', exc)

def mongo_required():
    """Comprueba que MongoDB esté configurado y disponible."""
    if db is None or client is None:
        flash(
            'MongoDB no está configurado. Revisa MONGO_URI en tu archivo .env.',
            'error'
        )
        return False

    try:
        client.admin.command('ping')
        return True
    except PyMongoError as exc:
        app.logger.error('Error de conexión con MongoDB: %s', exc)
        flash(
            'No se pudo conectar con MongoDB. Revisa tu conexión y el archivo .env.',
            'error'
        )
        return False

# CONEXIÓN Y ESTRUCTURA DE SQLITE

@contextmanager
def get_sqlite_connection():
    """Abre y cierra correctamente la conexión SQLite."""
    connection = sqlite3.connect(SQLITE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

def now_text():
    return datetime.now(timezone.utc).isoformat()

def init_sqlite():
    """Crea las tablas del sistema sin borrar datos existentes."""

    tables = [

        # 1. USUARIOS
        
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mongo_id TEXT NOT NULL UNIQUE,
            username TEXT NOT NULL,
            name TEXT NOT NULL,
            email TEXT DEFAULT '',
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TEXT,
            updated_at TEXT
        )
        """,

        # 2. CATEGORÍAS
        """
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
        """,

        # 3. PRODUCTOS
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mongo_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            category TEXT NOT NULL,
            price REAL NOT NULL DEFAULT 0,
            available INTEGER NOT NULL DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        )
        """,

        # 4. PEDIDOS
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mongo_id TEXT NOT NULL UNIQUE,
            user_mongo_id TEXT NOT NULL,
            status TEXT NOT NULL,
            note TEXT DEFAULT '',
            total REAL NOT NULL DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )
        """,

        # 5. PRODUCTOS DE LOS PEDIDOS
        """
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_mongo_id TEXT NOT NULL,
            product_mongo_id TEXT DEFAULT '',
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            subtotal REAL NOT NULL
        )
        """,

        # 6. INVENTARIO
        """
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_mongo_id TEXT NOT NULL UNIQUE,
            quantity INTEGER NOT NULL DEFAULT 0,
            minimum_quantity INTEGER NOT NULL DEFAULT 5,
            updated_at TEXT NOT NULL
        )
        """,

        # 7. NOTIFICACIONES
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_mongo_id TEXT DEFAULT '',
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """,

        # 8. MENÚS DIARIOS
        """
        CREATE TABLE IF NOT EXISTS daily_menus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            menu_date TEXT NOT NULL,
            product_mongo_id TEXT NOT NULL,
            available INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            UNIQUE(menu_date, product_mongo_id)
        )
        """,

        # 9. HISTORIAL DE INICIOS DE SESIÓN
        """
        CREATE TABLE IF NOT EXISTS login_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            successful INTEGER NOT NULL DEFAULT 1,
            details TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
        """,

        # 10. HISTORIAL DE ESTADOS DE PEDIDOS
        """
        CREATE TABLE IF NOT EXISTS order_status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_mongo_id TEXT NOT NULL,
            previous_status TEXT DEFAULT '',
            new_status TEXT NOT NULL,
            changed_by TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """,

        # 11. BITÁCORA DE ACCIONES
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    ]

    # CREAR TODAS LAS TABLAS

    with get_sqlite_connection() as connection:

        for statement in tables:
            connection.execute(statement)
        # Revisar las columnas existentes de login_history
        columnas_login = [
            columna["name"]
            for columna in connection.execute(
                "PRAGMA table_info(login_history)"
            ).fetchall()
        ]

        if "successful" not in columnas_login:
            connection.execute("""
                ALTER TABLE login_history
                ADD COLUMN successful INTEGER NOT NULL DEFAULT 1
            """)

        if "details" not in columnas_login:
            connection.execute("""
                ALTER TABLE login_history
                ADD COLUMN details TEXT DEFAULT ''
            """) 
            
        columnas_order_items = {
            columna["name"]
            for columna in connection.execute(
                "PRAGMA table_info(order_items)"
            ).fetchall()
        }

        if "order_mongo_id" not in columnas_order_items:
            connection.execute("""
                ALTER TABLE order_items
                ADD COLUMN order_mongo_id TEXT
            """)

        if "product_mongo_id" not in columnas_order_items:
            connection.execute("""
                ALTER TABLE order_items
                ADD COLUMN product_mongo_id TEXT DEFAULT ''
            """)
        

def log_action(username, action, details=''):
    """Registra acciones importantes en la bitácora."""
    try:
        with get_sqlite_connection() as connection:
            connection.execute(
                """
                INSERT INTO audit_logs
                (username, action, details, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    username or 'anónimo',
                    action,
                    str(details)[:500],
                    now_text()
                )
            )
    except sqlite3.Error as exc:
        app.logger.error('Error en la bitácora SQLite: %s', exc)

def save_user_sqlite(document):
    """Guarda o actualiza un usuario de MongoDB en SQLite."""
    if not document or not document.get('_id'):
        return

    mongo_id = str(document['_id'])
    username = document.get('username', '')

    with get_sqlite_connection() as connection:
        connection.execute(
            """
            DELETE FROM users
            WHERE username = ? AND mongo_id != ?
            """,
            (username, mongo_id)
        )

        connection.execute(
            """
            INSERT INTO users
            (mongo_id, username, name, email, password_hash, role, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(mongo_id) DO UPDATE SET
                username = excluded.username,
                name = excluded.name,
                email = excluded.email,
                password_hash = excluded.password_hash,
                role = excluded.role,
                updated_at = excluded.updated_at
            """,
            (
                mongo_id,
                username,
                document.get('name', ''),
                document.get('email', ''),
                document.get('password', ''),
                document.get('role', 'alumno'),
                str(document.get('created_at', now_text())),
                now_text()
            )
        )

def save_product_sqlite(document):
    """Guarda o actualiza un producto en SQLite."""
    if not document or not document.get('_id'):
        return

    category = document.get('category', 'comida')

    with get_sqlite_connection() as connection:
        connection.execute(
            """
            INSERT INTO categories (name, description, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(name) DO NOTHING
            """,
            (category, 'Categoría del menú escolar', now_text())
        )

        connection.execute(
            """
            INSERT INTO products
            (mongo_id, name, description, category, price, available, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(mongo_id) DO UPDATE SET
                name = excluded.name,
                description = excluded.description,
                category = excluded.category,
                price = excluded.price,
                available = excluded.available,
                updated_at = excluded.updated_at
            """,
            (
                str(document['_id']),
                document.get('name', ''),
                document.get('description', ''),
                category,
                float(document.get('price', 0)),
                1 if document.get('available', True) else 0,
                str(document.get('created_at', now_text())),
                now_text()
            )
        )


def save_order_sqlite(document):
    """Guarda un pedido y sus productos en SQLite."""

    if not document or not document.get('_id'):
        return

    order_mongo_id = str(document['_id'])
    lines = document.get('lines', [])

    with get_sqlite_connection() as connection:

        # 1. GUARDAR EL PEDIDO PRINCIPAL

        connection.execute(
            """
            INSERT INTO orders
            (
                mongo_id,
                user_mongo_id,
                status,
                note,
                total,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)

            ON CONFLICT(mongo_id) DO UPDATE SET
                user_mongo_id = excluded.user_mongo_id,
                status = excluded.status,
                note = excluded.note,
                total = excluded.total,
                updated_at = excluded.updated_at
            """,
            (
                order_mongo_id,
                str(document.get('user_id', '')),
                document.get('status', 'pendiente'),
                document.get('note', ''),
                float(document.get('total', 0)),
                str(document.get('created_at', now_text())),
                now_text()
            )
        )

        # Obtener el ID numérico del pedido en SQLite
        order_row = connection.execute(
            """
            SELECT id
            FROM orders
            WHERE mongo_id = ?
            """,
            (order_mongo_id,)
        ).fetchone()

        if not order_row:
            raise sqlite3.Error(
                'No se pudo obtener el ID del pedido en SQLite.'
            )

        sqlite_order_id = order_row['id']

        # 2. ELIMINAR ARTÍCULOS ANTERIORES

        connection.execute(
            """
            DELETE FROM order_items
            WHERE order_mongo_id = ?
            """,
            (order_mongo_id,)
        )

        # 3. GUARDAR LOS PRODUCTOS DEL PEDIDO

        for line in lines:

            connection.execute(
                """
                INSERT INTO order_items
                (
                    order_id,
                    order_mongo_id,
                    product_mongo_id,
                    product_name,
                    quantity,
                    unit_price,
                    subtotal
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sqlite_order_id,
                    order_mongo_id,
                    str(line.get('product_id', '')),
                    line.get('product_name', 'Producto'),
                    int(line.get('quantity', 1)),
                    float(line.get('price', 0)),
                    float(line.get('subtotal', 0))
                )
            )


def sync_mongo_to_sqlite():
    """Copia a SQLite los usuarios, productos y pedidos existentes."""
    if db is None:
        return

    for document in db.users.find({}):
        save_user_sqlite(document)

    for document in db.products.find({}):
        save_product_sqlite(document)

    for document in db.orders.find({}):
        save_order_sqlite(document)

init_sqlite()

# USUARIOS Y SEGURIDAD

class User(UserMixin):
    def __init__(self, document):
        self.document = document
        self.id = str(document['_id'])
        self.username = document.get('username', '')
        self.name = document.get('name') or self.username
        self.role = document.get('role', 'alumno')
        self.email = document.get('email', '')

def safe_object_id(value):
    """Convierte un identificador de MongoDB o devuelve error 404."""
    try:
        return ObjectId(str(value))
    except Exception:
        abort(404)

@login_manager.user_loader
def load_user(user_id):
    if db is None:
        return None

    try:
        doc = db.users.find_one({'_id': ObjectId(user_id)})
        return User(doc) if doc else None
    except Exception:
        return None

def roles_required(*roles):
    """Protege rutas según el rol del usuario."""
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator

# FILTROS Y DATOS DE DEMOSTRACIÓN

def money(value):
    try:
        return f"${float(value):,.2f}"
    except (ValueError, TypeError):
        return '$0.00'

app.jinja_env.filters['money'] = money

def ensure_seed_data():
    """Agrega usuarios y productos iniciales sin duplicarlos."""
    if db is None:
        return

    now = datetime.now(timezone.utc)

    if db.users.count_documents({}) == 0:
        db.users.insert_many([
            {
                'username': 'administrador',
                'name': 'Administración',
                'email': 'admin@sazon.local',
                'password': generate_password_hash('Admin123!'),
                'role': 'admin',
                'created_at': now
            },
            {
                'username': 'cocinero',
                'name': 'Equipo de cocina',
                'email': 'cocina@sazon.local',
                'password': generate_password_hash('Cocina123!'),
                'role': 'cocinero',
                'created_at': now
            },
            {
                'username': 'alumno',
                'name': 'Alumno de prueba',
                'email': 'alumno@sazon.local',
                'password': generate_password_hash('Alumno123!'),
                'role': 'alumno',
                'created_at': now
            }
        ])

    products = [
        ('Baguette de pollo', 'Pollo, lechuga fresca y aderezo de la casa.', 'comida', 38),
        ('Sincronizada', 'Tortilla doradita con queso derretido.', 'comida', 25),
        ('Mollete', 'Bolillo con frijoles, queso gratinado y pico de gallo.', 'comida', 28),
        ('Sándwich de jamón', 'Pan suave, jamón, queso, jitomate y lechuga.', 'comida', 30),
        ('Torta de milanesa', 'Milanesa, aguacate, jitomate y frijoles.', 'comida', 42),
        
    ]

    for name, description, category, price in products:
        db.products.update_one(
            {'name': name},
            {
                '$setOnInsert': {
                    'name': name,
                    'description': description,
                    'category': category,
                    'price': float(price),
                    'available': True,
                    'created_at': now
                }
            },
            upsert=True
        )

    try:
        db.users.create_index('username', unique=True)
        db.orders.create_index([('user_id', 1), ('created_at', -1)])
        db.products.create_index([('available', 1), ('category', 1)])
    except PyMongoError as exc:
        app.logger.warning('Error al crear índices: %s', exc)

@app.context_processor
def inject_globals():
    return {'brand_name': 'Sazón Escolar'}

# PÁGINA PRINCIPAL

@app.route('/')
def home():
    return render_template('inicio.html')

# REGISTRO DE ALUMNOS

@app.route('/registro', methods=['GET', 'POST'])
def register():
    if not mongo_required():
        return render_template('acceso.html', register=True)

    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if (
            not username
            or not name
            or len(username) > 40
            or len(name) > 100
            or len(password) < 8
        ):
            flash(
                'Completa los campos. La contraseña debe tener al menos 8 caracteres.',
                'error'
            )
        else:
            doc = {
                'username': username,
                'name': name,
                'email': email,
                'password': generate_password_hash(password),
                'role': 'alumno',
                'created_at': datetime.now(timezone.utc)
            }

            try:
                result = db.users.insert_one(doc)
                new_user = db.users.find_one({'_id': result.inserted_id})

                save_user_sqlite(new_user)
                login_user(User(new_user))

                log_action(
                    username,
                    'Registro de cuenta',
                    'Se creó una cuenta de alumno en MongoDB y SQLite.'
                )

                flash('¡Tu cuenta quedó lista!', 'success')
                return redirect(url_for('dashboard'))

            except DuplicateKeyError:
                flash('Ese nombre de usuario ya está registrado.', 'error')
            except (PyMongoError, sqlite3.Error) as exc:
                app.logger.error('Error durante el registro: %s', exc)
                flash('No se pudo crear tu cuenta. Inténtalo nuevamente.', 'error')

    return render_template('acceso.html', register=True)

# INICIO DE SESIÓN


@app.route('/iniciar-sesion', methods=['GET', 'POST'])
def login():
    if not mongo_required():
        return render_template('acceso.html', register=False)

    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')

        doc = db.users.find_one({'username': username})

        if doc and check_password_hash(doc.get('password', ''), password):
            save_user_sqlite(doc)
            login_user(User(doc))

            with get_sqlite_connection() as connection:
                connection.execute(
                    """
                    INSERT INTO login_history
                    (username, event, successful, details, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        username,
                        'inicio_sesion',
                        1,
                        'Inicio de sesión correcto.',
                        now_text()
                    )
                )

            log_action(
                username,
                'Inicio de sesión',
                'Autenticación correcta; usuario consultado en MongoDB.'
            )

            return redirect(url_for('dashboard'))

        with get_sqlite_connection() as connection:
            connection.execute(
                """
                INSERT INTO login_history
                (username, event, successful, details, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    username,
                    'intento_fallido',
                    0,
                    'Credenciales incorrectas.',
                    now_text()
                )
            )

        log_action(
            username,
            'Intento de inicio de sesión',
            'Credenciales incorrectas.'
        )

        flash('Usuario o contraseña incorrectos.', 'error')

    return render_template('acceso.html', register=False)


# CERRAR SESIÓN

@app.route('/salir')
@login_required
def logout():
    log_action(
        current_user.username,
        'Cierre de sesión',
        'Sesión finalizada.'
    )

    logout_user()
    flash('Sesión cerrada. ¡Hasta pronto!', 'success')

    return redirect(url_for('home'))

# PANELES DE USUARIO Y PERSONAL

@app.route('/panel')
@login_required
def dashboard():
    if not mongo_required():
        return redirect(url_for('home'))

    # PANEL DEL ALUMNO
    if current_user.role == 'alumno':
        products = list(
            db.products.find({'available': True}).sort('name', 1)
        )

        orders = list(
            db.orders.find({
                'user_id': current_user.id
            }).sort('created_at', DESCENDING).limit(12)
        )

        return render_template(
            'panel_alumno.html',
            products=products,
            orders=orders
        )

    # PANEL DE COCINA Y ADMINISTRACIÓN
    orders = list(
        db.orders.find({}).sort('created_at', DESCENDING).limit(40)
    )

    for order in orders:
        try:
            student_id = ObjectId(order['user_id'])
            order['student'] = db.users.find_one({
                '_id': student_id
            }) or {'name': 'Usuario', 'username': ''}
        except Exception:
            order['student'] = {'name': 'Usuario', 'username': ''}

    products = list(db.products.find({}).sort('name', 1))

    users = []

    if current_user.role == 'admin':
        users = list(
            db.users.find({
                'role': {'$in': ['alumno', 'cocinero']}
            }).sort('username', 1)
        )

    stats = {
        'orders': db.orders.count_documents({}),
        'users': db.users.count_documents({}),
        'products': db.products.count_documents({'available': True})
    }

    with get_sqlite_connection() as connection:
        audit_logs = []
        audit_count = 0

        if current_user.role == 'admin':
            audit_logs = connection.execute(
                'SELECT * FROM audit_logs ORDER BY id DESC LIMIT 12'
            ).fetchall()

            audit_count = connection.execute(
                'SELECT COUNT(*) FROM audit_logs'
            ).fetchone()[0]

    return render_template(
        'panel_personal.html',
        orders=orders,
        products=products,
        users=users,
        stats=stats,
        audit_logs=audit_logs,
        audit_count=audit_count
    )

# CREAR PEDIDOS

@app.route('/pedido/crear', methods=['POST'])
@roles_required('alumno')
def create_order():
    if not mongo_required():
        return redirect(url_for('dashboard'))

    selected = request.form.getlist('product_id')
    lines = []
    total = 0.0

    for product_id in selected:
        try:
            product = db.products.find_one({
                '_id': safe_object_id(product_id),
                'available': True
            })
        except Exception:
            product = None

        if not product:
            continue

        try:
            quantity = int(
                request.form.get(f'quantity_{product_id}', 1)
            )
            quantity = max(1, min(20, quantity))
        except (ValueError, TypeError):
            quantity = 1

        price = float(product.get('price', 0))

        if not math.isfinite(price) or price <= 0:
            continue

        subtotal = round(price * quantity, 2)

        lines.append({
            'product_id': str(product['_id']),
            'product_name': product['name'],
            'quantity': quantity,
            'price': price,
            'subtotal': subtotal
        })

        total += subtotal

    if not lines:
        flash('Selecciona al menos un producto disponible.', 'error')
    else:
        order = {
            'user_id': current_user.id,
            'lines': lines,
            'total': round(total, 2),
            'note': request.form.get('note', '').strip()[:240],
            'status': 'pendiente',
            'created_at': datetime.now(timezone.utc)
        }

        try:
            result = db.orders.insert_one(order)
            order['_id'] = result.inserted_id

            save_order_sqlite(order)

            log_action(
                current_user.username,
                'Pedido creado',
                f'{len(lines)} producto(s), total ${round(total, 2):.2f}.'
            )

            flash('¡Pedido enviado! Cocina ya puede verlo.', 'success')

        except (PyMongoError, sqlite3.Error) as exc:
            app.logger.error('Error al guardar el pedido: %s', exc)
            flash(
                'No se pudo guardar correctamente el pedido. Inténtalo nuevamente.',
                'error'
            )

    return redirect(url_for('dashboard'))

# CANCELAR PEDIDOS

@app.route('/pedido/<order_id>/cancelar', methods=['POST'])
@roles_required('alumno')
def cancel_order(order_id):
    if not mongo_required():
        return redirect(url_for('dashboard'))

    mongo_order_id = safe_object_id(order_id)

    order = db.orders.find_one({
        '_id': mongo_order_id,
        'user_id': current_user.id,
        'status': 'pendiente'
    })

    if not order:
        flash('Ese pedido ya no se puede cancelar.', 'info')
        return redirect(url_for('dashboard'))

    result = db.orders.update_one(
        {'_id': mongo_order_id},
        {'$set': {'status': 'cancelado'}}
    )

    if result.modified_count:
        order['status'] = 'cancelado'

        try:
            save_order_sqlite(order)

            with get_sqlite_connection() as connection:
                connection.execute(
                    """
                    INSERT INTO order_status_history
                    (order_mongo_id, previous_status, new_status, changed_by, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        str(mongo_order_id),
                        'pendiente',
                        'cancelado',
                        current_user.username,
                        now_text()
                    )
                )
        except sqlite3.Error as exc:
            app.logger.error('Error al registrar cancelación en SQLite: %s', exc)

        log_action(
            current_user.username,
            'Pedido cancelado',
            f'Pedido {order_id}.'
        )

        flash('Pedido cancelado correctamente.', 'success')
    else:
        flash('Ese pedido ya no se puede cancelar.', 'info')

    return redirect(url_for('dashboard'))

# ACTUALIZAR ESTADO DE PEDIDOS

@app.route('/pedido/<order_id>/estado', methods=['POST'])
@roles_required('cocinero', 'admin')
def update_status(order_id):
    if not mongo_required():
        return redirect(url_for('dashboard'))

    status = request.form.get('status')

    allowed_statuses = [
        'pendiente',
        'preparando',
        'listo',
        'entregado',
        'cancelado'
    ]

    if status not in allowed_statuses:
        abort(400)

    mongo_order_id = safe_object_id(order_id)

    order = db.orders.find_one({'_id': mongo_order_id})

    if not order:
        flash('No encontramos ese pedido.', 'error')
        return redirect(url_for('dashboard'))

    previous_status = order.get('status', 'pendiente')

    result = db.orders.update_one(
        {'_id': mongo_order_id},
        {'$set': {'status': status}}
    )

    if result.matched_count:
        order['status'] = status

        try:
            save_order_sqlite(order)

            if previous_status != status:
                with get_sqlite_connection() as connection:
                    connection.execute(
                        """
                        INSERT INTO order_status_history
                        (order_mongo_id, previous_status, new_status, changed_by, created_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            str(mongo_order_id),
                            previous_status,
                            status,
                            current_user.username,
                            now_text()
                        )
                    )
        except sqlite3.Error as exc:
            app.logger.error('Error al actualizar el pedido en SQLite: %s', exc)

        log_action(
            current_user.username,
            'Estado de pedido actualizado',
            f'Pedido {order_id}: {previous_status} → {status}.'
        )

        flash('Estado del pedido actualizado.', 'success')
    else:
        flash('No encontramos ese pedido.', 'error')

    return redirect(url_for('dashboard'))

# AGREGAR Y EDITAR PRODUCTOS

@app.route('/producto/guardar', methods=['POST'])
@roles_required('cocinero', 'admin')
def save_product():
    if not mongo_required():
        return redirect(url_for('dashboard'))

    name = request.form.get('name', '').strip()
    category = request.form.get('category', 'comida')

    if not name or category not in ['comida', 'bebida', 'postre']:
        flash('Revisa el nombre y la categoría del producto.', 'error')
        return redirect(url_for('dashboard'))

    try:
        price = float(request.form.get('price', '0'))

        if not math.isfinite(price) or price <= 0:
            raise ValueError

    except (ValueError, TypeError):
        flash('El precio debe ser un número mayor que cero.', 'error')
        return redirect(url_for('dashboard'))

    doc = {
        'name': name[:100],
        'description': request.form.get('description', '').strip()[:240],
        'category': category,
        'price': price,
        'available': bool(request.form.get('available'))
    }

    product_id = request.form.get('product_id', '').strip()

    try:
        if product_id:
            mongo_product_id = safe_object_id(product_id)

            result = db.products.update_one(
                {'_id': mongo_product_id},
                {'$set': doc}
            )

            if result.matched_count:
                updated_product = db.products.find_one({
                    '_id': mongo_product_id
                })

                save_product_sqlite(updated_product)

                log_action(
                    current_user.username,
                    'Producto actualizado',
                    f"Producto: {doc['name']}"
                )

                flash('Producto actualizado.', 'success')
            else:
                flash('No encontramos ese producto.', 'error')

        else:
            doc['created_at'] = datetime.now(timezone.utc)
            result = db.products.insert_one(doc)
            doc['_id'] = result.inserted_id

            save_product_sqlite(doc)

            log_action(
                current_user.username,
                'Producto creado',
                f"Producto: {doc['name']}"
            )

            flash('Producto agregado al menú.', 'success')

    except (PyMongoError, sqlite3.Error) as exc:
        app.logger.error('Error al guardar producto: %s', exc)
        flash('No se pudo guardar el producto correctamente.', 'error')

    return redirect(url_for('dashboard'))

# ELIMINAR PRODUCTOS

@app.route('/producto/<product_id>/eliminar', methods=['POST'])
@roles_required('cocinero', 'admin')
def delete_product(product_id):
    if not mongo_required():
        return redirect(url_for('dashboard'))

    mongo_product_id = safe_object_id(product_id)

    product = db.products.find_one({'_id': mongo_product_id})

    if not product:
        flash('No encontramos ese producto.', 'error')
        return redirect(url_for('dashboard'))

    result = db.products.delete_one({'_id': mongo_product_id})

    if result.deleted_count:
        try:
            with get_sqlite_connection() as connection:
                connection.execute(
                    """
                    UPDATE products
                    SET available = 0, updated_at = ?
                    WHERE mongo_id = ?
                    """,
                    (now_text(), str(mongo_product_id))
                )

        except sqlite3.Error as exc:
            app.logger.error('Error al actualizar producto en SQLite: %s', exc)

        log_action(
            current_user.username,
            'Producto eliminado',
            f"Producto: {product.get('name', product_id)}"
        )

        flash('Producto eliminado del catálogo.', 'success')

    return redirect(url_for('dashboard'))

# ADMINISTRAR ROLES DE USUARIOS

@app.route('/usuario/<user_id>/rol', methods=['POST'])
@roles_required('admin')
def change_role(user_id):
    if not mongo_required():
        return redirect(url_for('dashboard'))

    role = request.form.get('role')

    if role not in ['alumno', 'cocinero']:
        abort(400)

    target_id = safe_object_id(user_id)

    if target_id == ObjectId(current_user.id):
        flash('No puedes modificar tu propio rol desde esta sección.', 'error')
        return redirect(url_for('dashboard'))

    result = db.users.update_one(
        {
            '_id': target_id,
            'role': {'$in': ['alumno', 'cocinero']}
        },
        {'$set': {'role': role}}
    )

    if result.modified_count:
        updated_user = db.users.find_one({'_id': target_id})

        try:
            save_user_sqlite(updated_user)
        except sqlite3.Error as exc:
            app.logger.error('Error al actualizar rol en SQLite: %s', exc)

        log_action(
            current_user.username,
            'Rol de usuario actualizado',
            f'Usuario {user_id}: {role}.'
        )

        flash('Rol de usuario actualizado.', 'success')

    elif result.matched_count:
        flash('El usuario ya tenía ese rol.', 'info')

    else:
        flash('No encontramos ese usuario.', 'error')

    return redirect(url_for('dashboard'))

# PÁGINAS DE ERROR

@app.errorhandler(403)
def forbidden(_error):
    return render_template(
        'error.html',
        code=403,
        message='No tienes permiso para entrar a esta sección.'
    ), 403

@app.errorhandler(404)
def not_found(_error):
    return render_template(
        'error.html',
        code=404,
        message='No encontramos esa página.'
    ), 404

@app.errorhandler(400)
def bad_request(_error):
    return render_template(
        'error.html',
        code=400,
        message='La solicitud no es válida. Revisa los datos e inténtalo nuevamente.'
    ), 400

# INICIALIZACIÓN DE MONGODB Y SINCRONIZACIÓN

def initialize_mongo():
    if db is None or client is None:
        app.logger.warning(
            'MONGO_URI no está configurada. Completa el archivo .env.'
        )
        return

    try:
        client.admin.command('ping')

        ensure_seed_data()

        # Sincroniza la información que ya existe en MongoDB.
        sync_mongo_to_sqlite()

        app.logger.info(
            'Conexión con MongoDB correcta. '
            'Datos sincronizados con SQLite.'
        )

    except (PyMongoError, sqlite3.Error) as exc:
        app.logger.error(
            'No se pudo inicializar o sincronizar las bases de datos: %s',
            exc
        )

initialize_mongo()

# EJECUCIÓN LOCAL

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', '5000')),
        debug=os.getenv('FLASK_DEBUG', '1') == '1'
    )