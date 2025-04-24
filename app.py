import streamlit as st
import pandas as pd
from simulation import SimulationEnvironment # Importa tu clase de simulación
# Añade ProductType aquí:
from models import ProductionStatus, PurchaseStatus, ProductType

# ... resto del código ...
# --- Inicialización y Gestión del Estado ---
# Usamos st.session_state para mantener la instancia de la simulación
# entre interacciones del usuario (reruns de Streamlit).

def initialize_simulation():
    """Inicializa la simulación si no existe en el estado de la sesión."""
    if 'sim' not in st.session_state:
        st.info("Inicializando entorno de simulación...")
        try:
            # Crear la instancia de la simulación
            sim_env = SimulationEnvironment("config_initial.json")
            # Guardarla en el estado de la sesión
            st.session_state.sim = sim_env
            # Iniciar procesos de SimPy que deben correr desde el principio
            st.session_state.sim.env.process(st.session_state.sim.daily_demand_generator())
            # Inicializar otras variables de estado de la UI si es necesario
            st.session_state.current_day = sim_env.sim_start_day
            st.session_state.selected_orders_to_release = set()
            print("Simulation initialized and stored in session state.") # Debug console
            st.success("Entorno de simulación listo.")
        except Exception as e:
            st.error(f"Error fatal al inicializar la simulación: {e}")
            st.stop() # Detiene la app si la inicialización falla


# --- Funciones Callback para Botones ---
# Estas funciones se ejecutarán cuando se haga clic en los botones correspondientes.

def advance_day_callback():
    """Callback para el botón 'Avanzar Día'."""
    if 'sim' in st.session_state:
        try:
            print(f"UI: Requesting run_day from day {st.session_state.current_day}")
            st.session_state.sim.run_day()
            # Actualizar el día en el estado de la sesión para que la UI lo refleje
            st.session_state.current_day = st.session_state.sim.current_day
            print(f"UI: Day advanced to {st.session_state.current_day}")
            st.success(f"Simulación avanzada al final del día {st.session_state.current_day - 1}.")
        except Exception as e:
            st.error(f"Error durante la simulación del día: {e}")
    else:
        st.error("La simulación no está inicializada.")

def release_orders_callback():
    """Callback para el botón 'Liberar Seleccionados'."""
    if 'sim' in st.session_state and 'selected_orders_to_release' in st.session_state:
        sim = st.session_state.sim
        released_count = 0
        errors = []
        # Iterar sobre los IDs seleccionados guardados en session_state
        for order_id in st.session_state.selected_orders_to_release:
            try:
                # Llamar al método de la simulación para liberar la orden
                sim.release_order(order_id) # El método interno ya verifica el estado
                # Nota: El método release_order imprime sus propios mensajes/logs
                released_count += 1 # Asumimos éxito si no hay excepción (mejorar sim.release_order para devolver bool?)
            except Exception as e: # O un error específico si lo defines
                errors.append(f"Error liberando orden {order_id}: {e}")

        if released_count > 0:
            st.success(f"Solicitud de liberación enviada para {released_count} pedido(s).")
        if errors:
            for error in errors:
                st.warning(error) # Muestra errores/advertencias si no se pudieron liberar
        # Limpiar la selección después del intento
        st.session_state.selected_orders_to_release = set()
    else:
        st.warning("No hay pedidos seleccionados para liberar o la simulación no está lista.")


def create_purchase_order_callback():
    """Callback llamado cuando se envía el formulario de compra."""
    if 'sim' in st.session_state:
        sim = st.session_state.sim
        # Obtener valores directamente de st.session_state (vinculados por 'key' en los widgets)
        product_id = st.session_state.get('purchase_product_id')
        supplier_id = st.session_state.get('purchase_supplier_id')
        quantity = st.session_state.get('purchase_quantity', 0)

        if product_id and supplier_id and quantity > 0:
            try:
                print(f"UI: Requesting creation of PO: Prod={product_id}, Supp={supplier_id}, Qty={quantity}")
                new_po = sim.create_purchase_order(supplier_id, product_id, quantity)
                if new_po:
                    st.success(f"Orden de Compra {new_po.id} creada exitosamente.")
                else:
                    # La función sim.create_purchase_order debería haber impreso un error
                    st.error("No se pudo crear la Orden de Compra (verifique consola/logs).")
            except Exception as e:
                st.error(f"Error al crear la Orden de Compra: {e}")
        else:
            st.warning("Por favor, seleccione un producto, proveedor y cantidad válida (>0).")
    else:
        st.error("La simulación no está inicializada.")


# --- Renderizado de la Interfaz de Usuario ---

st.set_page_config(layout="wide") # Usar ancho completo de la página
st.title("Interfaz del Simulador de Producción 3D")

# Asegurarse de que la simulación esté inicializada al cargar/refrescar la página
initialize_simulation()

# Acceder a la instancia de simulación desde el estado de la sesión
sim = st.session_state.sim

# --- Header: Día Actual y Botón de Avanzar ---
col1, col2 = st.columns([3, 1])
with col1:
    # Usamos el día guardado en session_state para mostrarlo
    st.header(f"Día de Simulación Actual: {st.session_state.get('current_day', 'N/A')}")
with col2:
    # Botón para avanzar el día, llama a la función callback al hacer clic
    st.button("Avanzar 1 Día >>", on_click=advance_day_callback, key="advance_button")

st.divider() # Separador visual

# --- Layout Principal (dos columnas) ---
col_izq, col_der = st.columns(2)

with col_izq:
    # --- Panel Pedidos Pendientes ---
    st.subheader("📦 Pedidos de Fabricación Pendientes")
    # Filtrar solo los pedidos con estado 'pendiente'
    pending_orders = [o for o in sim.production_orders if o.status == ProductionStatus.PENDIENTE]

    if not pending_orders:
        st.info("No hay pedidos de fabricación pendientes.")
    else:
        # Preparar datos para la tabla
        orders_data = []
        for order in pending_orders:
            product = sim.get_product(order.product_id)
            orders_data.append({
                "ID": order.id,
                "Producto": product.name if product else f"ID {order.product_id}",
                "Cantidad": order.quantity,
                "Fecha Creación": order.creation_date,
                "Seleccionar": False # Columna para el checkbox
            })
        orders_df = pd.DataFrame(orders_data)

        # Usar st.data_editor para permitir la selección directa en la tabla
        edited_df = st.data_editor(
            orders_df,
            column_config={
                "Seleccionar": st.column_config.CheckboxColumn(required=True, default=False),
                "ID": st.column_config.NumberColumn(disabled=True),
                "Producto": st.column_config.TextColumn(disabled=True),
                "Cantidad": st.column_config.NumberColumn(disabled=True),
                "Fecha Creación": st.column_config.NumberColumn(disabled=True),
            },
            disabled=["ID", "Producto", "Cantidad", "Fecha Creación"], # Columnas no editables
            hide_index=True,
            key="orders_editor" # Clave única para el editor
        )

        # Guardar los IDs de las filas seleccionadas en session_state
        selected_rows = edited_df[edited_df["Seleccionar"]]
        st.session_state.selected_orders_to_release = set(selected_rows["ID"])

        # Botón para liberar los seleccionados, llama al callback
        st.button("Liberar Seleccionados", on_click=release_orders_callback, key="release_button")

    st.divider()
     # --- Panel Pedidos Liberados/En Progreso --- (Añadido para más visibilidad)
    st.subheader("🏭 Pedidos en Cola / Producción")
    active_orders = [o for o in sim.production_orders if o.status in [ProductionStatus.LIBERADO, ProductionStatus.EN_PROGRESO]]
    if not active_orders:
        st.info("No hay pedidos liberados o en producción.")
    else:
        active_orders_data = []
        for order in active_orders:
            product = sim.get_product(order.product_id)
            active_orders_data.append({
                "ID": order.id,
                "Producto": product.name if product else f"ID {order.product_id}",
                "Cantidad": order.quantity,
                "Estado": order.status.upper(), # Mostrar estado
            })
        active_orders_df = pd.DataFrame(active_orders_data)
        st.dataframe(active_orders_df, hide_index=True, use_container_width=True)


with col_der:
    # --- Panel Inventario ---
    st.subheader("📊 Inventario Actual")
    inventory_data = []
    # Crear una lista de diccionarios para el DataFrame
    for prod_id, quantity in sorted(sim.inventory.items()): # Ordenar por ID
        product = sim.get_product(prod_id)
        if product: # Asegurarse que el producto existe en los datos maestros
            inventory_data.append({
                "ID": prod_id,
                "Nombre Producto": product.name,
                "Tipo": product.type.capitalize(),
                "Cantidad": quantity
            })
    if inventory_data:
        inventory_df = pd.DataFrame(inventory_data)
        st.dataframe(inventory_df, hide_index=True, use_container_width=True)
    else:
        st.warning("Inventario vacío o no disponible.")
    # TODO: Añadir cálculo de faltantes basado en pedidos liberados/pendientes


    st.divider()
    # --- Panel Compras ---
    st.subheader("🛒 Emitir Órdenes de Compra")
    # Usar un formulario para agrupar los widgets de compra
    with st.form("purchase_order_form", clear_on_submit=True):
        # app.py (línea ~221)

        # 1. Seleccionar Materia Prima
        # Compara directamente con la cadena "raw"
        raw_materials = {p.id: p for p in sim.products.values() if p.type == "raw"}
        if not raw_materials:
            st.warning("No hay materias primas definidas en la configuración.")

        else:
            selected_product_id = st.selectbox(
                "Materia Prima:",
                options=list(raw_materials.keys()),
                format_func=lambda x: f"{raw_materials[x].name} (ID: {x})",
                key='purchase_product_id' # Guarda la selección en session_state
            )

            # 2. Seleccionar Proveedor (filtrado por producto)
            available_suppliers = {}
            if selected_product_id:
                # Obtener proveedores que venden el producto seleccionado
                suppliers_details = sim.get_supplier_details_for_product(selected_product_id)
                for sup_id, cost, lead_time in suppliers_details:
                    supplier = sim.get_supplier(sup_id)
                    if supplier:
                        available_suppliers[sup_id] = f"{supplier.name} ({cost:.2f}€, {lead_time}d)"

            selected_supplier_id = st.selectbox(
                "Proveedor:",
                options=list(available_suppliers.keys()),
                format_func=lambda x: available_suppliers.get(x, "N/A"),
                key='purchase_supplier_id', # Guarda la selección
                disabled=not available_suppliers, # Deshabilitar si no hay proveedores
                help="Solo se muestran proveedores que venden la materia prima seleccionada."
            )

            # 3. Cantidad a Comprar
            quantity_to_buy = st.number_input(
                "Cantidad:",
                min_value=1,
                step=10, # Ajustar el paso si se compran en lotes
                key='purchase_quantity' # Guarda la selección
            )

            # 4. Botón de Envío del Formulario
            submitted = st.form_submit_button("Emitir Orden de Compra")
            if submitted:
                # Llamar al callback cuando el formulario se envía
                create_purchase_order_callback()

# --- Footer o Información Adicional (opcional) ---
st.sidebar.info("Controles de Simulación")
# Podrías añadir aquí opciones para reiniciar simulación, cargar/guardar estado, etc. en fases posteriores.
st.sidebar.write("Event Log (Próximamente)")