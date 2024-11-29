from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
import os
from datetime import date, timedelta
from datetime import date
from werkzeug.utils import secure_filename
import bcrypt

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui'  # Cambia esto por una clave secreta única


UPLOAD_FOLDER = 'static/documentos/'  # El directorio donde se guardarán las imágenes
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}  # Extensiones permitidas para las imágenes

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_tournament_image(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)  # Asegura que el nombre sea seguro
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)  # Ruta completa del archivo
        file.save(filepath)  # Guarda el archivo en el servidor
        return f'/static/documentos/{filename}'  # Retorna la URL de la imagen guardada
    return None  # Si el archivo no es válido, retorna None

# Conexión a MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="db_troya_fc"
)




# Ruta para mostrar las estadísticas del torneo
@app.route('/estadisticas_torneo')
def estadisticas_torneo():
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT t.nombre AS torneo, t.imagen_url AS torneo_imagen,
               te.equipo_nombre, te.puntos, te.goles, te.goles_recibidos,
               te.id as equipo_id
        FROM torneo t
        LEFT JOIN torneos_estadisticas te ON t.id = te.torneo_id
        ORDER BY t.nombre, te.puntos DESC
    """)
    estadisticas = cursor.fetchall()
    cursor.close()
    return render_template('estadisticas_torneo.html', estadisticas=estadisticas)

# Ruta para el panel de administración de torneos
@app.route('/estadisticas_torneo_admin', methods=['GET', 'POST'])
def estadisticas_torneo_admin():
    cursor = db.cursor(dictionary=True)

    if request.method == 'POST':
        try:
            # Agregar un nuevo torneo
            if 'add_torneo' in request.form:
                nombre = request.form['nombre']
                imagen_url = None

                # Procesar la imagen si se proporcionó
                if 'imagen' in request.files:
                    file = request.files['imagen']
                    imagen_url = save_tournament_image(file)

                cursor.execute(
                    "INSERT INTO torneo (nombre, imagen_url) VALUES (%s, %s)",
                    (nombre, imagen_url)
                )
                db.commit()
                flash('Torneo agregado exitosamente', 'success')

            # Agregar un nuevo equipo
            elif 'add_equipo' in request.form:
                torneo_id = request.form['torneo_id']
                equipo_nombre = request.form['equipo_nombre']
                puntos = request.form['puntos']
                goles = request.form['goles']
                goles_recibidos = request.form['goles_recibidos']

                # Verificar si el equipo ya existe en el torneo
                cursor.execute("""
                    SELECT id FROM torneos_estadisticas 
                    WHERE torneo_id = %s AND equipo_nombre = %s
                """, (torneo_id, equipo_nombre))
                
                if cursor.fetchone():
                    flash('Este equipo ya existe en el torneo', 'error')
                else:
                    cursor.execute("""
                        INSERT INTO torneos_estadisticas 
                        (torneo_id, equipo_nombre, puntos, goles, goles_recibidos)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (torneo_id, equipo_nombre, puntos, goles, goles_recibidos))
                    db.commit()
                    flash('Equipo agregado exitosamente', 'success')

            # Eliminar un torneo
            elif 'delete_torneo' in request.form:
                torneo_id = request.form['torneo_id']
                
                # Obtener la URL de la imagen antes de eliminar
                cursor.execute("SELECT imagen_url FROM torneo WHERE id = %s", (torneo_id,))
                result = cursor.fetchone()
                if result and result['imagen_url']:
                    # Eliminar el archivo de imagen si existe
                    imagen_path = os.path.join(app.root_path, result['imagen_url'].lstrip('/'))
                    if os.path.exists(imagen_path):
                        os.remove(imagen_path)

                # Eliminar el torneo y sus estadísticas (asumiendo ON DELETE CASCADE)
                cursor.execute("DELETE FROM torneo WHERE id = %s", (torneo_id,))
                db.commit()
                flash('Torneo eliminado exitosamente', 'success')

            # Eliminar un equipo
            elif 'delete_equipo' in request.form:
                equipo_id = request.form['equipo_id']
                cursor.execute("DELETE FROM torneos_estadisticas WHERE id = %s", (equipo_id,))
                db.commit()
                flash('Equipo eliminado exitosamente', 'success')

        except Exception as e:
            db.rollback()
            flash(f'Error: {str(e)}', 'error')
            
        return redirect(url_for('estadisticas_torneo_admin'))

    # Obtener todos los torneos y estadísticas
    cursor.execute("SELECT id, nombre, imagen_url FROM torneo ORDER BY nombre")
    torneos = cursor.fetchall()

    cursor.execute("""
        SELECT t.id AS torneo_id, t.nombre AS torneo, t.imagen_url AS torneo_imagen,
               te.id AS equipo_id, te.equipo_nombre, te.puntos, te.goles, te.goles_recibidos
        FROM torneo t
        LEFT JOIN torneos_estadisticas te ON t.id = te.torneo_id
        ORDER BY t.nombre, te.puntos DESC
    """)
    estadisticas = cursor.fetchall()

    cursor.close()
    return render_template('estadisticas_torneo_admin.html', 
                         torneos=torneos, 
                         estadisticas=estadisticas)
    








# Confirmación de registro
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Las contraseñas no coinciden', 'error')
            return redirect(url_for('register'))
        
        # Generar el hash de la contraseña
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        cursor = db.cursor(dictionary=True)
        query = "INSERT INTO usuarios (usuario, contraseña) VALUES (%s, %s)"
        cursor.execute(query, (email, hashed_password))
        db.commit()
        cursor.close()
        
        flash('Registro exitoso. Por favor, inicia sesión.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

# Confirmación de inicio de sesión
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor = db.cursor(dictionary=True)
        query = "SELECT * FROM usuarios WHERE usuario = %s"
        cursor.execute(query, (email,))
        user = cursor.fetchone()
        cursor.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user['contraseña'].encode('utf-8')):
            session['user_id'] = user['id']  # Guarda el ID del usuario en la sesión
            flash('Inicio de sesión exitoso.', 'success')
            return redirect(url_for('bienvenido'))
        else:
            flash('Usuario o contraseña incorrectos.', 'error')
    
    return render_template('login.html')

# Cierre de sesión
@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Elimina el ID del usuario de la sesión
    flash('Has cerrado sesión correctamente.', 'success')
    return redirect(url_for('login'))




@app.route('/')

def index():
    return render_template('index.html')
#panel de torneo
@app.route('/torneos')
def torneos():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM torneos")
    torneos = cursor.fetchall()
    cursor.close()
    return render_template('torneos.html', torneos=torneos)


@app.route('/quien')
def quien():
    return render_template('quien.html')

#panel de administrador

@app.route('/bienvenido')
def bienvenido():
    return render_template('bienvenido.html')
#noticias 
@app.route('/noticias')
def noticias():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM noticias")
    noticias = cursor.fetchall()
    cursor.close()
    return render_template('noticias.html', noticias=noticias)
#galeria
@app.route('/galeria')
def galeria():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM galeria")
    galeria = cursor.fetchall()
    cursor.close()
    return render_template('galeria.html', galeria=galeria)


    
    
# Noticias admin agregar
@app.route('/noticias_admin', methods=['GET', 'POST'])
def noticias_admin():
    cursor = db.cursor()
    
    # Obtener todas las noticias
    cursor.execute("SELECT id, titulo, descripcion, imagen FROM noticias")
    noticias = cursor.fetchall()
    
    if request.method == 'POST':
        if 'add_noticia' in request.form:
            titulo = request.form['titulo']
            descripcion = request.form['descripcion']
            imagen = request.files['imagen']
            if imagen:
                imagen_filename = os.path.join('static/media', imagen.filename)
                imagen.save(imagen_filename)
                cursor.execute("INSERT INTO noticias (titulo, descripcion, imagen) VALUES (%s, %s, %s)", (titulo, descripcion, imagen.filename))
                db.commit()
                return redirect(url_for('noticias_admin'))
        elif 'delete_noticia' in request.form:
            noticia_id = request.form['noticia_id']
            cursor.execute("SELECT imagen FROM noticias WHERE id = %s", (noticia_id,))
            result = cursor.fetchone()
            if result:
                imagen_filename = os.path.join('static/media', result[0])
                if os.path.exists(imagen_filename):
                    os.remove(imagen_filename)
                cursor.execute("DELETE FROM noticias WHERE id = %s", (noticia_id,))
                db.commit()
            return redirect(url_for('noticias_admin'))
    
    cursor.close()
    return render_template('noticias_admin.html', noticias=noticias)


# gale admin agregar
@app.route('/galeria_admin', methods=['GET', 'POST'])
def galeria_admin():
    cursor = db.cursor()
    
    # Obtener todas las galeria
    cursor.execute("SELECT id, titulo, descripcion, imagen FROM galeria")
    galeria = cursor.fetchall()
    
    if request.method == 'POST':
        if 'add_galeria' in request.form:
            titulo = request.form['titulo']
            descripcion = request.form['descripcion']
            imagen = request.files['imagen']
            if imagen:
                imagen_filename = os.path.join('static/media', imagen.filename)
                imagen.save(imagen_filename)
                cursor.execute("INSERT INTO galeria (titulo, descripcion, imagen) VALUES (%s, %s, %s)", (titulo, descripcion, imagen.filename))
                db.commit()
                return redirect(url_for('galeria_admin'))
        elif 'delete_galeria' in request.form:
            galeria_id = request.form['galeria_id']
            cursor.execute("SELECT imagen FROM galeria WHERE id = %s", (galeria_id,))
            result = cursor.fetchone()
            if result:
                imagen_filename = os.path.join('static/media', result[0])
                if os.path.exists(imagen_filename):
                    os.remove(imagen_filename)
                cursor.execute("DELETE FROM galeria WHERE id = %s", (galeria_id,))
                db.commit()
            return redirect(url_for('galeria_admin'))
    
    cursor.close()
    return render_template('galeria_admin.html', galeria=galeria)


# torneos admin agregar
@app.route('/torneos_admin', methods=['GET', 'POST'])
def torneos_admin():
    cursor = db.cursor()

    # Obtener todos los torneos
    cursor.execute("SELECT id, titulo, descripcion, imagen FROM torneos")
    torneos = cursor.fetchall()
    
    if request.method == 'POST':
        if 'add_torneo' in request.form:
            titulo = request.form['titulo']
            descripcion = request.form['descripcion']
            imagen = request.files['imagen']
            if imagen:
                imagen_filename = os.path.join('static/media', imagen.filename)
                imagen.save(imagen_filename)
                cursor.execute("INSERT INTO torneos (titulo, descripcion, imagen) VALUES (%s, %s, %s)", (titulo, descripcion, imagen.filename))
                db.commit()
                return redirect(url_for('torneos_admin'))
        elif 'delete_torneo' in request.form:
            torneo_id = request.form['torneo_id']
            cursor.execute("SELECT imagen FROM torneos WHERE id = %s", (torneo_id,))
            result = cursor.fetchone()
            if result:
                imagen_filename = os.path.join('static/media', result[0])
                if os.path.exists(imagen_filename):
                    os.remove(imagen_filename)
                cursor.execute("DELETE FROM torneos WHERE id = %s", (torneo_id,))
                db.commit()
            return redirect(url_for('torneos_admin'))
    
    cursor.close()
    return render_template('torneos_admin.html', torneos=torneos)



@app.route('/subs')
def subs():
    return render_template('subs.html')

# Ruta para mostrar los jugadores de la categoría sub12
@app.route('/sub12')
def sub12():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM sub12")
    jugadores = cursor.fetchall()
    cursor.close()
    return render_template('sub12.html', jugadores=jugadores, fecha_actual=date.today(), date=date,timedelta=timedelta)



@app.route('/eliminar_jugador_sub12/<int:jugador_id>', methods=['POST'])
def eliminar_jugador_sub12(jugador_id):
    cursor = db.cursor()

    # Primero eliminar documentos asociados al jugador
    cursor.execute("DELETE FROM documentos_sub12 WHERE jugador_id = %s", (jugador_id,))
    
    # Luego eliminar el jugador
    cursor.execute("DELETE FROM sub12 WHERE id = %s", (jugador_id,))
    db.commit()
    cursor.close()
    return redirect(url_for('sub12'))



# Ruta para ver un jugador específico de sub12
@app.route('/jugador_sub12/<int:id>', methods=['GET', 'POST'])
def jugador_sub12(id):
    cursor = db.cursor(dictionary=True)
    
    # Obtener información del jugador
    cursor.execute("SELECT * FROM sub12 WHERE id = %s", (id,))
    jugador = cursor.fetchone()

    if request.method == 'POST':
        # Manejar carga de documentos
        if 'documento' in request.files:
            documento = request.files['documento']
            if documento and documento.filename.endswith('.pdf'):
                filename = f"{id}_{documento.filename}"
                documento.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                cursor.execute("INSERT INTO documentos_sub12 (jugador_id, titulo_documento, ruta_documento) VALUES (%s, %s, %s)",
                               (id, documento.filename, filename))
                db.commit()
                cursor.close()
                return redirect(url_for('jugador_sub12', id=id))

    # Calcular el rendimiento del jugador
    def calcular_rendimiento(jugador):
        partidos_jugados = jugador.get('partidos_jugados', 0)
        goles = jugador.get('goles', 0)
        asistencias = jugador.get('asistencias', 0)
        goles_sin_penalti = jugador.get('goles_sin_penalti', 0)
        goles_recibidos = jugador.get('goles_recibidos', 0)
        intercepciones = jugador.get('intercepciones', 0)
        
        # Fórmula de rendimiento para el arquero
        if jugador.get('posicion') == 'Arquero':
            rendimiento = (intercepciones * 0.4 - goles_recibidos * 0.6) / max(partidos_jugados, 1)
        else:
            # Fórmula de rendimiento para jugadores de campo
            rendimiento = (goles * 0.5 + asistencias * 0.3 + goles_sin_penalti * 0.2) / max(partidos_jugados, 1)
        
        # Determinar calificación
        if rendimiento > 2:
            calificacion = "Excelente"
        elif rendimiento > 1.5:
            calificacion = "Muy Bueno"
        elif rendimiento > 1:
            calificacion = "Bueno"
        else:
            calificacion = "Mejorable"
        
        return {'puntaje': round(rendimiento, 2), 'calificacion': calificacion}
    
    rendimiento = calcular_rendimiento(jugador)
    
    # Obtener documentos del jugador
    cursor.execute("SELECT * FROM documentos_sub12 WHERE jugador_id = %s", (id,))
    documentos = cursor.fetchall()
    
    cursor.close()
    return render_template('jugador_sub12.html', jugador=jugador, rendimiento=rendimiento, documentos=documentos)

@app.route('/descargar_documento/<filename>')
def descargar_documento(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Ruta para actualizar estadísticas de jugadores sub12
@app.route('/actualizar_estadisticas_sub12/<int:id>', methods=['POST'])
def actualizar_estadisticas_sub12(id):
    partidos_jugados = request.form.get('partidos_jugados', 0)
    goles_recibidos = request.form.get('goles_recibidos', 0)
    intercepciones = request.form.get('intercepciones', 0)
    tarjetas_amarillas = request.form.get('tarjetas_amarillas', 0)
    tarjetas_rojas = request.form.get('tarjetas_rojas', 0)
    goles = request.form.get('goles', 0)
    asistencias = request.form.get('asistencias', 0)
    goles_sin_penalti = request.form.get('goles_sin_penalti', 0)

    cursor = db.cursor()
    
    if request.form['posicion'] == 'Arquero':
        cursor.execute("""
            UPDATE sub12 
            SET partidos_jugados = %s, goles_recibidos = %s, intercepciones = %s, 
            tarjetas_amarillas = %s, tarjetas_rojas = %s
            WHERE id = %s""",
            (partidos_jugados, goles_recibidos, intercepciones, tarjetas_amarillas, tarjetas_rojas, id))
    else:
        cursor.execute("""
            UPDATE sub12 
            SET partidos_jugados = %s, goles = %s, asistencias = %s, 
            goles_sin_penalti = %s, tarjetas_amarillas = %s, tarjetas_rojas = %s
            WHERE id = %s""",
            (partidos_jugados, goles, asistencias, goles_sin_penalti, tarjetas_amarillas, tarjetas_rojas, id))
    
    db.commit()
    cursor.close()

    return redirect(url_for('jugador_sub12', id=id))

# Nueva ruta para agregar jugadores a sub12
@app.route('/agregar_jugador_sub12', methods=['GET', 'POST'])
def agregar_jugador_sub12():
    if request.method == 'POST':
        nombre = request.form['nombre']
        documento = request.form['documento']
        tipo_documento = request.form['tipo_documento']  # Agregado
        edad = request.form['edad']
        estatura = request.form['estatura']
        peso = request.form['peso']
        imagen = request.files['imagen']
        posicion = request.form['posicion']

        if imagen:
            imagen_filename = os.path.join('static/uploads', imagen.filename)
            imagen.save(imagen_filename)
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO sub12 (nombre, documento, tipo_documento, edad, estatura, peso, imagen, posicion)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (nombre, documento, tipo_documento, edad, estatura, peso, imagen.filename, posicion))
            db.commit()
            cursor.close()

            return redirect(url_for('sub12'))

    return render_template('agregar_jugador_sub12.html')


@app.route('/agregar_jugador_sub15', methods=['GET', 'POST'])
def agregar_jugador_sub15():
    if request.method == 'POST':
        nombre = request.form['nombre']
        documento = request.form['documento']
        tipo_documento = request.form['tipo_documento']  # Agregado
        edad = request.form['edad']
        estatura = request.form['estatura']
        peso = request.form['peso']
        imagen = request.files['imagen']
        posicion = request.form['posicion']

        if imagen:
            imagen_filename = os.path.join('static/uploads', imagen.filename)
            imagen.save(imagen_filename)
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO sub15 (nombre, documento, tipo_documento, edad, estatura, peso, imagen, posicion)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (nombre, documento, tipo_documento, edad, estatura, peso, imagen.filename, posicion))
            db.commit()
            cursor.close()

            return redirect(url_for('sub15'))

    return render_template('agregar_jugador_sub15.html')



@app.route('/agregar_jugador_sub18', methods=['GET', 'POST'])
def agregar_jugador_sub18():
    if request.method == 'POST':
        nombre = request.form['nombre']
        documento = request.form['documento']
        tipo_documento = request.form['tipo_documento']  # Agregado
        edad = request.form['edad']
        estatura = request.form['estatura']
        peso = request.form['peso']
        imagen = request.files['imagen']
        posicion = request.form['posicion']

        if imagen:
            imagen_filename = os.path.join('static/uploads', imagen.filename)
            imagen.save(imagen_filename)
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO sub18 (nombre, documento, tipo_documento, edad, estatura, peso, imagen, posicion)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (nombre, documento, tipo_documento, edad, estatura, peso, imagen.filename, posicion))
            db.commit()
            cursor.close()

            return redirect(url_for('sub18'))

    return render_template('agregar_jugador_sub18.html')


# Nueva ruta para pagar mensualidad
@app.route('/pagar_mensualidad_sub12/<int:id>', methods=['POST'])
def pagar_mensualidad_sub12(id):
    fecha_actual = date.today()

    cursor = db.cursor()
    cursor.execute("""
        UPDATE sub12 
        SET fecha_inicio = %s
        WHERE id = %s""",
        (fecha_actual, id))
    db.commit()
    cursor.close()

    return redirect(url_for('sub12'))

@app.route('/pagar_mensualidad_sub15/<int:id>', methods=['POST'])
def pagar_mensualidad_sub15(id):
    fecha_actual = date.today()

    cursor = db.cursor()
    cursor.execute("""
        UPDATE sub15 
        SET fecha_inicio = %s
        WHERE id = %s""",
        (fecha_actual, id))
    db.commit()
    cursor.close()

    return redirect(url_for('sub15'))


@app.route('/pagar_mensualidad_sub18/<int:id>', methods=['POST'])
def pagar_mensualidad_sub18(id):
    fecha_actual = date.today()

    cursor = db.cursor()
    cursor.execute("""
        UPDATE sub18 
        SET fecha_inicio = %s
        WHERE id = %s""",
        (fecha_actual, id))
    db.commit()
    cursor.close()

    return redirect(url_for('sub18'))
# Ruta para mostrar los jugadores de la categoría sub15
@app.route('/sub15')
def sub15():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM sub15")
    jugadores = cursor.fetchall()
    cursor.close()
    return render_template('sub15.html', jugadores=jugadores, fecha_actual=date.today(), date=date,timedelta=timedelta)

@app.route('/eliminar_jugador_sub15/<int:jugador_id>', methods=['POST'])
def eliminar_jugador_sub15(jugador_id):
    cursor = db.cursor()

    # Primero eliminar documentos asociados al jugador
    cursor.execute("DELETE FROM documentos_sub15 WHERE jugador_id = %s", (jugador_id,))
    
    # Luego eliminar el jugador
    cursor.execute("DELETE FROM sub15 WHERE id = %s", (jugador_id,))
    db.commit()
    cursor.close()
    return redirect(url_for('sub15'))


# Ruta para ver un jugador específico de sub15
@app.route('/jugador_sub15/<int:id>', methods=['GET', 'POST'])
def jugador_sub15(id):
    cursor = db.cursor(dictionary=True)
    
    # Obtener información del jugador
    cursor.execute("SELECT * FROM sub15 WHERE id = %s", (id,))
    jugador = cursor.fetchone()

    if request.method == 'POST':
        # Manejar carga de documentos
        if 'documento' in request.files:
            documento = request.files['documento']
            if documento and documento.filename.endswith('.pdf'):
                filename = f"{id}_{documento.filename}"
                documento.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                cursor.execute("INSERT INTO documentos_sub15 (jugador_id, titulo_documento, ruta_documento) VALUES (%s, %s, %s)",
                               (id, documento.filename, filename))
                db.commit()
                cursor.close()
                return redirect(url_for('jugador_sub15', id=id))

    # Calcular el rendimiento del jugador
    def calcular_rendimiento(jugador):
        partidos_jugados = jugador.get('partidos_jugados', 0)
        goles = jugador.get('goles', 0)
        asistencias = jugador.get('asistencias', 0)
        goles_sin_penalti = jugador.get('goles_sin_penalti', 0)
        goles_recibidos = jugador.get('goles_recibidos', 0)
        intercepciones = jugador.get('intercepciones', 0)
        
        # Fórmula de rendimiento para el arquero
        if jugador.get('posicion') == 'Arquero':
            rendimiento = (intercepciones * 0.4 - goles_recibidos * 0.6) / max(partidos_jugados, 1)
        else:
            # Fórmula de rendimiento para jugadores de campo
            rendimiento = (goles * 0.5 + asistencias * 0.3 + goles_sin_penalti * 0.2) / max(partidos_jugados, 1)
        
        # Determinar calificación
        if rendimiento > 2:
            calificacion = "Excelente"
        elif rendimiento > 1.5:
            calificacion = "Muy Bueno"
        elif rendimiento > 1:
            calificacion = "Bueno"
        else:
            calificacion = "Mejorable"
        
        return {'puntaje': round(rendimiento, 2), 'calificacion': calificacion}
    
    rendimiento = calcular_rendimiento(jugador)
    
    # Obtener documentos del jugador
    cursor.execute("SELECT * FROM documentos_sub15 WHERE jugador_id = %s", (id,))
    documentos = cursor.fetchall()
    
    cursor.close()
    return render_template('jugador_sub15.html', jugador=jugador, rendimiento=rendimiento, documentos=documentos)

@app.route('/descargar_documento_sub15/<filename>')
def descargar_documento_sub15(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Ruta para actualizar estadísticas de jugadores sub15
@app.route('/actualizar_estadisticas_sub15/<int:id>', methods=['POST'])
def actualizar_estadisticas_sub15(id):
    partidos_jugados = request.form.get('partidos_jugados', 0)
    goles_recibidos = request.form.get('goles_recibidos', 0)
    intercepciones = request.form.get('intercepciones', 0)
    tarjetas_amarillas = request.form.get('tarjetas_amarillas', 0)
    tarjetas_rojas = request.form.get('tarjetas_rojas', 0)
    goles = request.form.get('goles', 0)
    asistencias = request.form.get('asistencias', 0)
    goles_sin_penalti = request.form.get('goles_sin_penalti', 0)

    cursor = db.cursor()
    cursor.execute("""
        UPDATE sub15
        SET partidos_jugados = %s, goles_recibidos = %s, intercepciones = %s, tarjetas_amarillas = %s, tarjetas_rojas = %s,
            goles = %s, asistencias = %s, goles_sin_penalti = %s
        WHERE id = %s
    """, (partidos_jugados, goles_recibidos, intercepciones, tarjetas_amarillas, tarjetas_rojas, goles, asistencias, goles_sin_penalti, id))
    db.commit()
    cursor.close()
    
    return redirect(url_for('jugador_sub15', id=id))


# Ruta para mostrar los jugadores de la categoría sub18
@app.route('/sub18')
def sub18():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM sub18")
    jugadores = cursor.fetchall()
    cursor.close()
    return render_template('sub18.html', jugadores=jugadores, fecha_actual=date.today(), date=date,timedelta=timedelta)

@app.route('/eliminar_jugador_sub18/<int:jugador_id>', methods=['POST'])
def eliminar_jugador_sub18(jugador_id):
    cursor = db.cursor()

    # Primero eliminar documentos asociados al jugador
    cursor.execute("DELETE FROM documentos_sub18 WHERE jugador_id = %s", (jugador_id,))
    
    # Luego eliminar el jugador
    cursor.execute("DELETE FROM sub18 WHERE id = %s", (jugador_id,))
    db.commit()
    cursor.close()
    return redirect(url_for('sub18'))


# Ruta para ver un jugador específico de sub18
@app.route('/jugador_sub18/<int:id>', methods=['GET', 'POST'])
def jugador_sub18(id):
    cursor = db.cursor(dictionary=True)
    
    # Obtener información del jugador
    cursor.execute("SELECT * FROM sub18 WHERE id = %s", (id,))
    jugador = cursor.fetchone()

    if request.method == 'POST':
        # Manejar carga de documentos
        if 'documento' in request.files:
            documento = request.files['documento']
            if documento and documento.filename.endswith('.pdf'):
                filename = f"{id}_{documento.filename}"
                documento.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                cursor.execute("INSERT INTO documentos_sub18 (jugador_id, titulo_documento, ruta_documento) VALUES (%s, %s, %s)",
                               (id, documento.filename, filename))
                db.commit()
                cursor.close()
                return redirect(url_for('jugador_sub18', id=id))

    # Calcular el rendimiento del jugador
    def calcular_rendimiento(jugador):
        partidos_jugados = jugador.get('partidos_jugados', 0)
        goles = jugador.get('goles', 0)
        asistencias = jugador.get('asistencias', 0)
        goles_sin_penalti = jugador.get('goles_sin_penalti', 0)
        goles_recibidos = jugador.get('goles_recibidos', 0)
        intercepciones = jugador.get('intercepciones', 0)
        
        # Fórmula de rendimiento para el arquero
        if jugador.get('posicion') == 'Arquero':
            rendimiento = (intercepciones * 0.4 - goles_recibidos * 0.6) / max(partidos_jugados, 1)
        else:
            # Fórmula de rendimiento para jugadores de campo
            rendimiento = (goles * 0.5 + asistencias * 0.3 + goles_sin_penalti * 0.2) / max(partidos_jugados, 1)
        
        # Determinar calificación
        if rendimiento > 2:
            calificacion = "Excelente"
        elif rendimiento > 1.5:
            calificacion = "Muy Bueno"
        elif rendimiento > 1:
            calificacion = "Bueno"
        else:
            calificacion = "Mejorable"
        
        return {'puntaje': round(rendimiento, 2), 'calificacion': calificacion}
    
    rendimiento = calcular_rendimiento(jugador)
    
    # Obtener documentos del jugador
    cursor.execute("SELECT * FROM documentos_sub18 WHERE jugador_id = %s", (id,))
    documentos = cursor.fetchall()
    
    cursor.close()
    return render_template('jugador_sub18.html', jugador=jugador, rendimiento=rendimiento, documentos=documentos)

@app.route('/descargar_documento_sub18/<filename>')
def descargar_documento_sub18(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Ruta para actualizar estadísticas de jugadores sub18
@app.route('/actualizar_estadisticas_sub18/<int:id>', methods=['POST'])
def actualizar_estadisticas_sub18(id):
    partidos_jugados = request.form.get('partidos_jugados', 0)
    goles_recibidos = request.form.get('goles_recibidos', 0)
    intercepciones = request.form.get('intercepciones', 0)
    tarjetas_amarillas = request.form.get('tarjetas_amarillas', 0)
    tarjetas_rojas = request.form.get('tarjetas_rojas', 0)
    goles = request.form.get('goles', 0)
    asistencias = request.form.get('asistencias', 0)
    goles_sin_penalti = request.form.get('goles_sin_penalti', 0)

    cursor = db.cursor()
    cursor.execute("""
        UPDATE sub18
        SET partidos_jugados = %s, goles_recibidos = %s, intercepciones = %s, tarjetas_amarillas = %s, tarjetas_rojas = %s,
            goles = %s, asistencias = %s, goles_sin_penalti = %s
        WHERE id = %s
    """, (partidos_jugados, goles_recibidos, intercepciones, tarjetas_amarillas, tarjetas_rojas, goles, asistencias, goles_sin_penalti, id))
    db.commit()
    cursor.close()
    
    return redirect(url_for('jugador_sub18', id=id))

if __name__ == '__main__':
    app.run(debug=True)
