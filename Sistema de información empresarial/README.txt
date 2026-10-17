NUBEGESTIÓN PRO
Sistema de información empresarial para una pequeña empresa
===========================================================

FUNCIONES
- Inicio de sesión con contraseña protegida mediante hash.
- Panel con indicadores de ventas, ingresos, clientes, productos y stock bajo.
- Registro, búsqueda y eliminación segura de productos.
- Registro, búsqueda y eliminación segura de clientes.
- Registro de ventas con cálculo automático y descuento de inventario.
- Reportes de ventas e inventario valorizado.
- Exportación de productos, clientes y ventas a CSV como respaldo.
- Bitácora de acciones importantes.
- Base de datos SQLite en el equipo local y PostgreSQL al desplegar en nube.
- Diseño adaptable para computadora y celular.

REQUISITOS
- Python 3.10 o posterior.
- Internet para instalar las bibliotecas.

INSTALACIÓN EN WINDOWS (PowerShell)
1. Descomprime NubeGestion_Pro.zip.
2. Abre la carpeta NubeGestion_Pro.
3. En la barra de dirección del Explorador escribe powershell y presiona Enter.
4. Ejecuta:
   py -m venv .venv
5. Activa el entorno:
   .\.venv\Scripts\Activate.ps1

Si PowerShell bloquea la activación, ejecuta:
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
Y luego repite:
   .\.venv\Scripts\Activate.ps1

6. Instala las bibliotecas:
   python -m pip install -r requirements.txt
7. Inicia el sistema:
   python app.py
8. Abre en el navegador:
   http://127.0.0.1:5000

USUARIO DE DEMOSTRACIÓN LOCAL
Usuario: admin
Contraseña: Admin123!

La base de datos nubegestion.db se crea automáticamente.
Se cargan productos y clientes de ejemplo para la demostración.

IMPORTANTE SOBRE LA NUBE
Cuando se ejecuta en http://127.0.0.1:5000, el programa funciona localmente en la computadora.
Para demostrar computación en la nube real, se debe publicar el proyecto en un servicio de hosting
y conectar una base de datos PostgreSQL en la nube. El archivo render.yaml prepara la configuración
para Render, pero el despliegue requiere crear la cuenta, publicar el código y configurar ADMIN_PASSWORD.
No subas contraseñas reales ni información personal de clientes a un repositorio público.

SEGURIDAD
- Las contraseñas no se guardan en texto plano.
- La sesión se controla desde el servidor.
- Los formularios validan cantidades básicas.
- Las acciones principales quedan registradas.
- Exporta CSV periódicamente y guarda copias en un lugar seguro.
- Antes de usar en una empresa real, configura HTTPS, una SECRET_KEY propia,
  una contraseña de administrador fuerte y copias de seguridad automáticas.
