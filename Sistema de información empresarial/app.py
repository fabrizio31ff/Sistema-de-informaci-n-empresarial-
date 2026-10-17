import os
import io
import csv
import secrets
from datetime import datetime, date
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, Response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "cambia-esta-clave-para-produccion-" + secrets.token_hex(8))

database_url = os.environ.get("DATABASE_URL", "sqlite:///nubegestion.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre_usuario = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(20), default="Administrador", nullable=False)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    def verificar_password(self, password):
        return check_password_hash(self.password_hash, password)


class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    documento = db.Column(db.String(30), default="")
    telefono = db.Column(db.String(40), default="")
    correo = db.Column(db.String(120), default="")
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)


class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    categoria = db.Column(db.String(80), default="General")
    precio = db.Column(db.Float, nullable=False, default=0)
    stock = db.Column(db.Integer, nullable=False, default=0)
    stock_minimo = db.Column(db.Integer, nullable=False, default=5)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)


class Venta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=True)
    total = db.Column(db.Float, nullable=False, default=0)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    cliente = db.relationship("Cliente", backref="ventas")
    usuario = db.relationship("Usuario", backref="ventas")


class DetalleVenta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    venta_id = db.Column(db.Integer, db.ForeignKey("venta.id"), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey("producto.id"), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    producto = db.relationship("Producto")
    venta = db.relationship("Venta", backref=db.backref("detalles", cascade="all, delete-orphan"))


class RegistroAccion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(80), nullable=False)
    accion = db.Column(db.String(200), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)


def registrar_accion(accion):
    nombre = session.get("usuario", "Sistema")
    db.session.add(RegistroAccion(usuario=nombre, accion=accion))
    db.session.commit()


def login_requerido(func):
    @wraps(func)
    def decorada(*args, **kwargs):
        if "usuario_id" not in session:
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return decorada


@app.context_processor
def datos_globales():
    return {"fecha_actual": date.today(), "usuario_actual": session.get("usuario")}


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        nombre = request.form.get("usuario", "").strip()
        password = request.form.get("password", "")
        usuario = Usuario.query.filter_by(nombre_usuario=nombre).first()
        if usuario and usuario.verificar_password(password):
            session.clear()
            session["usuario_id"] = usuario.id
            session["usuario"] = usuario.nombre_usuario
            session["rol"] = usuario.rol
            registrar_accion("Inicio de sesión")
            return redirect(url_for("inicio"))
        flash("Usuario o contraseña incorrectos.", "danger")
    return render_template("login.html")


@app.route("/salir")
def salir():
    if "usuario_id" in session:
        registrar_accion("Cierre de sesión")
    session.clear()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("login"))


@app.route("/")
@login_requerido
def inicio():
    productos = Producto.query.order_by(Producto.nombre.asc()).all()
    total_productos = Producto.query.count()
    total_clientes = Cliente.query.count()
    total_ventas = Venta.query.count()
    ingresos = db.session.query(db.func.coalesce(db.func.sum(Venta.total), 0)).scalar() or 0
    stock_bajo = Producto.query.filter(Producto.stock <= Producto.stock_minimo).order_by(Producto.stock.asc()).limit(8).all()
    ventas_recientes = Venta.query.order_by(Venta.fecha.desc()).limit(6).all()
    hoy_inicio = datetime.combine(date.today(), datetime.min.time())
    hoy_fin = datetime.combine(date.today(), datetime.max.time())
    ventas_hoy = Venta.query.filter(Venta.fecha >= hoy_inicio, Venta.fecha <= hoy_fin).count()
    ingresos_hoy = db.session.query(db.func.coalesce(db.func.sum(Venta.total), 0)).filter(Venta.fecha >= hoy_inicio, Venta.fecha <= hoy_fin).scalar() or 0
    return render_template("dashboard.html", total_productos=total_productos, total_clientes=total_clientes,
                           total_ventas=total_ventas, ingresos=ingresos, stock_bajo=stock_bajo,
                           ventas_recientes=ventas_recientes, ventas_hoy=ventas_hoy, ingresos_hoy=ingresos_hoy)


@app.route("/productos", methods=["GET", "POST"])
@login_requerido
def productos():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        categoria = request.form.get("categoria", "General").strip() or "General"
        try:
            precio = float(request.form.get("precio", "0"))
            stock = int(request.form.get("stock", "0"))
            stock_minimo = int(request.form.get("stock_minimo", "5"))
            if not nombre or precio < 0 or stock < 0 or stock_minimo < 0:
                raise ValueError
            producto = Producto(nombre=nombre, categoria=categoria, precio=precio, stock=stock, stock_minimo=stock_minimo)
            db.session.add(producto)
            db.session.commit()
            registrar_accion(f"Registró producto: {nombre}")
            flash("Producto registrado correctamente.", "success")
        except ValueError:
            flash("Verifica el nombre, precio y cantidades del producto.", "danger")
        return redirect(url_for("productos"))
    q = request.args.get("q", "").strip()
    consulta = Producto.query
    if q:
        consulta = consulta.filter(Producto.nombre.ilike(f"%{q}%") | Producto.categoria.ilike(f"%{q}%"))
    lista = consulta.order_by(Producto.nombre.asc()).all()
    return render_template("productos.html", productos=lista, q=q)


@app.route("/productos/<int:producto_id>/eliminar", methods=["POST"])
@login_requerido
def eliminar_producto(producto_id):
    producto = db.session.get(Producto, producto_id)
    if not producto:
        flash("No se encontró el producto.", "danger")
    elif DetalleVenta.query.filter_by(producto_id=producto_id).first():
        flash("No se puede eliminar: el producto tiene ventas registradas. Puedes dejar su stock en cero.", "warning")
    else:
        nombre = producto.nombre
        db.session.delete(producto)
        db.session.commit()
        registrar_accion(f"Eliminó producto: {nombre}")
        flash("Producto eliminado.", "success")
    return redirect(url_for("productos"))


@app.route("/clientes", methods=["GET", "POST"])
@login_requerido
def clientes():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        documento = request.form.get("documento", "").strip()
        telefono = request.form.get("telefono", "").strip()
        correo = request.form.get("correo", "").strip()
        if not nombre:
            flash("El nombre del cliente es obligatorio.", "danger")
        else:
            db.session.add(Cliente(nombre=nombre, documento=documento, telefono=telefono, correo=correo))
            db.session.commit()
            registrar_accion(f"Registró cliente: {nombre}")
            flash("Cliente registrado correctamente.", "success")
        return redirect(url_for("clientes"))
    q = request.args.get("q", "").strip()
    consulta = Cliente.query
    if q:
        consulta = consulta.filter(Cliente.nombre.ilike(f"%{q}%") | Cliente.documento.ilike(f"%{q}%"))
    lista = consulta.order_by(Cliente.nombre.asc()).all()
    return render_template("clientes.html", clientes=lista, q=q)


@app.route("/clientes/<int:cliente_id>/eliminar", methods=["POST"])
@login_requerido
def eliminar_cliente(cliente_id):
    cliente = db.session.get(Cliente, cliente_id)
    if not cliente:
        flash("No se encontró el cliente.", "danger")
    elif Venta.query.filter_by(cliente_id=cliente_id).first():
        flash("No se puede eliminar un cliente con ventas registradas.", "warning")
    else:
        nombre = cliente.nombre
        db.session.delete(cliente)
        db.session.commit()
        registrar_accion(f"Eliminó cliente: {nombre}")
        flash("Cliente eliminado.", "success")
    return redirect(url_for("clientes"))


@app.route("/ventas", methods=["GET", "POST"])
@login_requerido
def ventas():
    if request.method == "POST":
        cliente_id = request.form.get("cliente_id") or None
        producto_id = request.form.get("producto_id")
        try:
            cantidad = int(request.form.get("cantidad", "1"))
            producto = db.session.get(Producto, int(producto_id))
            cliente = db.session.get(Cliente, int(cliente_id)) if cliente_id else None
            if not producto or cantidad <= 0:
                raise ValueError
            if producto.stock < cantidad:
                flash(f"Stock insuficiente. Disponible: {producto.stock}.", "danger")
                return redirect(url_for("ventas"))
            venta = Venta(cliente=cliente, total=producto.precio * cantidad, usuario_id=session["usuario_id"])
            producto.stock -= cantidad
            db.session.add(venta)
            db.session.flush()
            detalle = DetalleVenta(venta_id=venta.id, producto_id=producto.id, cantidad=cantidad,
                                   precio_unitario=producto.precio, subtotal=producto.precio * cantidad)
            db.session.add(detalle)
            db.session.commit()
            registrar_accion(f"Registró venta #{venta.id} por S/ {venta.total:.2f}")
            flash(f"Venta #{venta.id} registrada. Total: S/ {venta.total:.2f}", "success")
        except (ValueError, TypeError):
            db.session.rollback()
            flash("Selecciona un producto y una cantidad válida.", "danger")
        return redirect(url_for("ventas"))
    lista_ventas = Venta.query.order_by(Venta.fecha.desc()).limit(100).all()
    lista_productos = Producto.query.filter(Producto.stock > 0).order_by(Producto.nombre.asc()).all()
    lista_clientes = Cliente.query.order_by(Cliente.nombre.asc()).all()
    return render_template("ventas.html", ventas=lista_ventas, productos=lista_productos, clientes=lista_clientes)


@app.route("/reportes")
@login_requerido
def reportes():
    ventas = Venta.query.order_by(Venta.fecha.desc()).limit(200).all()
    ingresos = db.session.query(db.func.coalesce(db.func.sum(Venta.total), 0)).scalar() or 0
    productos_valorizados = db.session.query(db.func.coalesce(db.func.sum(Producto.precio * Producto.stock), 0)).scalar() or 0
    return render_template("reportes.html", ventas=ventas, ingresos=ingresos, productos_valorizados=productos_valorizados)


@app.route("/seguridad")
@login_requerido
def seguridad():
    acciones = RegistroAccion.query.order_by(RegistroAccion.fecha.desc()).limit(30).all()
    return render_template("seguridad.html", acciones=acciones, database_type="PostgreSQL en nube" if "postgresql" in app.config["SQLALCHEMY_DATABASE_URI"] else "SQLite local")


@app.route("/exportar")
@login_requerido
def exportar():
    salida = io.StringIO()
    escritor = csv.writer(salida)
    tipo = request.args.get("tipo", "productos")
    if tipo == "clientes":
        escritor.writerow(["ID", "Nombre", "Documento", "Telefono", "Correo"])
        for x in Cliente.query.order_by(Cliente.id).all():
            escritor.writerow([x.id, x.nombre, x.documento, x.telefono, x.correo])
        nombre = "respaldo_clientes.csv"
    elif tipo == "ventas":
        escritor.writerow(["ID venta", "Fecha", "Cliente", "Total", "Usuario"])
        for x in Venta.query.order_by(Venta.fecha.desc()).all():
            escritor.writerow([x.id, x.fecha.strftime("%Y-%m-%d %H:%M"), x.cliente.nombre if x.cliente else "Venta general", f"{x.total:.2f}", x.usuario.nombre_usuario if x.usuario else ""])
        nombre = "respaldo_ventas.csv"
    else:
        escritor.writerow(["ID", "Producto", "Categoria", "Precio", "Stock", "Stock minimo"])
        for x in Producto.query.order_by(Producto.id).all():
            escritor.writerow([x.id, x.nombre, x.categoria, f"{x.precio:.2f}", x.stock, x.stock_minimo])
        nombre = "respaldo_productos.csv"
    contenido = "\ufeff" + salida.getvalue()
    registrar_accion(f"Exportó respaldo CSV: {tipo}")
    return Response(contenido, mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename={nombre}"})


@app.errorhandler(404)
def no_encontrado(error):
    return render_template("error.html", codigo=404, mensaje="La página que buscas no existe."), 404


@app.errorhandler(500)
def error_servidor(error):
    db.session.rollback()
    return render_template("error.html", codigo=500, mensaje="Ocurrió un error interno. Intenta nuevamente."), 500


def inicializar():
    with app.app_context():
        db.create_all()
        if not Usuario.query.filter_by(nombre_usuario=os.environ.get("ADMIN_USER", "admin")).first():
            usuario = Usuario(
                nombre_usuario=os.environ.get("ADMIN_USER", "admin"),
                password_hash=generate_password_hash(os.environ.get("ADMIN_PASSWORD", "Admin123!")),
                rol="Administrador"
            )
            db.session.add(usuario)
            db.session.commit()
        if Producto.query.count() == 0:
            db.session.add_all([
                Producto(nombre="Cuaderno universitario", categoria="Útiles", precio=8.50, stock=35, stock_minimo=8),
                Producto(nombre="Lapicero azul", categoria="Útiles", precio=1.50, stock=60, stock_minimo=15),
                Producto(nombre="Memoria USB 32 GB", categoria="Tecnología", precio=28.00, stock=9, stock_minimo=5),
                Producto(nombre="Mouse inalámbrico", categoria="Tecnología", precio=35.90, stock=4, stock_minimo=5),
            ])
        if Cliente.query.count() == 0:
            db.session.add_all([
                Cliente(nombre="María Quispe", documento="12345678", telefono="999111222", correo="maria@example.com"),
                Cliente(nombre="José Mamani", documento="87654321", telefono="988222333", correo="jose@example.com"),
            ])
        db.session.commit()


inicializar()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1", host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
