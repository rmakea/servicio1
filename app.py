from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
import json
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui'

# Simulación de base de datos
users = {
    'admin': generate_password_hash('admin123'),
    '2021630001': generate_password_hash('password123'),
}

# Datos de inventario de ejemplo
inventario = [
    {
        'id': 1,
        'producto': 'Reactivo A',
        'descripcion': 'Reactivo químico para análisis',
        'categoria': 'Químicos',
        'cantidad': '2 ml',
        'cantidad_disponible': '1 ml',
        'estado': 'stock_bajo',
        'fecha_caducidad': '2024-12-31'
    },
    {
        'id': 2,
        'producto': 'Reactivo B',
        'descripcion': 'Reactivo para pruebas especiales',
        'categoria': 'Químicos',
        'cantidad': '20 ml',
        'cantidad_disponible': '15 ml',
        'estado': 'ok',
        'fecha_caducidad': '2025-06-15'
    },
    {
        'id': 3,
        'producto': 'Reactivo C',
        'descripcion': 'Reactivo con fecha de caducidad próxima',
        'categoria': 'Químicos',
        'cantidad': '5 ml',
        'cantidad_disponible': '4 ml',
        'estado': 'proximo_caducar',
        'fecha_caducidad': '2024-08-30'
    },
    {
        'id': 4,
        'producto': 'Ácido Sulfúrico',
        'descripcion': 'Ácido para análisis volumétrico',
        'categoria': 'Ácidos',
        'cantidad': '500 ml',
        'cantidad_disponible': '450 ml',
        'estado': 'ok',
        'fecha_caducidad': '2025-12-31'
    },
    {
        'id': 5,
        'producto': 'Hidróxido de Sodio',
        'descripcion': 'Base fuerte para neutralización',
        'categoria': 'Bases',
        'cantidad': '100 g',
        'cantidad_disponible': '25 g',
        'estado': 'stock_bajo',
        'fecha_caducidad': '2025-03-15'
    }
]

def login_required(f):
    """Decorador para rutas que requieren autenticación"""
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@app.route('/')
def index():
    """Página principal"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Ruta para el login"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if not username or not password:
            flash('Por favor completa todos los campos', 'error')
            return render_template('login.html')
        
        if username in users and check_password_hash(users[username], password):
            session['user_id'] = username
            flash('¡Inicio de sesión exitoso!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
            return render_template('login.html')
    
    return render_template('login.html')

@app.route('/inicio')
@login_required
def dashboard():
    return render_template('dashboard.html', usuario=session['user_id'])
 #Para abrir despues de iniciar sesión

@app.route('/inventario')
@login_required
def inventario_view():
    """Vista principal del inventario"""
    # Calcular estadísticas
    total_productos = len(inventario)
    bajo_stock = len([item for item in inventario if item['estado'] == 'stock_bajo'])
    caducan_pronto = len([item for item in inventario if item['estado'] == 'proximo_caducar'])
    
    estadisticas = {
        'total_productos': total_productos,
        'bajo_stock': bajo_stock,
        'caducan_pronto': caducan_pronto
    }
    
    return render_template('inventario.html', 
                         inventario=inventario, 
                         estadisticas=estadisticas,
                         usuario=session['user_id'])

@app.route('/almacen')
def inventory():
    products = [
        {'name': 'Reactivo A', 'barcode': '2112345789'},
        {'name': 'Reactivo B', 'barcode': '2112345790'},
        # ... más productos
    ]
    return render_template('almacen.html', products=products)

@app.route('/inventario/buscar')
@login_required
def buscar_producto():
    """API para buscar productos"""
    query = request.args.get('q', '').lower()
    
    if not query:
        return jsonify(inventario)
    
    resultados = [
        item for item in inventario 
        if query in item['producto'].lower() or query in item['descripcion'].lower()
    ]
    
    return jsonify(resultados)

@app.route('/citas')
def citas():
    citas = [
        {
            'id': 1,
            'fecha': '03/07/2025',
            'hora': '10:00 am',
            'solicitante': 'Juan Martínez',
            'actividad': 'Uso de espectrofotómetro',
            'estado': 'Aprobada'
        },
        {
            'id': 2,
            'fecha': '04/07/2025',
            'hora': '12:00 pm',
            'solicitante': 'Ana Torres',
            'actividad': 'Análisis microbiológico',
            'estado': 'Pendiente'
        }
    ]
    return render_template('citas.html', citas=citas)

@app.route('/tickets')
@login_required
def listar_tickets():
    # Simulación de tickets (puedes usar una lista por ahora)
    tickets = [
        {'id': 1, 'alumno': 'Luis Pérez', 'fecha_prestamo': datetime(2025, 7, 10, 10, 30)},
        {'id': 2, 'alumno': 'María López', 'fecha_prestamo': datetime(2025, 7, 11, 9, 15)},
    ]
    return render_template('tickets.html', tickets=tickets)


@app.route('/aprobar/<int:id>', methods=['POST'])
def aprobar_cita(id):
    # lógica para aprobar cita
    return redirect(url_for('citas'))

@app.route('/rechazar/<int:id>', methods=['POST'])
def rechazar_cita(id):
    # lógica para rechazar cita
    return redirect(url_for('citas'))

@app.route('/ver/<int:id>')
def ver_cita(id):
    # lógica para mostrar detalle de cita
    return f"Detalle de la cita {id}"


@app.route('/logout')
def logout():
    """Cerrar sesión"""
    session.pop('user_id', None)
    flash('Has cerrado sesión correctamente', 'success')
    return redirect(url_for('login'))

@app.context_processor
def utility_processor():
    """Funciones auxiliares para templates"""
    def get_estado_badge(estado):
        badges = {
            'ok': 'bg-green-100 text-green-800',
            'stock_bajo': 'bg-yellow-100 text-yellow-800',
            'proximo_caducar': 'bg-orange-100 text-orange-800'
        }
        return badges.get(estado, 'bg-gray-100 text-gray-800')
    
    def get_estado_icon(estado):
        icons = {
            'ok': 'fas fa-check',
            'stock_bajo': 'fas fa-exclamation-triangle',
            'proximo_caducar': 'fas fa-clock'
        }
        return icons.get(estado, 'fas fa-question')
    
    def get_estado_text(estado):
        texts = {
            'ok': 'OK',
            'stock_bajo': 'Stock bajo',
            'proximo_caducar': 'Próximo a caducar'
        }
        return texts.get(estado, 'Desconocido')
    
    return dict(
        get_estado_badge=get_estado_badge,
        get_estado_icon=get_estado_icon,
        get_estado_text=get_estado_text
    )

if __name__ == '__main__':
    app.run(debug=True)