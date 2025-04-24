# Simulador de Producción de Impresoras 3D

Este proyecto es un simulador día a día del ciclo completo de una planta de fabricación de impresoras 3D, desarrollado como reto de programación. El enfoque principal está en la gestión de inventarios, compras y planificación de producción, permitiendo al usuario tomar decisiones como planificador.

## Objetivo

Desarrollar un software que simule la operación diaria de una fábrica, permitiendo al usuario:
*   Gestionar el inventario de materias primas y productos terminados.
*   Decidir qué pedidos de fabricación liberar a producción.
*   Decidir qué materias primas comprar, a qué proveedor y en qué cantidad.
*   Visualizar el estado de la producción, las compras y el inventario.

## Características Implementadas

*   Simulación basada en eventos discretos día a día (usando SimPy).
*   Modelado de datos para productos (materias primas, terminados), BOMs, proveedores e inventario (usando Pydantic).
*   Configuración inicial cargada desde `config_initial.json`.
*   Generación aleatoria (configurable) de demanda diaria de productos terminados.
*   Capacidad de producción diaria limitada.
*   Proceso de compra con lead times específicos por proveedor/producto.
*   Interfaz web interactiva (usando Streamlit) para visualizar el estado y tomar decisiones:
    *   Tablero con día actual.
    *   Panel de pedidos pendientes (con visualización de BOM requerido).
    *   Panel de pedidos en cola/producción.
    *   Panel de inventario actual.
    *   Panel de cálculo de faltantes de materiales.
    *   Panel para emitir órdenes de compra.
    *   Panel de órdenes de compra en tránsito.
    *   Botón para avanzar la simulación un día.
    *   Botón para liberar pedidos seleccionados a producción.

## Tecnologías Utilizadas

*   **Lenguaje:** Python 3.11+
*   **Simulación:** SimPy
*   **Modelado de Datos:** Pydantic
*   **Interfaz Web:** Streamlit
*   **Manipulación de Datos (Tablas UI):** Pandas
*   **Control de Versiones:** Git & GitHub

## Instalación

1.  **Clonar el repositorio:**
    ```bash
    git clone <URL_DE_TU_REPOSITORIO_EN_GITHUB>
    cd <NOMBRE_DE_LA_CARPETA_DEL_PROYECTO>
    ```
2.  **Crear un entorno virtual:** (Recomendado)
    ```bash
    python -m venv venv
    ```
3.  **Activar el entorno virtual:**
    *   Windows (cmd): `.\venv\Scripts\activate`
    *   Windows (PowerShell): `.\venv\Scripts\Activate.ps1`
    *   macOS/Linux: `source venv/bin/activate`
4.  **Instalar dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

## Uso

1.  Asegúrate de que tu entorno virtual esté activado.
2.  Ejecuta la aplicación Streamlit desde la carpeta raíz del proyecto:
    ```bash
    streamlit run app.py
    ```
3.  Se abrirá una pestaña en tu navegador web con la interfaz del simulador.
4.  Interactúa con la interfaz:
    *   Observa el estado inicial (Día 0, inventario, etc.).
    *   Usa el botón **"Avanzar 1 Día >>"** para progresar la simulación.
    *   Selecciona pedidos pendientes usando los checkboxes y haz clic en **"Liberar Seleccionados"**.
    *   Usa el formulario en **"Emitir Órdenes de Compra"** para comprar materias primas (observa el panel de faltantes como guía).
    *   Analiza los paneles de inventario, faltantes y órdenes en tránsito para tomar decisiones.

## Configuración Inicial

El comportamiento inicial de la simulación (productos, BOMs, proveedores, inventario inicial, capacidad, parámetros de demanda) se define en el archivo `config_initial.json`. Puedes modificar este archivo para probar diferentes escenarios antes de lanzar la aplicación.

## Estructura del Proyecto (Simplificada)
├── venv/ 
├── app.py
├── simulation.py 
├── models.py 
├── config_loader.py 
├── config_initial.json 
├── requirements.txt 
├── README.md 
└── .gitignore 