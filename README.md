# CANopenAnalyzer
Flet CANopen General Purpose Analyzer

## 📋 Descripción

CANopenAnalyzer es una aplicación GUI multiplataforma desarrollada con Flet que proporciona capacidades avanzadas de monitoreo, análisis y manipulación de redes CANopen. Diseñada para ingenieros y desarrolladores que trabajan con sistemas embebidos basados en el protocolo CANopen.

**Nuevas Características:**
- ✨ **Soporte para múltiples interfaces CAN**: SocketCAN (Linux) y convertidores USB-Serial
- 🔌 **Interfaz USB-Serial integrada**: Adaptación del analyzer.py original para convertidores CAN-USB
- 🎛️ **Sistema de interfaces modulares**: Fácil intercambio entre diferentes métodos de comunicación CAN
- ⚙️ **Configuración flexible**: Soporte para diferentes tipos de hardware CAN

## 🎯 Objetivos del Proyecto

### Objetivo Principal
Desarrollar una herramienta integral de análisis CANopen que permita a los usuarios monitorear, diagnosticar y controlar dispositivos en una red CANopen de manera eficiente y user-friendly, con soporte para múltiples interfaces de hardware CAN.

### Objetivos Específicos

1. **Soporte Multi-Interfaz**
   - Compatibilidad con SocketCAN (Linux) y convertidores USB-Serial
   - Sistema de interfaces intercambiables en tiempo de ejecución
   - Configuración automática según el hardware disponible

2. **Monitoreo en Tiempo Real**
   - Captura y visualización de mensajes CANopen en tiempo real
   - Análisis de tráfico de red y estadísticas de comunicación
   - Detección automática de errores y anomalías en la red

2. **Manipulación de Variables CANopen**
   - Edición de variables críticas del protocolo CANopen
   - Control de estados NMT (Network Management)
   - Configuración de parámetros de Heartbeat de nodos

3. **Gestión de Object Dictionary**
   - Carga e interpretación de archivos OD.c
   - Extracción automática de información de variables
   - Mapeo de nombres de variables legibles

4. **Visualización de Datos**
   - Graficación individual de variables seleccionadas
   - Tendencias históricas y análisis temporal
   - Exportación de datos para análisis posterior

## 🚀 Características Principales

### 📊 Interfaz Modular
- **Arquitectura basada en pestañas** para organización eficiente
- **Módulos independientes** para diferentes funcionalidades
- **Interfaz responsive** adaptable a diferentes tamaños de pantalla

### 🔧 Módulos de Testing
- **Editor NMT**: Control de estados de red (Operational, Pre-operational, Stopped)
- **Configurador HB**: Modificación de períodos de Heartbeat de nodos
- **Lector OD**: Carga y análisis de Object Dictionary desde archivos .c
- **Monitor Variables**: Supervisión en tiempo real de variables específicas

### 📈 Sistema de Graficación
- **Gráficos individuales** para variables seleccionadas
- **Visualización en tiempo real** con actualización automática
- **Configuración personalizable** de escalas y períodos de muestreo
- **Exportación de gráficos** en múltiples formatos

### 🔍 Herramientas de Análisis
- **Decodificación automática** de mensajes CANopen
- **Filtrado avanzado** por COB-ID, Node-ID y tipo de mensaje
- **Estadísticas de red** (throughput, errores, latencia)
- **Logging configurable** para depuración y auditoría

## 🛠️ Arquitectura del Sistema

### Componentes Principales

```
CANopenAnalyzer/
├── src/
│   ├── main.py              # Punto de entrada principal
│   ├── analyzer/            # Motor de análisis CANopen
│   ├── interfaces/          # 🆕 Sistema de interfaces CAN modulares
│   │   ├── base_interface.py        # Interfaz base abstracta
│   │   ├── usb_serial_interface.py  # Interfaz USB-Serial (tu analyzer.py)
│   │   ├── interface_factory.py     # Factory para crear interfaces
│   │   └── interface_manager.py     # Manager unificado
│   ├── gui/                 # Componentes de interfaz gráfica
│   ├── modules/             # Módulos funcionales independientes
│   │   └── interface_config_module.py # 🆕 Configuración de interfaces
│   ├── utils/               # Utilidades y helpers
│   └── config/              # Configuraciones del sistema
├── examples/                # 🆕 Ejemplos de uso de interfaces
├── docs/                    # Documentación del proyecto
│   └── interfaces.md        # 🆕 Documentación de interfaces
└── tests/                   # Pruebas unitarias y de integración
```

### Tecnologías Base
- **Flet**: Framework para desarrollo de aplicaciones GUI multiplataforma
- **Python 3.8+**: Lenguaje de programación principal
- **CANopen**: Protocolo de comunicación industrial estándar
- **Threading**: Manejo de procesos concurrentes para análisis en tiempo real
- **PySerial**: 🆕 Comunicación con convertidores USB-Serial
- **python-can**: Soporte para interfaces CAN estándar

## 🔌 Interfaces CAN Soportadas

### USB-Serial Interface
Basada en tu `analyzer.py` original, proporciona comunicación con convertidores CAN-USB:
- ✅ Protocolo personalizado con headers 0xAA/0x55
- ✅ Soporte para mensajes SDO de CANopen
- ✅ Threading no bloqueante
- ✅ Validación de integridad de mensajes
- ✅ Windows/Linux compatible

### SocketCAN Interface (Linux)
Wrapper para la implementación original usando python-can:
- ✅ Soporte para SocketCAN en Linux
- ✅ Integración con librerías estándar
- ✅ Interfaces CAN nativas

### Uso Rápido
```python
from interfaces import InterfaceManager

# USB-Serial (Windows/Linux)
config.can_config.interface = "usb_serial"
config.can_config.com_port = "COM3"

# SocketCAN (Linux)
config.can_config.interface = "socketcan"
config.can_config.channel = "can0"

manager = InterfaceManager(config, logger)
manager.connect()
manager.start_monitoring()
```

📖 **Ver documentación completa**: [`docs/interfaces.md`](docs/interfaces.md)

## 📋 Requerimientos del Proyecto

### Requerimientos Funcionales

#### RF-001: Análisis de Red CANopen
- El sistema debe capturar y decodificar mensajes CANopen en tiempo real
- Debe identificar automáticamente tipos de mensaje (PDO, SDO, NMT, HB)
- Debe proporcionar estadísticas de red actualizadas continuamente

#### RF-002: Manipulación de Variables
- El sistema debe permitir edición de variables críticas CANopen
- Debe soportar control de estados NMT de nodos individuales
- Debe permitir configuración de parámetros de Heartbeat

#### RF-003: Gestión de Object Dictionary
- El sistema debe cargar archivos OD.c y extraer información de variables
- Debe mapear direcciones de memoria a nombres legibles
- Debe mantener una base de datos de variables conocidas

#### RF-004: Visualización de Datos
- El sistema debe generar gráficos individuales para variables seleccionadas
- Debe actualizar visualizaciones en tiempo real
- Debe permitir configuración de parámetros de graficación

#### RF-005: Interfaz Modular
- El sistema debe organizarse en módulos independientes
- Debe proporcionar navegación por pestañas
- Debe mantener estado independiente entre módulos

### Requerimientos No Funcionales

#### RNF-001: Rendimiento
- Procesamiento de mensajes con latencia < 10ms
- Actualización de GUI a 30 FPS mínimo
- Soporte para hasta 127 nodos CANopen simultáneos

#### RNF-002: Usabilidad
- Interfaz intuitiva para usuarios no expertos
- Configuración mediante asistentes paso a paso
- Documentación integrada y tooltips contextuales

#### RNF-003: Confiabilidad
- Manejo robusto de errores de comunicación
- Recuperación automática de conexiones perdidas
- Validación de datos de entrada

#### RNF-004: Portabilidad
- Compatibilidad con Windows, Linux y macOS
- Instalación mediante paquetes standalone
- Configuración mínima requerida

## 🔧 Instalación y Configuración

### Prerequisitos
```bash
# Python 3.8 o superior
python --version

# Pip para gestión de paquetes
pip --version
```

### Instalación
```bash
# Clonar el repositorio
git clone https://github.com/usuario/CANopenAnalyzer.git
cd CANopenAnalyzer

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar aplicación
python src/main.py
```

## 🚀 Uso Básico

### Inicio Rápido
1. **Configurar interfaz CAN**: Seleccionar puerto y velocidad de comunicación
2. **Cargar Object Dictionary**: Importar archivo OD.c del proyecto
3. **Iniciar monitoreo**: Activar captura de mensajes en tiempo real
4. **Configurar variables**: Seleccionar variables para graficación
5. **Analizar datos**: Utilizar herramientas de filtrado y análisis

### Módulos Principales
- **Monitor**: Visualización en tiempo real de tráfico CANopen
- **Variables**: Gestión y edición de variables de red
- **Gráficos**: Visualización temporal de datos seleccionados
- **Configuración**: Ajustes de sistema y preferencias

## 🤝 Contribución

### Guías de Desarrollo
- Seguir PEP 8 para estilo de código Python
- Documentar funciones con docstrings
- Incluir pruebas unitarias para nuevas funcionalidades
- Mantener compatibilidad con versiones anteriores

### Proceso de Contribución
1. Fork del repositorio
2. Crear rama para nueva funcionalidad
3. Implementar cambios con pruebas
4. Enviar Pull Request con descripción detallada

## 📝 Licencia

Este proyecto está licenciado bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 📞 Soporte

Para soporte técnico y reportes de bugs:
- **Issues**: [GitHub Issues](https://github.com/usuario/CANopenAnalyzer/issues)
- **Documentación**: [Wiki del proyecto](https://github.com/usuario/CANopenAnalyzer/wiki)
- **Email**: soporte@canopenanalyzer.com

---

**CANopenAnalyzer** - Herramienta profesional para análisis y control de redes CANopen