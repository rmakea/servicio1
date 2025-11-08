from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
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
from datetime import datetime, timedelta
# ===============================
# 🔹 Dashboard
# ===============================
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', usuario=session.get('user_id'))

# ===============================
# 🔹 Funciones para obtener materiales y reactivos
# ===============================
def obtener_materiales_desde_bd():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM inventario WHERE tipo = 'Material'")
    materiales = cur.fetchall()
    cur.close()
    return materiales

def obtener_reactivos_desde_bd():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM inventario WHERE tipo = 'Reactivo'")
    reactivos = cur.fetchall()
    cur.close()
    return reactivos


@app.route('/inventario')
@login_required
def inventario_view():
    materiales = obtener_materiales_desde_bd()
    reactivos = obtener_reactivos_desde_bd()

    hoy = datetime.now().date()
    limite_caducidad = hoy + timedelta(days=7)

    # 🔹 Filtrar materiales con stock bajo y caducidad próxima
    stock_bajo_materiales = [m for m in materiales if m['cantidad'] <= 5]
    caducidad_proxima_materiales = [
        m for m in materiales
        if m.get('fecha_caducidad') and m['fecha_caducidad'] <= limite_caducidad
    ]

    # 🔹 Filtrar reactivos con stock bajo y caducidad próxima
    stock_bajo_reactivos = [r for r in reactivos if r['cantidad'] <= 5]
    caducidad_proxima_reactivos = [
        r for r in reactivos
        if r.get('fecha_caducidad') and r['fecha_caducidad'] <= limite_caducidad
    ]

    return render_template(
        'inventario.html',
        materiales=materiales,
        reactivos=reactivos,
        stock_bajo_materiales=stock_bajo_materiales,
        caducidad_proxima_materiales=caducidad_proxima_materiales,
        stock_bajo_reactivos=stock_bajo_reactivos,
        caducidad_proxima_reactivos=caducidad_proxima_reactivos
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
    productos = cur.fetchall()
    cur.close()
    return render_template('almacen.html', productos=productos, usuario=session['user_id'])


@app.route('/almacen/listar')
def listar_materiales():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM materiales")
    materiales = cur.fetchall()
    cur.close()
    return jsonify(materiales)

@app.route('/almacen/agregar', methods=['POST'])
@login_required
def agregar_material():
    data = request.get_json()

    nombre = data.get('nombre')
    tipo = data.get('tipo')
    color = data.get('color')
    cantidad = data.get('cantidad')
    localizacion = data.get('localizacion')
    capacidad = data.get('capacidad')
    fecha_ingreso = data.get('fecha_ingreso')
    fecha_caducidad = data.get('fecha_caducidad')
    observaciones = data.get('observaciones')

    # Genera código de barras automático
    codigo_barras = f"MT{int(datetime.now().timestamp())}"

    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO inventario 
        (nombre, tipo, color, codigo_barras, cantidad, cantidad_buen_estado, cantidad_disponible, cantidad_danada, 
         localizacion, capacidad, fecha_ingreso, fecha_caducidad, observaciones)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        nombre, tipo, color, codigo_barras, cantidad,
        cantidad, cantidad, 0, localizacion, capacidad,
        fecha_ingreso, fecha_caducidad, observaciones
    ))

    mysql.connection.commit()
    cur.close()

    return jsonify({'ok': True})

@app.route('/inventario/eliminar/<codigo_barras>', methods=['DELETE'])
@login_required
def eliminar_producto(codigo_barras):
    try:
        print(f"🗑️ Intentando eliminar producto con código: {codigo_barras}")
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM inventario WHERE codigo_barras = %s", (codigo_barras,))
        mysql.connection.commit()
        cur.close()
        print("✅ Producto eliminado de la base de datos.")
        return jsonify({'ok': True, 'mensaje': 'Producto eliminado correctamente'})
    except Exception as e:
        print("❌ Error al eliminar:", e)
        return jsonify({'ok': False, 'error': str(e)})



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
