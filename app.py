from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from flask_mysqldb import MySQL

app = Flask(__name__)

# ===============================
# 🔹 Configuración MySQL
# ===============================
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''   # Cambia según tu contraseña
app.config['MYSQL_DB'] = 'labiiz_db'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

app.secret_key = 'tu_clave_secreta_aqui'

# ===============================
# 🔹 Decorador de login
# ===============================
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# ===============================
# 🔹 Rutas de autenticación
# ===============================
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if not username or not password:
            flash('Por favor completa todos los campos', 'error')
            return render_template('login.html')
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM usuarios WHERE username = %s", (username,))
        user = cur.fetchone()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = username
            flash('¡Inicio de sesión exitoso!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
            return render_template('login.html')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Has cerrado sesión correctamente', 'success')
    return redirect(url_for('login'))

# ===============================
# 🔹 Dashboard
# ===============================
@app.route('/inicio')
@login_required
def dashboard():
    return render_template('dashboard.html', usuario=session['user_id'])

# ===============================
# 🔹 Inventario
# ===============================
@app.route('/inventario')
@login_required
def inventario_view():
    cur = mysql.connection.cursor()

    # 🔹 Actualiza los estados automáticamente (ahora insensible a mayúsculas/minúsculas)
    cur.execute("""
    UPDATE inventario
    SET estado = CASE
        WHEN tipo = 'reactivo' 
             AND fecha_caducidad <= CURDATE() + INTERVAL 7 DAY 
             AND cantidad_disponible <= 5 THEN 'proximo_caducar_y_stock_bajo'
        WHEN tipo = 'reactivo' 
             AND fecha_caducidad <= CURDATE() + INTERVAL 7 DAY THEN 'proximo_caducar'
        WHEN cantidad_disponible <= 5 THEN 'stock_bajo'
        ELSE 'ok'
    END
""")

    mysql.connection.commit()

    # 🔹 Obtiene todos los registros
    cur.execute("SELECT * FROM inventario")
    inventario_db = cur.fetchall()

    # 🔹 Filtra por tipo
    materiales = [item for item in inventario_db if item['tipo'].lower() == 'material']
    reactivos = [item for item in inventario_db if item['tipo'].lower() == 'reactivo']

    # 🔹 Reactivos próximos a caducar (7 días o menos)
    cur.execute("""
        SELECT nombre, fecha_caducidad
        FROM inventario
        WHERE LOWER(tipo) = 'reactivo' AND fecha_caducidad IS NOT NULL AND fecha_caducidad <= CURDATE() + INTERVAL 7 DAY
    """)
    proximos_caducar = cur.fetchall()
    
    proximos_caducar = list(proximos_caducar)

    cur.close()
    
    print("🧪 Reactivos próximos a caducar:", proximos_caducar)

    # 🔹 Enviar datos al template
    return render_template(
        'inventario.html',
        materiales=materiales,
        reactivos=reactivos,
        proximos_caducar=proximos_caducar,
        usuario=session['user_id']
    )

@app.route('/inventario/buscar')
@login_required
def buscar_producto():
    query = request.args.get('q', '').lower()
    cur = mysql.connection.cursor()
    if query:
        cur.execute("""
            SELECT * FROM inventario
            WHERE LOWER(nombre) LIKE %s OR LOWER(tipo) LIKE %s
        """, ('%' + query + '%', '%' + query + '%'))
    else:
        cur.execute("SELECT * FROM inventario")
    
    resultados = cur.fetchall()
    cur.close()
    return jsonify(resultados)

# ===============================
# 🔹 Almacén
# ===============================
@app.route('/almacen')
@login_required
def almacen_view():
    cur = mysql.connection.cursor()
    cur.execute("SELECT nombre, codigo_barras, tipo, color FROM inventario")
    almacen_db = cur.fetchall()
    cur.close()

    return render_template('almacen.html', productos=almacen_db, usuario=session['user_id'])

@app.route('/almacen/listar')
def listar_materiales():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM materiales")
    materiales = cur.fetchall()
    cur.close()
    return jsonify(materiales)

@app.route('/almacen/agregar', methods=['POST'])
def agregar_material():
    data = request.get_json()
    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO materiales (nombre, tipo, color, codigo, cantidad, localizacion, capacidad, fecha_ingreso, fecha_caducidad, observaciones)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        data['nombre'], data['tipo'], data['color'], data['codigo'], data['cantidad'],
        data['localizacion'], data['capacidad'], data['fechaIngreso'], data['fechaCaducidad'], data['observaciones']
    ))
    mysql.connection.commit()
    cur.close()
    return jsonify({"mensaje": "Producto agregado correctamente"})

# ===============================
# 🔹 Citas
# ===============================
@app.route('/citas')
@login_required
def citas():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM citas")
    citas_db = cur.fetchall()
    cur.close()
    return render_template('citas.html', citas=citas_db)

@app.route('/aprobar/<int:id>', methods=['POST'])
@login_required
def aprobar_cita(id):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE citas SET estado = 'Aprobada' WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('citas'))

@app.route('/rechazar/<int:id>', methods=['POST'])
@login_required
def rechazar_cita(id):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE citas SET estado = 'Rechazada' WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('citas'))

@app.route('/ver/<int:id>')
@login_required
def ver_cita(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM citas WHERE id = %s", (id,))
    cita = cur.fetchone()
    cur.close()
    return render_template('ver_cita.html', cita=cita)

# ===============================
# 🔹 Tickets
# ===============================
@app.route('/tickets')
@login_required
def listar_tickets():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM tickets")
    tickets = cur.fetchall()
    cur.close()
    return render_template('tickets.html', tickets=tickets)

# ===============================
# 🔹 Funciones auxiliares
# ===============================
@app.context_processor
def utility_processor():
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

# ===============================
# 🔹 Ejecutar servidor
# ===============================
if __name__ == '__main__':
    app.run(debug=True)
