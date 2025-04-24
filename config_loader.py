import json
from typing import Dict, List, Tuple
# Asegúrate que models.py esté en el mismo directorio o sea accesible
from models import Product, Supplier, InventoryItem, BOMItem

def load_initial_config(filepath: str) -> Dict:
    """
    Carga la configuración inicial desde un archivo JSON.

    Args:
        filepath: Ruta al archivo JSON de configuración.

    Returns:
        Un diccionario conteniendo las listas de productos, proveedores,
        inventario inicial y parámetros de simulación.
        Ej: {'products': [...], 'suppliers': [...], 'initial_inventory': [...],
             'simulation_parameters': {...}, 'production_capacity': ...}
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Archivo de configuración no encontrado en {filepath}")
        return {}
    except json.JSONDecodeError:
        print(f"Error: El archivo de configuración {filepath} no es un JSON válido.")
        return {}

    # Validar y convertir los datos usando Pydantic (opcional pero recomendado)
    # Aquí simplemente extraemos, la validación ocurrirá si instancias los modelos
    initial_state = {
        "simulation_parameters": config_data.get("simulation_parameters", {}),
        "production_capacity": config_data.get("production_capacity_per_day", 0),
        "products": [],
        "suppliers": [],
        "initial_inventory": []
    }

    # Cargar productos
    for prod_data in config_data.get("products", []):
        bom_items = None
        if "bom" in prod_data and prod_data["bom"] is not None:
            bom_items = [BOMItem(**item) for item in prod_data["bom"]]
        initial_state["products"].append(Product(bom=bom_items, **prod_data))

    # Cargar proveedores
    for supp_data in config_data.get("suppliers", []):
         # Convertimos las keys del supply_details a int porque JSON las trata como string
         details = supp_data.get("supply_details", {})
         parsed_details = {int(k): tuple(v) for k, v in details.items()}
         supp_data['supply_details'] = parsed_details # Reemplaza con el diccionario parseado
         initial_state["suppliers"].append(Supplier(**supp_data))


    # Cargar inventario inicial
    for inv_data in config_data.get("initial_inventory", []):
        initial_state["initial_inventory"].append(InventoryItem(**inv_data))

    print(f"Configuración cargada desde {filepath}")
    return initial_state

# Ejemplo de cómo usarlo (puedes borrar o comentar esto más tarde)
if __name__ == "__main__":
    config = load_initial_config("config_initial.json")
    if config:
        print("\n--- Resumen Configuración ---")
        print(f"Capacidad Producción/día: {config['production_capacity']}")
        print(f"Número de tipos de productos definidos: {len(config['products'])}")
        print(f"Número de proveedores definidos: {len(config['suppliers'])}")
        print(f"Items iniciales en inventario: {len(config['initial_inventory'])}")
        # print("\nProductos:")
        # for p in config['products']:
        #     print(f"- {p.name} (ID: {p.id}, Tipo: {p.type})")
        # print("\nProveedores:")
        # for s in config['suppliers']:
        #      print(f"- {s.name} (ID: {s.id})")
        # print("\nInventario Inicial:")
        # for i in config['initial_inventory']:
        #      print(f"- Producto ID: {i.product_id}, Cantidad: {i.quantity}")