import streamlit as st
import pandas as pd
from simulation import SimulationEnvironment # Importa tu clase de simulación
# Asegúrate de importar TODOS los tipos necesarios de models
from models import ProductionStatus, PurchaseStatus, ProductType

# --- Inicialización y Gestión del Estado ---
def initialize_simulation():
    """Inicializa la simulación si no existe en el estado de la sesión."""
    if 'sim' not in st.session_state:
        st.info("Inicializando entorno de simulación...")
        try:
            sim_env = SimulationEnvironment("config_initial.json")
            st.session_state.sim = sim_env
            # Iniciar procesos SimPy que corren continuamente
            st.session_state.sim.env.process(st.session_state.sim.daily_demand_generator())
            # Inicializar variables de estado de la UI
            st.session_state.current_day = sim_env.sim_start_day
            st.session_state.selected_orders_to_release = set() # Inicializa el set para la selección
            print("Simulation initialized and stored in session state.")
            st.success("Entorno de simulación listo.")
        except Exception as e:
            st.error(f"Error fatal al inicializar la simulación: {e}")
            st.stop()

# --- Funciones Callback para Botones ---
def advance_day_callback():
    """Callback para el botón 'Avanzar Día'."""
    if 'sim' in st.session_state:
        try:
            current_day_before_run = st.session_state.current_day
            print(f"UI: Requesting run_day from day {current_day_before_run}")
            st.session_state.sim.run_day()
            st.session_state.current_day = st.session_state.sim.current_day # Actualiza día después de correr
            print(f"UI: Day advanced to {st.session_state.current_day}")
            st.success(f"Simulación avanzada al final del día {current_day_before_run}.")
        except Exception as e:
            st.error(f"Error durante la simulación del día: {e}")
    else:
        st.error("La simulación no está inicializada.")

def release_orders_callback():
    """Callback para el botón 'Liberar Seleccionados'."""
    if 'sim' in st.session_state and 'selected_orders_to_release' in st.session_state:
        sim = st.session_state.sim
        orders_to_process = list(st.session_state.selected_orders_to_release)
        released_count = 0
        errors = []
        print(f"UI: Attempting to release IDs: {orders_to_process}")

        # Modifica sim.release_order para devolver True/False o manejar excepciones
        def try_release(order_id):
             try:
                 return sim.release_order(order_id) # Asume que devuelve True/False
             except Exception as e:
                 errors.append(f"Excepción liberando orden {order_id}: {e}")
                 return False # Considera la excepción como fallo

        for order_id in orders_to_process:
             if try_release(order_id):
                 released_count += 1
             #else: # Opcional: añadir a errores si devuelve False
             #    errors.append(f"No se pudo liberar orden {order_id} (ya procesada?).")


        if released_count > 0:
            st.success(f"Solicitud de liberación enviada para {released_count} pedido(s).")
        if errors:
            for error in errors:
                st.warning(error)

        # Limpiar la selección después del intento
        st.session_state.selected_orders_to_release = set()
        print("UI: Selection cleared after release attempt.")
    else:
        st.warning("No hay pedidos seleccionados para liberar o la simulación no está lista.")


def create_purchase_order_callback():
    """Callback llamado cuando se envía el formulario de compra."""
    if 'sim' in st.session_state:
        sim = st.session_state.sim
        product_id = st.session_state.get('purchase_product_id')
        supplier_id = st.session_state.get('purchase_supplier_id')
        quantity = st.session_state.get('purchase_quantity', 0)

        if product_id and supplier_id and quantity > 0:
            try:
                print(f"UI: Requesting creation of PO: Prod={product_id}, Supp={supplier_id}, Qty={quantity}")
                new_po = sim.create_purchase_order(supplier_id, product_id, quantity)
                if new_po:
                    st.success(f"Orden de Compra {new_po.id} creada exitosamente.")
                    # No necesitas rerun aquí porque el form ya lo causa
                else:
                    st.error("No se pudo crear la Orden de Compra (verifique logs).")
            except Exception as e:
                st.error(f"Error al crear la Orden de Compra: {e}")
        else:
            st.warning("Por favor, seleccione un producto, proveedor y cantidad válida (>0).")
    else:
        st.error("La simulación no está inicializada.")

# --- Renderizado de la Interfaz de Usuario ---

st.set_page_config(layout="wide")
st.title("Interfaz del Simulador de Producción 3D")

# Inicializar simulación al principio
initialize_simulation()

# Acceder a la instancia de simulación desde el estado de la sesión
# Comprobar si la simulación se inicializó correctamente
if 'sim' not in st.session_state:
    st.error("La simulación no se pudo inicializar. Por favor, revise la consola.")
    st.stop() # Detener la ejecución si no hay simulación
sim = st.session_state.sim

# --- Header: Día Actual y Botón de Avanzar ---
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.header(f"Día de Simulación Actual: {st.session_state.get('current_day', 'N/A')}")
with col_head2:
    st.button("Avanzar 1 Día >>", on_click=advance_day_callback, key="advance_button")

st.divider()

# --- Layout Principal (dos columnas) ---
col_izq, col_der = st.columns(2)

with col_izq:
    # --- Panel Pedidos Pendientes ---
    st.subheader("📦 Pedidos de Fabricación Pendientes")
    pending_orders = [o for o in sim.production_orders if o.status == "pendiente"]

    if not pending_orders:
        st.info("No hay pedidos de fabricación pendientes.")
    else:
        current_selection_set = st.session_state.setdefault('selected_orders_to_release', set())
        # --- INICIO: BUCLE PARA PEDIDOS PENDIENTES ---
        for order in pending_orders:
            product = sim.get_product(order.product_id)
            product_name = product.name if product else f"ID {order.product_id}"

            col_a, col_b, col_c = st.columns([2,1,1])
            with col_a:
                 st.write(f"**ID {order.id}:** {order.quantity} x {product_name}")
            with col_b:
                 st.write(f"Creado Día: {order.creation_date}")
            with col_c:
                 is_selected = order.id in current_selection_set
                 selected = st.checkbox("Liberar", key=f"select_{order.id}", value=is_selected)
                 # Actualizar el set si el estado del checkbox cambió
                 if selected and not is_selected:
                     current_selection_set.add(order.id)
                 elif not selected and is_selected:
                     current_selection_set.discard(order.id)

            bom = sim.get_bom(order.product_id)
            if bom:
                with st.expander(f"Ver Materiales Requeridos (Pedido {order.id})"):
                    bom_data = []
                    for item in bom:
                        mat_product = sim.get_product(item.material_id)
                        mat_name = mat_product.name if mat_product else f"ID {item.material_id}"
                        total_needed = item.quantity * order.quantity
                        current_stock = sim.inventory.get(item.material_id, 0)
                        bom_data.append({
                            "Material ID": item.material_id, "Nombre": mat_name,
                            "Nec./Unidad": item.quantity, "Total Nec.": total_needed,
                            "Stock": current_stock, "Faltante (Pedido)": max(0, total_needed - current_stock)
                        })
                    if bom_data:
                        bom_df = pd.DataFrame(bom_data)
                        st.dataframe(bom_df, hide_index=True, use_container_width=True)
                    else:
                        st.info("No se pudieron obtener detalles del BOM.")
            st.markdown("---")
        # --- FIN: BUCLE PARA PEDIDOS PENDIENTES ---

        # --- BOTÓN DE LIBERAR (FUERA DEL BUCLE) ---
        st.button("Liberar Seleccionados",
                  on_click=release_orders_callback,
                  key="release_button",
                  disabled=not current_selection_set # Deshabilitar si no hay nada seleccionado
                 )

    st.divider()

    # --- Panel Pedidos Liberados/En Progreso ---
    st.subheader("🏭 Pedidos en Cola / Producción")
    active_orders = [o for o in sim.production_orders if o.status in ["liberado", "en_progreso"]]
    if not active_orders:
        st.info("No hay pedidos liberados o en producción.")
    else:
        for order in active_orders:
            product = sim.get_product(order.product_id)
            product_name = product.name if product else f"ID {order.product_id}"
            st.write(f"**ID {order.id}:** {order.quantity} x {product_name} - Estado: **{order.status.upper()}**")
            bom = sim.get_bom(order.product_id)
            if bom:
                with st.expander(f"Ver Materiales Requeridos (Pedido {order.id})"):
                   bom_data = []
                   for item in bom:
                       mat_product = sim.get_product(item.material_id)
                       mat_name = mat_product.name if mat_product else f"ID {item.material_id}"
                       total_needed = item.quantity * order.quantity
                       current_stock = sim.inventory.get(item.material_id, 0)
                       bom_data.append({
                           "Material ID": item.material_id, "Nombre": mat_name,
                           "Nec./Unidad": item.quantity, "Total Nec.": total_needed,
                           "Stock": current_stock, "Faltante (Pedido)": max(0, total_needed - current_stock)
                       })
                   if bom_data:
                        bom_df = pd.DataFrame(bom_data)
                        st.dataframe(bom_df, hide_index=True, use_container_width=True)
                   else:
                        st.info("No se pudieron obtener detalles del BOM.")
            st.markdown("---")

with col_der:
    # --- Panel Inventario ---
    st.subheader("📊 Inventario Actual")
    inventory_data = []
    for prod_id, quantity in sorted(sim.inventory.items()):
        product = sim.get_product(prod_id)
        if product:
            inventory_data.append({
                "ID": prod_id, "Nombre Producto": product.name,
                "Tipo": product.type.capitalize(), "Cantidad": quantity
            })
    if inventory_data:
        inventory_df = pd.DataFrame(inventory_data)
        # Formatear columnas si es necesario (opcional)
        st.dataframe(inventory_df, hide_index=True, use_container_width=True,
                     column_config={"ID": st.column_config.NumberColumn(format="%d"),
                                     "Cantidad": st.column_config.NumberColumn(format="%d")})
    else:
        st.warning("Inventario vacío o no disponible.")

    st.divider()

    # --- Panel Faltantes Globales ---
    st.subheader("⚠️ Faltantes de Materiales")
    orders_for_shortage_calc = [o for o in sim.production_orders if o.status in ["liberado", "pendiente"]]
    shortages = sim.calculate_shortages(orders_for_shortage_calc)

    if not shortages:
        st.success("No hay faltantes de materiales críticos para los pedidos considerados.")
    else:
        st.warning("Se detectan los siguientes faltantes:")
        shortage_data = []
        for mat_id, qty_short in shortages.items():
            product = sim.get_product(mat_id)
            product_name = product.name if product else f"ID {mat_id}"
            shortage_data.append({
                "ID Material": mat_id, "Nombre": product_name,
                "Cantidad Faltante": qty_short, "Stock Actual": sim.inventory.get(mat_id, 0)
            })
        shortage_df = pd.DataFrame(shortage_data)
        st.dataframe(shortage_df, hide_index=True, use_container_width=True,
                     column_config={"ID Material": st.column_config.NumberColumn(format="%d"),
                                     "Cantidad Faltante": st.column_config.NumberColumn(format="%d"),
                                     "Stock Actual": st.column_config.NumberColumn(format="%d")})

    st.divider()

    # --- Panel Compras ---
    st.subheader("🛒 Emitir Órdenes de Compra")
    with st.form("purchase_order_form", clear_on_submit=True):
        raw_materials = {p.id: p for p in sim.products.values() if p.type == "raw"}
        if not raw_materials:
            st.warning("No hay materias primas definidas en la configuración.")
            # Deshabilitar el resto del formulario si no hay materias primas
            st.form_submit_button("Emitir Orden de Compra", disabled=True)
        else:
            selected_product_id = st.selectbox(
                "Materia Prima:", options=list(raw_materials.keys()),
                format_func=lambda x: f"{raw_materials[x].name} (ID: {x})",
                key='purchase_product_id', index=0 # Seleccionar el primero por defecto
            )

            available_suppliers = {}
            if selected_product_id:
                suppliers_details = sim.get_supplier_details_for_product(selected_product_id)
                for sup_id, cost, lead_time in suppliers_details:
                    supplier = sim.get_supplier(sup_id)
                    if supplier:
                        available_suppliers[sup_id] = f"{supplier.name} ({cost:.2f}€, {lead_time}d)"

            selected_supplier_id = st.selectbox(
                "Proveedor:", options=list(available_suppliers.keys()),
                format_func=lambda x: available_suppliers.get(x, "N/A"),
                key='purchase_supplier_id',
                disabled=not available_suppliers,
                help="Solo se muestran proveedores que venden la materia prima seleccionada."
            )

            quantity_to_buy = st.number_input(
                "Cantidad:", min_value=1, value=10, step=10, # Poner un valor por defecto > 0
                key='purchase_quantity'
            )

            # Botón de Envío del Formulario
            submitted = st.form_submit_button("Emitir Orden de Compra", disabled=not selected_supplier_id) # Deshabilitar si no hay proveedor
            if submitted:
                # La lógica de creación se maneja en el callback global al detectar el submit
                 create_purchase_order_callback() # Llamar al callback


# --- Sidebar (Opcional) ---
st.sidebar.title("Opciones")
st.sidebar.info(f"Simulación en Día: {st.session_state.get('current_day', 'N/A')}")
# Aquí podrías añadir botones para reiniciar, guardar/cargar estado en el futuro