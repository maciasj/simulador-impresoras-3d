from pydantic import BaseModel, Field
from typing import List, Dict, Literal, Optional

# Tipos de productos (basado en Sección 5)
ProductType = Literal["raw", "finished"]

# Estados posibles para pedidos y órdenes (puedes añadir más)
ProductionStatus = Literal["pendiente", "liberado", "en_progreso", "completado", "cancelado"]
PurchaseStatus = Literal["emitida", "en_transito", "recibida", "cancelada"]

# Para representar un item en el Bill of Materials (BOM)
class BOMItem(BaseModel):
    material_id: int # ID del producto materia prima
    quantity: int

# Modelo para Productos (materias primas o terminados) (basado en Sección 4 y 5)
class Product(BaseModel):
    id: int
    name: str
    type: ProductType
    # El BOM solo aplica a productos terminados, lo hacemos opcional
    bom: Optional[List[BOMItem]] = None
    # Podrías añadir el tiempo de fabricación aquí si varía por producto

# Modelo para Proveedores (basado en Sección 4 y 5)
class Supplier(BaseModel):
    id: int
    name: str
    # Qué productos vende este proveedor (lista de IDs de producto)
    products_supplied: List[int] = Field(default_factory=list)
    # Costos y lead times podrían ser más complejos, ej. por producto
    # Simplificación inicial: un costo y lead time general o por producto específico
    # Ejemplo: un diccionario {product_id: (cost, lead_time)}
    # O la versión más simple del doc: asume que vende UN producto
    product_id: Optional[int] = None # ID del producto que vende (simple)
    unit_cost: Optional[float] = None # Costo por unidad (simple)
    lead_time: Optional[int] = None # Días (simple)
    # Estructura más flexible:
    supply_details: Dict[int, tuple[float, int]] = Field(default_factory=dict) # {prod_id: (cost, lead_time_days)}


# Modelo para Items en Inventario (basado en Sección 4 y 5)
class InventoryItem(BaseModel):
    product_id: int
    quantity: int = Field(ge=0) # Cantidad no puede ser negativa

# Modelo para Pedidos de Fabricación (PedidoFab) (basado en Sección 4)
class ProductionOrder(BaseModel):
    id: int
    creation_date: int # Día de creación (simulado)
    product_id: int   # ID del producto terminado a fabricar
    quantity: int
    status: ProductionStatus = "pendiente"

# Modelo para Órdenes de Compra (OrdenCompra) (basado en Sección 4)
class PurchaseOrder(BaseModel):
    id: int
    supplier_id: int
    product_id: int # ID del producto materia prima comprado
    quantity: int
    emission_date: int # Día de emisión (simulado)
    estimated_delivery_date: Optional[int] = None # Calculado: emission_date + lead_time
    actual_delivery_date: Optional[int] = None # Cuando realmente llega
    status: PurchaseStatus = "emitida"

# Modelo para Eventos (basado en Sección 4)
class Event(BaseModel):
    id: int
    type: str # Ej: "DEMANDA_GENERADA", "PRODUCCION_INICIADA", "COMPRA_RECIBIDA"
    sim_day: int # Día de la simulación en que ocurrió
    details: Dict # Un diccionario con detalles específicos del evento