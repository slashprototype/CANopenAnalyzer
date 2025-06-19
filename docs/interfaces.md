# CAN Interfaces Documentation

Este proyecto incluye soporte para múltiples interfaces CAN a través de un sistema de interfaces modulares.

## Interfaces Disponibles

### 1. USB Serial Interface (USBSerialCANInterface)

Esta interfaz está basada en tu `analyzer.py` original y permite comunicación con convertidores CAN-USB que usan protocolo serial.

**Características:**
- Comunicación serial con convertidores CAN-USB
- Protocolo personalizado con headers 0xAA y terminadores 0x55
- Soporte para mensajes SDO de CANopen
- Buffer de mensajes con validación de integridad
- Threading para comunicación no bloqueante

**Configuración:**
```python
from config.app_config import AppConfig
from interfaces import InterfaceManager

config = AppConfig()
config.can_config.interface = "usb_serial"
config.can_config.com_port = "COM3"  # Windows
config.can_config.serial_baudrate = 115200

interface_manager = InterfaceManager(config, logger)
```

### 2. SocketCAN Interface (Wrapper)

Wrapper para la implementación original de CANopen que usa SocketCAN (Linux).

**Características:**
- Soporte para SocketCAN en Linux
- Integración con librerías python-can y canopen
- Compatibilidad con interfaces CAN estándar

## Uso Básico

### 1. Inicialización

```python
from config.app_config import AppConfig
from utils.logger import Logger
from interfaces import InterfaceManager

# Configuración
config = AppConfig()
logger = Logger()

# Crear manager de interfaces
interface_manager = InterfaceManager(config, logger)

# Inicializar la interfaz configurada
if not interface_manager.initialize_interface():
    print("Error inicializando interfaz")
    exit(1)
```

### 2. Conexión

```python
# Conectar a la interfaz
if not interface_manager.connect():
    print("Error conectando a la interfaz")
    exit(1)

print("Conectado exitosamente!")
```

### 3. Monitoreo de Mensajes

```python
def procesar_mensaje(mensaje):
    print(f"COB-ID: 0x{mensaje.cob_id:03X}")
    print(f"Tipo: {mensaje.message_type}")
    print(f"Datos: {[hex(b) for b in mensaje.data]}")

# Agregar callback para mensajes
interface_manager.add_message_callback(procesar_mensaje)

# Iniciar monitoreo
if interface_manager.start_monitoring():
    print("Monitoreo iniciado")
```

### 4. Envío de Datos (USB Serial)

```python
# Ejemplo: Leer registro SDO
sdo_request = {
    'index': 0x1000,        # Device type
    'subindex': 0x00,       # Subindex
    'size': 32,             # 4 bytes (32 bits)
    'value': 0,             # No aplica para lectura
    'is_read': True         # Operación de lectura
}

if interface_manager.send_data(sdo_request):
    print("Solicitud SDO enviada")

# Ejemplo: Escribir registro SDO
sdo_write = {
    'index': 0x1017,        # Heartbeat producer time
    'subindex': 0x00,       # Subindex
    'size': 16,             # 2 bytes (16 bits)
    'value': 1000,          # 1000 ms
    'is_read': False        # Operación de escritura
}

if interface_manager.send_data(sdo_write):
    print("Escritura SDO enviada")
```

### 5. Obtener Datos

```python
# Obtener diccionario de mensajes activos
mensajes = interface_manager.get_messages_dictionary()
for msg_id, data in mensajes.items():
    print(f"ID {msg_id}: {[hex(b) for b in data]}")

# Obtener historial de mensajes
historial = interface_manager.get_message_history()
for mensaje in historial[-10:]:  # Últimos 10 mensajes
    print(f"{mensaje.timestamp}: {mensaje.message_type}")
```

### 6. Cambio de Interfaz

```python
# Cambiar a otra interfaz
if interface_manager.switch_interface("socketcan"):
    print("Cambiado a SocketCAN")

# Ver interfaces disponibles
interfaces = interface_manager.get_available_interfaces()
print(f"Interfaces disponibles: {interfaces}")
```

## Configuración

### Archivo de Configuración (app_config.json)

```json
{
  "can": {
    "interface": "usb_serial",
    "channel": "can0",
    "bitrate": 125000,
    "timeout": 1.0,
    "com_port": "COM3",
    "serial_baudrate": 115200
  },
  "ui": {
    "theme": "light",
    "auto_refresh_rate": 100,
    "max_log_entries": 1000,
    "graph_update_rate": 500
  },
  "network": {
    "node_id": 1,
    "heartbeat_period": 1000,
    "sdo_timeout": 5.0,
    "emergency_timeout": 2.0
  }
}
```

## Ejemplos

### Ejemplo Completo

Ver `examples/interface_example.py` para un ejemplo completo de uso.

```bash
cd CANopenAnalyzer
python examples/interface_example.py
```

### Integración en GUI

El módulo `InterfaceConfigModule` proporciona una interfaz gráfica para configurar y controlar las interfaces CAN.

```python
from modules.interface_config_module import InterfaceConfigModule

# En tu aplicación Flet
interface_module = InterfaceConfigModule(page, config, logger)
interface_module.initialize()

# Obtener el manager para usar en otros módulos
interface_manager = interface_module.get_interface_manager()
```

## Estructura del Proyecto

```
src/
├── interfaces/
│   ├── __init__.py
│   ├── base_interface.py          # Interfaz base abstracta
│   ├── usb_serial_interface.py    # Tu analyzer.py adaptado
│   ├── interface_factory.py       # Factory para crear interfaces
│   └── interface_manager.py       # Manager para control unificado
├── modules/
│   └── interface_config_module.py # Módulo GUI para configuración
└── examples/
    └── interface_example.py       # Ejemplo de uso
```

## Protocolo USB Serial

El protocolo implementado en `USBSerialCANInterface` sigue el formato de tu `analyzer.py` original:

### Formato de Mensaje
```
[Header] [Type] [Frame ID LSB] [Frame ID MSB] [Payload...] [End]
  0xAA    0xCN        LSB           MSB         8 bytes    0x55
```

- **Header**: 0xAA (inicio de mensaje)
- **Type**: 0xCN donde N es la longitud del payload
- **Frame ID**: ID del frame CAN en little endian
- **Payload**: Datos del mensaje CAN (hasta 8 bytes)
- **End**: 0x55 (fin de mensaje)

### Comandos SDO Soportados

| Tamaño | Comando Escritura | Comando Lectura |
|--------|-------------------|-----------------|
| 1 byte | 0x2F             | 0x40            |
| 2 bytes| 0x2B             | 0x40            |
| 3 bytes| 0x27             | 0x40            |
| 4 bytes| 0x23             | 0x40            |

## Troubleshooting

### Error de Conexión Serial
- Verificar que el puerto COM esté disponible
- Comprobar que el baudrate coincida con el dispositivo
- Asegurar que no hay otras aplicaciones usando el puerto

### Mensajes Incompletos
- Verificar la conexión física
- Revisar la configuración de timeout
- Comprobar que el dispositivo esté enviando el protocolo correcto

### Error de Interfaz No Disponible
- Verificar que las dependencias estén instaladas (pyserial, python-can)
- En Linux, verificar permisos para acceder a dispositivos CAN
- Comprobar que el tipo de interfaz sea soportado en el sistema
