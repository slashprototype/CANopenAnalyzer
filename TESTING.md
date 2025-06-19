# Testing Instructions

## Pruebas de Integración USB Serial Interface

Hemos integrado exitosamente tu `analyzer.py` en el proyecto CANopenAnalyzer. Aquí tienes varias opciones para probar la funcionalidad:

### 🧪 Prueba 1: Test Básico de Interfaz (Línea de Comandos)

Ejecuta el test básico para verificar la conectividad:

```bash
cd CANopenAnalyzer
python test_usb_serial.py
```

**Qué hace:**
- Te pide el puerto COM y baudrate
- Se conecta a la interfaz USB-Serial
- Monitorea mensajes CAN en tiempo real
- Envía solicitudes SDO de prueba cada 10 segundos
- Muestra estadísticas cada 5 segundos

### 🎯 Prueba 2: Monitor Module GUI (Solo Monitor)

Ejecuta solo el módulo de monitoreo con GUI:

```bash
cd CANopenAnalyzer
python test_monitor.py
```

**Qué hace:**
- Abre una GUI con solo el módulo de monitoreo
- Puedes conectar/desconectar desde la interfaz
- Tabla en tiempo real de mensajes CAN
- Filtros por Node ID
- Estadísticas de velocidad y contadores

### 🚀 Prueba 3: Aplicación Completa

Ejecuta la aplicación completa con todas las pestañas:

```bash
cd CANopenAnalyzer
python src/main.py
```

**Qué incluye:**
- Pestaña "Interface": Configuración de interfaces CAN
- Pestaña "Monitor": Tu analyzer.py integrado
- Otras pestañas: Variables, NMT, etc.

### ⚙️ Configuración Previa

1. **Actualizar COM Port**: Edita `config/app_config.json`:
   ```json
   {
     "can": {
       "interface": "usb_serial",
       "com_port": "COM3",    // <- Cambia por tu puerto
       "serial_baudrate": 115200
     }
   }
   ```

2. **Hardware**: Asegúrate de que tu convertidor CAN-USB esté conectado

3. **Dispositivos CAN**: Conecta dispositivos CANopen para ver mensajes

### 📊 Qué Esperar Ver

**Mensajes Típicos:**
```
[14:23:45.123] COB-ID: 0x701 | Node:  1 | Type: Heartbeat  | Data: 05
[14:23:45.150] COB-ID: 0x181 | Node:  1 | Type: PDO1      | Data: 12 34 56 78
[14:23:45.200] COB-ID: 0x581 | Node:  1 | Type: SDO       | Data: 43 00 10 00 02 00 00 00
```

**Funcionalidades Integradas:**
- ✅ Protocolo 0xAA/0x55 de tu analyzer.py
- ✅ Parsing de mensajes CANopen
- ✅ Detección de tipos de mensaje (SDO, PDO, Heartbeat, etc.)
- ✅ Interfaz gráfica tiempo real
- ✅ Filtros y estadísticas
- ✅ Envío de comandos SDO

### 🔧 Troubleshooting

**Error "COM port not available":**
- Verifica que el puerto COM esté correcto
- Cierra otras aplicaciones que usen el puerto
- Verifica drivers del convertidor USB-Serial

**No se ven mensajes:**
- Verifica que hay dispositivos CANopen activos en la red
- Comprueba la velocidad de baudrate del CAN bus
- Verifica conexiones físicas CAN H/L

**Error de import:**
- Asegúrate de ejecutar desde el directorio CANopenAnalyzer
- Verifica que pyserial esté instalado: `pip install pyserial`

### 📝 Logs

Los logs se guardan en `logs/` y muestran:
- Conexiones/desconexiones
- Errores de protocolo
- Estadísticas de mensajes
- Debug de la interfaz USB-Serial

### 🎛️ Personalización

Para probar con diferentes configuraciones, modifica los archivos:

- `config/app_config.json` - Configuración global
- `test_usb_serial.py` - Test básico personalizable
- `test_monitor.py` - GUI simple personalizable

¡La integración mantiene toda la funcionalidad de tu `analyzer.py` original pero ahora está completamente integrada en el sistema modular del CANopenAnalyzer! 🎉
