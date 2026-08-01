from datetime import  date, timedelta
import holidays


def calcular_dias_laborales(fecha_inicio: date, fecha_fin: date) -> int:
    """
    Calcula los días laborales entre dos fechas (excluyendo sábados, domingos y festivos).
    fecha_inicio: fecha de inicio (no se incluye en el conteo)
    fecha_fin: fecha final (se incluye en el conteo)
    """
    if fecha_inicio >= fecha_fin:
        return 0
    
    # Obtener festivos de Colombia
    co_holidays = holidays.Colombia(years=range(fecha_inicio.year, fecha_fin.year + 1))
    
    dias_laborales = 0
    fecha_actual = fecha_inicio + timedelta(days=1)  # Comenzar desde el día siguiente
    
    while fecha_actual <= fecha_fin:
        # Verificar si es día laboral (no es sábado, domingo ni festivo)
        if fecha_actual.weekday() < 5 and fecha_actual not in co_holidays:
            dias_laborales += 1
        fecha_actual += timedelta(days=1)
    
    return dias_laborales

def obtener_fecha_despues_dias_laborales(fecha_inicio: date, dias_laborales: int) -> date:
    """
    Calcula la fecha después de transcurridos un número de días laborales (excluyendo sábados, domingos y festivos).
    fecha_inicio: fecha de inicio (se incluye en el conteo)
    dias_laborales: número de días laborales a sumar
    """
    # Obtener festivos de Colombia
    co_holidays = holidays.Colombia(years=range(fecha_inicio.year, fecha_inicio.year + 1))
    
    fecha_actual = fecha_inicio
    dias_sumados = 0
    
    while dias_sumados < dias_laborales:
        fecha_actual += timedelta(days=1)
        
        # Verificar si es un día laboral (no es sábado, domingo ni festivo)
        if fecha_actual.weekday() < 5 and fecha_actual not in co_holidays:
            dias_sumados += 1
            
    return fecha_actual
