import simpy
import random
import json
from typing import Dict, List, Optional, Tuple

# Importa tus modelos y el cargador de configuración
from models import (
    Product, Supplier, InventoryItem, ProductionOrder, PurchaseOrder,
    Event, BOMItem, ProductType, ProductionStatus, PurchaseStatus
)
from config_loader import load_initial_config

class SimulationEnvironment:
    def __init__(self, config_filepath: str):
        print("Initializing Simulation Environment...")
        # Cargar configuración
        config = load_initial_config(config_filepath)
        if not config:
            raise ValueError("Failed to load configuration.")

        self.config = config
        self.params = config['simulation_parameters']
        self.sim_start_day = 0 # O leerlo de config si se añade
        self.current_day = self.sim_start_day

        # Inicializar SimPy
        self.env = simpy.Environment(initial_time=self.sim_start_day)

        # Cargar datos maestros
        self._load_master_data(config)

        # Inicializar estado de la simulación
        self._initialize_state(config)

        # Configurar recursos de SimPy
        self.production_capacity = simpy.Resource(
            self.env, capacity=config['production_capacity']
        )

        # Contadores para IDs únicos
        self.next_production_order_id = 1
        self.next_purchase_order_id = 1
        self.next_event_id = 1

        # Iniciar procesos principales (si los hay que corran siempre)
        # self.env.process(self.some_continuous_process())
        print("Simulation Environment Initialized.")

    def _load_master_data(self, config):
        """Carga productos y proveedores en diccionarios para acceso rápido."""
        self.products: Dict[int, Product] = {p.id: p for p in config['products']}
        self.suppliers: Dict[int, Supplier] = {s.id: s for s in config['suppliers']}
        print(f"Loaded {len(self.products)} products and {len(self.suppliers)} suppliers.")

    def _initialize_state(self, config):
        """Inicializa inventario, listas de pedidos y eventos."""
        self.inventory: Dict[int, int] = {item.product_id: item.quantity for item in config['initial_inventory']}
        # Asegurarse que todos los productos (incluyendo materias primas sin stock inicial) estén en el inventario con 0
        for prod_id in self.products:
            if prod_id not in self.inventory:
                 self.inventory[prod_id] = 0

        self.production_orders: List[ProductionOrder] = []
        self.purchase_orders: List[PurchaseOrder] = []
        self.events: List[Event] = []
        print(f"Initial inventory set for {len(self.inventory)} product IDs.")


    def log_event(self, event_type: str, details: Dict):
        """Registra un evento en la simulación."""
        event = Event(
            id=self.next_event_id,
            type=event_type,
            sim_day=int(self.env.now), # Día actual
            details=details
        )
        self.events.append(event)
        self.next_event_id += 1
        # print(f"Day {int(self.env.now)}: EVENT - {event_type} - {details}") # Debug

    # --- Funciones de Acceso a Datos ---
    def get_product(self, product_id: int) -> Optional[Product]:
        return self.products.get(product_id)

    def get_supplier(self, supplier_id: int) -> Optional[Supplier]:
        return self.suppliers.get(supplier_id)

    def get_bom(self, product_id: int) -> Optional[List[BOMItem]]:
        product = self.get_product(product_id)
        return product.bom if product and product.type == "finished" else None

    def get_supplier_details_for_product(self, product_id: int) -> List[Tuple[int, float, int]]:
        """Encuentra qué proveedores venden un producto y sus detalles (costo, lead_time)."""
        details = []
        for sup_id, supplier in self.suppliers.items():
            if product_id in supplier.supply_details:
                cost, lead_time = supplier.supply_details[product_id]
                details.append((sup_id, cost, lead_time))
        return details


    # --- Funciones de Manipulación de Estado ---
    def check_stock(self, product_id: int, quantity: int) -> bool:
        """Verifica si hay suficiente stock."""
        return self.inventory.get(product_id, 0) >= quantity

    def check_bom_stock(self, product_id: int, quantity: int) -> bool:
        """Verifica si hay stock para todos los materiales del BOM para una cantidad dada."""
        bom = self.get_bom(product_id)
        if not bom:
            print(f"Warning: No BOM found for product {product_id}")
            return False
        for item in bom:
            required = item.quantity * quantity
            if not self.check_stock(item.material_id, required):
                # print(f"Stock check failed for BOM of {product_id}: Need {required} of {item.material_id}, have {self.inventory.get(item.material_id, 0)}")
                return False
        return True

    def add_stock(self, product_id: int, quantity: int):
        """Añade stock al inventario."""
        if quantity < 0: return # No añadir negativo
        self.inventory[product_id] = self.inventory.get(product_id, 0) + quantity
        self.log_event("INVENTORY_INCREASE", {"product_id": product_id, "quantity": quantity, "new_level": self.inventory[product_id]})

    def remove_stock(self, product_id: int, quantity: int):
        """Quita stock del inventario. Asume que check_stock fue llamado antes."""
        if quantity < 0: return # No quitar negativo
        current_stock = self.inventory.get(product_id, 0)
        if current_stock >= quantity:
            self.inventory[product_id] = current_stock - quantity
            self.log_event("INVENTORY_DECREASE", {"product_id": product_id, "quantity": quantity, "new_level": self.inventory[product_id]})
        else:
            print(f"Error: Attempted to remove {quantity} of {product_id}, but only {current_stock} available.")
            # Podrías levantar una excepción aquí

    # --- Procesos de SimPy ---

    def daily_demand_generator(self):
        """Proceso SimPy que genera demanda cada día."""
        while True:
            day = int(self.env.now)
            # Generar demanda para productos terminados
            for prod_id, product in self.products.items():
                if product.type == "finished":
                    # Usar media y varianza de los parámetros
                    mean = self.params.get("demand_mean", 5)
                    variance = self.params.get("demand_variance", 2)
                    # Generar demanda (usar normal, asegurar >= 0)
                    # random.gauss puede dar negativos, clamp a 0
                    quantity_demanded = max(0, round(random.gauss(mean, variance**0.5)))

                    if quantity_demanded > 0:
                        new_order = ProductionOrder(
                            id=self.next_production_order_id,
                            creation_date=day,
                            product_id=prod_id,
                            quantity=quantity_demanded,
                            status="pendiente" # Estado inicial
                        )
                        self.production_orders.append(new_order)
                        self.next_production_order_id += 1
                        self.log_event("DEMAND_GENERATED", {"order_id": new_order.id, "product_id": prod_id, "quantity": quantity_demanded})

            # Esperar hasta el próximo día
            yield self.env.timeout(1)

    def production_process(self, order: ProductionOrder):
        """Proceso SimPy para fabricar un pedido de producción."""
        print(f"Day {int(self.env.now)}: Attempting production for Order {order.id} ({order.quantity}x{order.product_id})")
        bom = self.get_bom(order.product_id)
        if not bom:
            print(f"Error: Cannot produce Order {order.id}, no BOM found for {order.product_id}.")
            order.status = "cancelado" # O algún estado de error
            self.log_event("PRODUCTION_ERROR", {"order_id": order.id, "reason": "No BOM"})
            return # Termina el proceso para esta orden

        # --- Adquisición de Capacidad ---
        # Este bloque 'with' solicita el recurso. Si no está disponible,
        # el proceso se pausa aquí hasta que lo esté.
        with self.production_capacity.request() as req:
            yield req # Espera a que se conceda la capacidad
            print(f"Day {int(self.env.now)}: Capacity granted for Order {order.id}. Verifying materials again.")

            # --- Doble chequeo de materiales (CRÍTICO por concurrencia) ---
            materials_still_available = True
            required_materials = {}
            for item in bom:
                required = item.quantity * order.quantity
                required_materials[item.material_id] = required
                if not self.check_stock(item.material_id, required):
                    materials_still_available = False
                    break # Salir del bucle for si falta algo

            if materials_still_available:
                print(f"Day {int(self.env.now)}: Materials confirmed for Order {order.id}. Starting production.")
                order.status = "en_progreso"
                self.log_event("PRODUCTION_STARTED", {"order_id": order.id})

                # --- Consumo de materiales ---
                for material_id, qty_needed in required_materials.items():
                    self.remove_stock(material_id, qty_needed)

                # --- Simulación del tiempo de producción ---
                # En este modelo, la adquisición de capacidad representa el tiempo.
                # Si 1 unidad de capacidad = 1 unidad de producto/día, ya está modelado.
                # Podríamos añadir un timeout pequeño si fuera necesario modelar un tiempo *después* de consumir materiales.
                yield self.env.timeout(0.001) # Pequeña espera simbólica

                # --- Finalización ---
                self.add_stock(order.product_id, order.quantity) # Añadir producto terminado
                order.status = "completado"
                print(f"Day {int(self.env.now)}: Production completed for Order {order.id}.")
                self.log_event("PRODUCTION_COMPLETED", {"order_id": order.id})

            else:
                # Los materiales fueron consumidos por otro proceso mientras esperaba capacidad
                print(f"Day {int(self.env.now)}: Materials no longer available for Order {order.id} after waiting for capacity. Releasing capacity.")
                order.status = "liberado" # Volver a estado liberado para reintentar? O pendiente_material?
                self.log_event("PRODUCTION_HALTED", {"order_id": order.id, "reason": "Materials unavailable after wait"})
                # La capacidad se libera automáticamente al salir del 'with'

    def purchase_tracking_process(self, purchase_order: PurchaseOrder):
        """Proceso SimPy que sigue una orden de compra hasta su llegada."""
        supplier = self.get_supplier(purchase_order.supplier_id)
        prod_details = supplier.supply_details.get(purchase_order.product_id) if supplier else None

        if not prod_details:
             print(f"Error: Cannot track Purchase Order {purchase_order.id}, invalid supplier or product details.")
             purchase_order.status = "cancelada"
             self.log_event("PURCHASE_ERROR", {"po_id": purchase_order.id, "reason": "Invalid supplier/product details"})
             return

        cost, lead_time = prod_details
        purchase_order.estimated_delivery_date = purchase_order.emission_date + lead_time
        print(f"Day {int(self.env.now)}: Tracking Purchase Order {purchase_order.id} (Product {purchase_order.product_id}). Est. Delivery: Day {purchase_order.estimated_delivery_date}")
        purchase_order.status = "en_transito"

        # Esperar el tiempo de entrega
        yield self.env.timeout(lead_time)

        # Llegada
        arrival_day = int(self.env.now)
        purchase_order.actual_delivery_date = arrival_day
        purchase_order.status = "recibida"
        self.add_stock(purchase_order.product_id, purchase_order.quantity)
        print(f"Day {arrival_day}: Purchase Order {purchase_order.id} received.")
        self.log_event("PURCHASE_RECEIVED", {"po_id": purchase_order.id, "product_id": purchase_order.product_id, "quantity": purchase_order.quantity})


    # --- Control de la Simulación ---

    def check_and_start_production(self):
         """Revisa pedidos liberados y si hay material, inicia el proceso SimPy."""
         # Iterar sobre una copia para poder modificar la lista original si fuera necesario
         for order in list(self.production_orders):
             if order.status == "liberado":
                 print(f"Day {int(self.env.now)}: Checking materials for released Order {order.id} ({order.quantity}x{order.product_id})")
                 if self.check_bom_stock(order.product_id, order.quantity):
                     print(f"Day {int(self.env.now)}: Materials OK for Order {order.id}. Launching production process.")
                     # Iniciar el proceso SimPy para esta orden
                     self.env.process(self.production_process(order))
                     # Cambiar estado para evitar re-lanzamiento inmediato?
                     # El propio proceso lo cambia a 'en_progreso' si consigue capacidad
                 else:
                     print(f"Day {int(self.env.now)}: Insufficient materials for Order {order.id}.")
                     # Opcional: Log evento "MATERIAL_SHORTAGE_PRODUCTION"

    def run_day(self):
        """Avanza la simulación un día."""
        target_day = self.current_day + 1
        print(f"\n--- Starting Day {self.current_day} ---")

        # 1. (Implícito por el bucle en daily_demand_generator) Generar demanda para el día actual.
        #    Asegurarse que el proceso se inició.

        # 2. Revisar y lanzar producción para pedidos liberados con material disponible
        self.check_and_start_production()

        # 3. Ejecutar la simulación hasta el final del día
        print(f"Running simulation until end of Day {self.current_day} (Time: {target_day})...")
        self.env.run(until=target_day)

        # 4. Actualizar día actual
        self.current_day = target_day
        print(f"--- End of Day {self.current_day - 1} ---") # El día que acaba de terminar

    # --- Métodos para Interacción Externa (llamados por UI/API) ---

    def release_order(self, order_id: int):
        """Marca un pedido como listo para producción (si existe y está pendiente)."""
        order = next((o for o in self.production_orders if o.id == order_id), None)
        if order and order.status == "pendiente":
            order.status = "liberado"
            print(f"Order {order_id} released for production.")
            self.log_event("ORDER_RELEASED", {"order_id": order_id})
            # La producción se intentará iniciar en el próximo check_and_start_production()
        elif order:
            print(f"Warning: Order {order_id} is not pending (status: {order.status}). Cannot release.")
        else:
            print(f"Warning: Order {order_id} not found.")

    def create_purchase_order(self, supplier_id: int, product_id: int, quantity: int):
         """Crea una orden de compra y lanza su proceso de seguimiento."""
         supplier = self.get_supplier(supplier_id)
         product = self.get_product(product_id)
         if not supplier or not product or product.type != 'raw':
              print(f"Error: Invalid supplier ({supplier_id}) or raw material ({product_id}) for purchase.")
              return None
         if product_id not in supplier.supply_details:
             print(f"Error: Supplier {supplier_id} does not sell product {product_id}.")
             return None
         if quantity <= 0:
             print(f"Error: Purchase quantity must be positive ({quantity}).")
             return None

         cost, lead_time = supplier.supply_details[product_id]
         emission_day = int(self.env.now) # Día actual

         new_po = PurchaseOrder(
             id=self.next_purchase_order_id,
             supplier_id=supplier_id,
             product_id=product_id,
             quantity=quantity,
             emission_date=emission_day,
             status="emitida" # Estado inicial
         )
         self.purchase_orders.append(new_po)
         self.next_purchase_order_id += 1

         print(f"Day {emission_day}: Created Purchase Order {new_po.id} for {quantity}x{product_id} from Supplier {supplier_id}.")
         self.log_event("PURCHASE_ORDER_CREATED", {"po_id": new_po.id, "supplier_id": supplier_id, "product_id": product_id, "quantity": quantity})

         # Iniciar el proceso SimPy para seguir esta orden
         self.env.process(self.purchase_tracking_process(new_po))
         return new_po # Devuelve la orden creada
    # Dentro de la clase SimulationEnvironment en simulation.py

    def calculate_total_material_needs(self, orders: List[ProductionOrder]) -> Dict[int, int]:
        """Calcula la suma total de cada materia prima necesaria para una lista de pedidos."""
        total_needs = {}
        for order in orders:
            if order.status not in ["completado", "cancelado"]: # Considerar solo pedidos activos/pendientes
                bom = self.get_bom(order.product_id)
                if bom:
                    for item in bom:
                        needed = item.quantity * order.quantity
                        total_needs[item.material_id] = total_needs.get(item.material_id, 0) + needed
        return total_needs

    def calculate_shortages(self, orders_to_consider: List[ProductionOrder]) -> Dict[int, int]:
        """Calcula la cantidad faltante de cada materia prima para los pedidos dados."""
        total_needs = self.calculate_total_material_needs(orders_to_consider)
        shortages = {}
        for material_id, needed_qty in total_needs.items():
            available_qty = self.inventory.get(material_id, 0)
            shortage = max(0, needed_qty - available_qty) # Faltante es lo necesario menos lo disponible (si es positivo)
            if shortage > 0:
                shortages[material_id] = shortage
        return shortages


# --- Bloque para probar la simulación directamente (opcional) ---
if __name__ == "__main__":
    # Crear instancia de la simulación
    sim = SimulationEnvironment("config_initial.json")

    # Registrar el proceso de generación de demanda para que se ejecute
    sim.env.process(sim.daily_demand_generator())

    # Simular algunos días
    num_days_to_simulate = 7
    for day in range(num_days_to_simulate):
         # --- Decisiones del "Usuario" para Probar ---
         if day == 1:
             # Intentar liberar el primer pedido pendiente que se haya creado el día 0
             if sim.production_orders:
                 sim.release_order(sim.production_orders[0].id)

         if day == 2:
             # Intentar comprar 20 kits de piezas (ID 101) al proveedor de Kits (ID 201)
             sim.create_purchase_order(supplier_id=201, product_id=101, quantity=20)

         # --- Avanzar un día en la simulación ---
         sim.run_day()


    # --- Imprimir Estado Final (Ejemplo) ---
    print("\n--- Simulation Finished ---")
    print(f"Ended on Day: {sim.current_day}")
    print("\nFinal Inventory:")
    for prod_id, qty in sim.inventory.items():
         prod = sim.get_product(prod_id)
         if qty > 0: # Mostrar solo los que tienen stock
             print(f"- {prod.name if prod else f'ID {prod_id}'}: {qty}")

    print("\nProduction Orders Status:")
    for order in sim.production_orders:
         print(f"- Order {order.id} ({order.quantity}x{order.product_id}): {order.status}")

    # Al final del bloque if __name__ == "__main__":
    print("\nPurchase Orders Status:")
    for po in sim.purchase_orders:
        supplier_name = sim.get_supplier(po.supplier_id).name if sim.get_supplier(po.supplier_id) else f"ID {po.supplier_id}"
        product_name = sim.get_product(po.product_id).name if sim.get_product(po.product_id) else f"ID {po.product_id}"
        print(f"- PO {po.id} ({po.quantity}x {product_name} from {supplier_name}): Status {po.status}, Emitted Day {po.emission_date}, Est. Delivery Day {po.estimated_delivery_date}, Actual Delivery Day {po.actual_delivery_date}")
    # print("\nEvent Log:")
    # for event in sim.events:
    #     print(f"- Day {event.sim_day}: {event.type} - {event.details}")