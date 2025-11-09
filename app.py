from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
from flask_mysqldb import MySQL
import json
from urllib.parse import quote_plus

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

# ===============================
# 🔹 Inventario
# ===============================
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


#-----------------------------
#@app.route('/inventario/buscar')
#@login_required
#def buscar_producto():
#    query = request.args.get('q', '').lower()
#    cur = mysql.connection.cursor()
#    if query:
#        cur.execute("""
#            SELECT * FROM inventario
#            WHERE LOWER(nombre) LIKE %s OR LOWER(tipo) LIKE %s
#        """, ('%' + query + '%', '%' + query + '%'))
#    else:
#        cur.execute("SELECT * FROM inventario")
#   
#    resultados = cur.fetchall()
#    cur.close()
#    return jsonify(resultados)
#
#@app.route('/actualizar_inventario', methods=['POST'])
#def actualizar_inventario():
#    data = request.get_json()
#    codigo_barras = data.get('codigo_barras')
#    tipo = data.get('tipo')

#    if not codigo_barras or not tipo:
#        return jsonify({'error': 'Datos incompletos'}), 400

#    cursor = mysql.connection.cursor()

#    try:
#        if tipo == 'material':
#            cursor.execute("""
#                UPDATE inventario
#                SET nombre=%s, cantidad=%s, cantidad_disponible=%s,
#                    localizacion=%s, capacidad=%s, fecha_ingreso=%s, observaciones=%s
#                WHERE codigo_barras=%s
#           """, (
#                data['nombre'], data['cantidad'], data['cantidad_disponible'],
#                data['localizacion'], data['capacidad'], data['fecha_ingreso'],
#                data['observaciones'], codigo_barras
#            ))
#        elif tipo == 'reactivo':
#            cursor.execute("""
#                UPDATE inventario
#                SET nombre=%s, color=%s, cantidad=%s, cantidad_buen_estado=%s,
#                    cantidad_disponible=%s, localizacion=%s, capacidad=%s,
#                    fecha_ingreso=%s, fecha_caducidad=%s
#                WHERE codigo_barras=%s
#            """, (
#                data['nombre'], data['color'], data['cantidad'],
#                data['cantidad_buen_estado'], data['cantidad_disponible'],
#                data['localizacion'], data['capacidad'],
#                data['fecha_ingreso'], data['fecha_caducidad'], codigo_barras
#            ))
#
#        mysql.connection.commit()
#        cursor.close()
#        return jsonify({'success': True})
#
#    except Exception as e:
#        print("Error al actualizar:", e)
#        return jsonify({'error': 'Error al actualizar producto'}), 500

#


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
# Listar citas (página)
@app.route('/citas')
@login_required
def citas_view():
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, solicitante, boleta, email_solicitante, fecha, hora, estado FROM citas ORDER BY fecha, hora")
    citas = cur.fetchall()
    cur.close()
    return render_template('citas.html', citas=citas, usuario=session.get('user_id'))

# API: obtener lista de materiales de una cita (JSON)
@app.route('/citas/materiales/<int:cita_id>')
@login_required
def cita_materiales(cita_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT materiales FROM citas WHERE id = %s", (cita_id,))
    row = cur.fetchone()
    cur.close()
    if not row or not row.get('materiales'):
        return jsonify([])
    try:
        items = json.loads(row['materiales'])
    except Exception:
        items = []
    return jsonify(items)

# Generar mailto pre-armado (abre cliente de correo)
@app.route('/citas/mail/<int:cita_id>')
@login_required
def cita_mail(cita_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, solicitante, boleta, email_solicitante, fecha, hora FROM citas WHERE id = %s", (cita_id,))
    c = cur.fetchone()
    cur.close()
    if not c:
        return "Cita no encontrada", 404

    approve_url = request.url_root.rstrip('/') + url_for('aprobar_cita', id=c['id'])
    reject_url = request.url_root.rstrip('/') + url_for('rechazar_cita', id=c['id'])
    subject = f"Aprobación cita laboratorio - {c['solicitante']} ({c['boleta']})"
    body = (
        f"Solicitud de cita:\n\n"
        f"Solicitante: {c['solicitante']}\n"
        f"Boleta: {c['boleta']}\n"
        f"Fecha: {c['fecha']} Hora: {c['hora']}\n\n"
        f"Aprobar: {approve_url}\n"
        f"Rechazar: {reject_url}\n"
    )
    mailto = f"mailto:?subject={quote_plus(subject)}&body={quote_plus(body)}"
    return redirect(mailto)

# Aprobar / rechazar (links del correo)
@app.route('/citas/aprobar/<int:id>', methods=['GET','POST'])
@login_required
def aprobar_cita(id):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE citas SET estado = 'aprobada' WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    # al aprobar, puedes redirect a creación de ticket o a listado de tickets
    return redirect(url_for('listar_tickets'))

@app.route('/citas/rechazar/<int:id>', methods=['GET','POST'])
@login_required
def rechazar_cita(id):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE citas SET estado = 'rechazada' WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('citas_view'))

# ===============================
# 🔹 Tickets
# ===============================
def get_db_connection():
    return mysql.connection

@app.route('/tickets')
def tickets():
    conexion = get_db_connection()
    cursor = conexion.cursor()  # solo cursor normal
    cursor.execute("SELECT * FROM tickets ORDER BY fecha_creacion DESC")
    tickets = cursor.fetchall()
    cursor.close()
    
    # Convertir hora_utilizacion a string si es timedelta
    for t in tickets:
        if isinstance(t['hora_utilizacion'], timedelta):
            total_seconds = t['hora_utilizacion'].total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            t['hora_str'] = f"{hours:02d}:{minutes:02d}"
        else:
            t['hora_str'] = t['hora_utilizacion']  # ya es string

    return render_template('tickets.html', tickets=tickets)



@app.route('/tickets/nuevo')
@login_required
def nuevo_ticket():
    # Obtener materiales del inventario para mostrarlos en el formulario
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM inventario")
    materiales = cur.fetchall()
    cur.close()
    return render_template('nuevo_ticket.html', materiales=materiales)


@app.route('/tickets/ver/<int:ticket_id>')
@login_required
def ver_ticket(ticket_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM tickets WHERE id = %s", (ticket_id,))
    ticket = cur.fetchone()

    if not ticket:
        flash("Ticket no encontrado", "error")
        return redirect(url_for('tickets'))

    try:
        materiales = json.loads(ticket['materiales'])
    except Exception:
        materiales = []

    cur.close()
    return render_template('ver_ticket.html', ticket=ticket, materiales=materiales)


@app.route('/tickets/subir-foto', methods=['POST'])
@login_required
def subir_foto_ticket():
    ticket_id = request.form.get('ticket_id')
    foto = request.files.get('foto')

    if not foto or not ticket_id:
        return jsonify({'success': False, 'error': 'Datos incompletos'})

    # Guardar la imagen en la carpeta static/uploads/tickets/
    upload_folder = os.path.join(app.root_path, 'static', 'uploads', 'tickets')
    os.makedirs(upload_folder, exist_ok=True)

    filename = f"ticket_{ticket_id}_{foto.filename}"
    path = os.path.join(upload_folder, filename)
    foto.save(path)

    # Guardar la ruta en la BD
    cur = mysql.connection.cursor()
    cur.execute("UPDATE tickets SET evidencia = %s WHERE id = %s", (filename, ticket_id))
    mysql.connection.commit()
    cur.close()

    return jsonify({'success': True})

@app.route('/guardar_ticket', methods=['POST'])
def guardar_ticket():
    solicitante = request.form['solicitante']
    boleta = request.form['boleta']
    fecha = request.form['fecha_utilizacion']
    hora = request.form['hora_utilizacion']
    codigos = request.form.getlist('codigo[]')
    cantidades = request.form.getlist('cantidad[]')

    materiales = []
    for codigo, cantidad in zip(codigos, cantidades):
        materiales.append({"codigo": codigo, "cantidad": int(cantidad)})

    materiales_json = json.dumps(materiales)

    conexion = get_db_connection()
    cursor = conexion.cursor()  # quitar dictionary=True


    # Generar número de ticket
    cursor.execute("SELECT COUNT(*) AS total FROM tickets")
    total = cursor.fetchone()['total'] + 1
    numero_ticket = f"TCK-{total:04d}"

    # Insertar ticket
    cursor.execute("""
        INSERT INTO tickets (numero_ticket, solicitante, boleta, fecha_utilizacion, hora_utilizacion, materiales)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (numero_ticket, solicitante, boleta, fecha, hora, materiales_json))

    # Descontar materiales del inventario
    for item in materiales:
        codigo = item['codigo']
        cantidad = item['cantidad']
        cursor.execute("""
            UPDATE inventario SET cantidad = cantidad - %s WHERE codigo = %s
        """, (cantidad, codigo))

    conexion.commit()
    cursor.close()
    conexion.close()

    flash(f"Ticket {numero_ticket} generado exitosamente", "success")
    return redirect(url_for('tickets'))

@app.route("/inventario/buscar")
@login_required
def buscar_inventario():
    try:
        q = request.args.get("q", "").upper()
        conn = get_db_connection()
        cursor = conn.cursor()  # quitar dictionary=True
        cursor.execute("""
            SELECT codigo_barras AS codigo, nombre 
            FROM inventario 
            WHERE UPPER(codigo_barras) LIKE %s OR UPPER(nombre) LIKE %s
        """, (f"%{q}%", f"%{q}%"))
        resultados = cursor.fetchall()
        conn.close()
        return jsonify([{"codigo": r["codigo"], "nombre": r["nombre"]} for r in resultados])

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"error": str(e)}), 500

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
