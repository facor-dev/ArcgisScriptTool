# -*- coding: utf-8 -*-
import arcpy
import os
from datetime import datetime, time

#--------------------------------------------------------------------------------------------------#
def normalizar_presion(valor):
    if not valor:
        return None
    valor = valor.strip().upper()
    if valor == "AP":
        # return "Alta Presión"
        return "50000"
    if valor == "MP":
        # return "Media Presión"
        return "5000"
    raise ValueError("El parámetro Presion debe ser 'AP' o 'MP'.")

def normalizar_zona(valor):
    if not valor:
        return None
    v = valor.strip().lower()
    if v == "zona comercial":
        return "ZONA COMERCIAL"
    if v == "zona no comercial":
        return "ZONA NO COMERCIAL"
    raise ValueError("El parámetro Zona debe ser 'Zona comercial' o 'Zona no comercial'.")

def obtener_datetime_inicio(fecha):
    return datetime.combine(fecha.date(), time.min)

def obtener_datetime_fin(fecha):
    return datetime.combine(fecha.date(), time.max)


def obtener_codigo_dominio_por_descripcion(feature_class, field_name, domain_name, descripcion):
    if not descripcion:
        return None
    desc = arcpy.Describe(feature_class)
    gdb = desc.path
    if not gdb:
        return None

    for domain in arcpy.da.ListDomains(gdb):
        if domain.name == domain_name and domain.domainType.lower() in ("coded", "codedvalue"):
            # domain.codedValues es dict {code: desc}
            for code, desc_val in domain.codedValues.items():
                if str(desc_val).strip().lower() == str(descripcion).strip().lower():
                    return code
    return None

def chunks(lista, size):
    for i in range(0, len(lista), size):
        yield lista[i:i + size]

def sql_in_text(field_name, values):
    valores = []
    for v in values:
        texto = str(v).replace("'", "''")
        valores.append(f"'{texto}'")
    return f"{field_name} IN ({', '.join(valores)})"

def crear_tabla_salida(workspace, nombre_tabla):
    salida = os.path.join(workspace, nombre_tabla)
    if arcpy.Exists(salida):
        arcpy.management.Delete(salida)
    carpeta = os.path.dirname(salida)
    nombre = os.path.basename(salida)
    arcpy.management.CreateTable(carpeta, nombre)
    arcpy.management.AddField(salida, "ID_PLANCHETA", "TEXT", field_length=100)
    arcpy.management.AddField(salida, "ZONA", "TEXT", field_length=50)
    arcpy.management.AddField(salida, "USUARIO_ASIGNADO_EXTERNO", "TEXT", field_length=100)
    arcpy.management.AddField(salida, "FECHA_INICIO", "DATE")
    arcpy.management.AddField(salida, "FECHA_FIN", "DATE")
    arcpy.management.AddField(salida, "PRESION", "TEXT", field_length=5)
    arcpy.management.AddField(salida, "CANT_OTS", "LONG")
    arcpy.management.AddField(salida, "SUMA_LONGITUD", "DOUBLE")
    arcpy.management.AddField(salida, "CANT_FUGAS", "LONG")
    arcpy.management.AddField(salida, "CANT_FUGAS_TE", "LONG")
    return salida

#--------------------------------------------------------------------------------------------------#
def main():
    arcpy.env.overwriteOutput = True    
    # Parámetros de entrada
    planchetas = arcpy.GetParameter(0)              # Planchetas
    presion = arcpy.GetParameterAsText(1)           # Presion
    fecha_inicio = arcpy.GetParameter(2)            # Fecha_Inicio
    fecha_fin = arcpy.GetParameter(3)               # Fecha_Fin
    usuario_asignado_externo = arcpy.GetParameterAsText(4)  # Usuario asignado externo (DOMINIO CONTRATISTAS_FUGAS, descripción)
    ots_relevadas = arcpy.GetParameter(5)           # OTs_Relevadas
    fugas = arcpy.GetParameter(6)                   # Fugas    
    
    # #----------------------MENSAJE DE LOGEO TEMPORAL--------------------------
    # arcpy.AddMessage("tipo planchetas: " + str(type(planchetas)))
    # arcpy.AddMessage("repr planchetas: " + str(planchetas))
    # #----------------------MENSAJE DE LOGEO TEMPORAL--------------------------
    
    planchetas_tmp = os.path.join(arcpy.env.scratchGDB, "planchetas_input")
    if arcpy.Exists(planchetas_tmp):
        arcpy.management.Delete(planchetas_tmp)
    arcpy.management.CopyFeatures(planchetas, planchetas_tmp)
        # Transformo los datos de seleccion a un Feature Layer por si vienen 
        # en otro formato (Feature Set) que no funcione en Experience Builder    
    
    escala_objetivo = normalizar_presion(presion)
    if fecha_inicio is None or fecha_fin is None:
        raise ValueError("Fecha Inicio y Fecha Fin son obligatorias.")
    dt_inicio = obtener_datetime_inicio(fecha_inicio)
    dt_fin = obtener_datetime_fin(fecha_fin)
    usuario_asignado_codigo = None
    if usuario_asignado_externo:
        usuario_asignado_codigo = obtener_codigo_dominio_por_descripcion(
            ots_relevadas, "USUARIO_ASIGNADO_EXTERNO", "CONTRATISTAS_FUGAS", usuario_asignado_externo)
        if usuario_asignado_codigo is None:
            # Si no existe en el dominio, podemos asumir que el valor se maneja como texto directo
            usuario_asignado_codigo = usuario_asignado_externo
    if dt_inicio > dt_fin:
        raise ValueError("Fecha Inicio no puede ser mayor que Fecha Fin.")
    arcpy.AddMessage("Leyendo planchetas seleccionadas...")    
    
    # 1) Obtener las planchetas seleccionadas y filtrar por ESCALA
    planchetas_ids = set()
    campos_planchetas = ["ID_PLANCHETA", "ESCALA"]
    with arcpy.da.SearchCursor(planchetas_tmp, campos_planchetas) as cursor:
        for id_plancheta, escala in cursor:
            if escala == escala_objetivo:
                if id_plancheta is not None:
                    planchetas_ids.add(str(id_plancheta))
    if not planchetas_ids:
        raise ValueError("No hay planchetas seleccionadas que coincidan con la presión indicada.")
    arcpy.AddMessage(f"Planchetas válidas: {len(planchetas_ids)}")
    
    # Estructura de acumulación por plancheta y zona (inicializar con 0s para cada plancheta)
    resumen = {}
    for pid in planchetas_ids:
        for zona_calc in ["ZONA COMERCIAL", "ZONA NO COMERCIAL"]:
            resumen[(pid, zona_calc)] = {
                "cantidad_ots": 0,
                "suma_longitud": 0.0,
                "cantidad_fugas": 0,
                "cantidad_fugas_te": 0
            }

    # 2) Leer OTs Relevadas relacionadas, filtrar por fecha (y agrupar por zona)
    arcpy.AddMessage("Procesando OTs Relevadas...")
    # Mapa: ID_RESEGUIMIENTO -> ID_PLANCHETA
    reseg_a_plancheta = {}
    campos_ots = ["ID", "ID_PLANCHETA", "CODIGO_LOCALIDAD", "LONGITUD", "FECHA_REL", "USUARIO_ASIGNADO_EXTERNO"]
    
    # Para evitar where muy largo, procesamos las planchetas en bloques
    for bloque_planchetas in chunks(list(planchetas_ids), 200):
        where_ots = sql_in_text("ID_PLANCHETA", bloque_planchetas)
        with arcpy.da.SearchCursor(ots_relevadas, campos_ots, where_clause=where_ots) as cursor:
            for id_reseguimiento, id_plancheta, codigo_localidad, longitud, fecha_rel, usuario_asignado_reg in cursor:
                if id_plancheta is None or id_reseguimiento is None or fecha_rel is None:
                    continue
                id_plancheta = str(id_plancheta)
                id_reseguimiento = str(id_reseguimiento)
                if not (dt_inicio <= fecha_rel <= dt_fin):
                    continue

                try:
                    zona_actual = normalizar_zona(codigo_localidad)
                except ValueError:
                    # Ignorar locales que no sean zona comercial/no comercial
                    continue

                # Filtrar por usuario asignado externo si se seleccionó algún valor
                if usuario_asignado_externo:
                    if usuario_asignado_reg is None:
                        continue
                    if str(usuario_asignado_reg).strip() != str(usuario_asignado_codigo).strip() and \
                       str(usuario_asignado_reg).strip().lower() != str(usuario_asignado_externo).strip().lower():
                        continue

                clave = (id_plancheta, zona_actual)
                if clave not in resumen:
                    resumen[clave] = {
                        "cantidad_ots": 0,
                        "suma_longitud": 0.0,
                        "cantidad_fugas": 0,
                        "cantidad_fugas_te": 0
                    }

                resumen[clave]["cantidad_ots"] += 1
                resumen[clave]["suma_longitud"] += float(longitud) if longitud is not None else 0.0
                reseg_a_plancheta[id_reseguimiento] = clave
    arcpy.AddMessage(f"OTs filtradas: {len(reseg_a_plancheta)}")    
    if len(reseg_a_plancheta) == 0:
        arcpy.AddMessage("No se encontraron OTs para las planchetas; se crearán registros de 0 valor por zona.")

    # 3) Leer Fugas relacionadas a las OTs filtradas
    if reseg_a_plancheta:
        arcpy.AddMessage("Procesando Fugas...")
        # campos_fugas = ["ID_RESEGUIMIENTO", "TIEMPO_ESPERA"]
        campos_fugas = ["ID_RESEGUIMIENTO"] #reemplaza lo dearriba, hasta que se ponga el campo de tiempo de espera en la tabla de fugas
        reseguimientos_ids = list(reseg_a_plancheta.keys())
        for bloque_reseg in chunks(reseguimientos_ids, 200):
            where_fugas = sql_in_text("ID_RESEGUIMIENTO", bloque_reseg)
            with arcpy.da.SearchCursor(fugas, campos_fugas, where_clause=where_fugas) as cursor:
                # for id_reseguimiento, tiempo_espera in cursor:
                for (id_reseguimiento,) in cursor: #reemplaza lo de arriba, hasta que se ponga el campo de tiempo de espera en la tabla de fugas
                    if id_reseguimiento is None:
                        continue
                    id_reseguimiento = str(id_reseguimiento)
                    clave = reseg_a_plancheta.get(id_reseguimiento)
                    if clave is None:
                        continue
                    resumen[clave]["cantidad_fugas"] += 1
                    # if tiempo_espera in (True, 1, "1", "true", "True", "TRUE"):
                    #     resumen[clave]["cantidad_fugas_te"] += 1
                    resumen[clave]["cantidad_fugas_te"] += 1 # reemplaza las dos lineas de arriba hasta que se ponga el campo tiempo de espera en la tabla de fugas                    
    
    # 4) Crear tabla de salida en scratchGDB
    arcpy.AddMessage("Creando tabla de salida...")
    scratch_gdb = arcpy.env.scratchGDB
    nombre_tabla = "reseguimiento_fugas_planchetas"
    tabla_salida = crear_tabla_salida(scratch_gdb, nombre_tabla)
    campos_insert = [
        "ID_PLANCHETA",
        "ZONA",
        "USUARIO_ASIGNADO_EXTERNO",
        "FECHA_INICIO",
        "FECHA_FIN",
        "PRESION",
        "CANT_OTS",
        "SUMA_LONGITUD",
        "CANT_FUGAS",
        "CANT_FUGAS_TE"
    ]
    with arcpy.da.InsertCursor(tabla_salida, campos_insert) as cursor:
        for id_plancheta, zona_calc in sorted(resumen.keys()):
            item = resumen[(id_plancheta, zona_calc)]
            cursor.insertRow([
                id_plancheta,
                zona_calc,
                usuario_asignado_externo if usuario_asignado_externo else "",
                dt_inicio,
                dt_fin,
                presion,
                item["cantidad_ots"],
                item["suma_longitud"],
                item["cantidad_fugas"],
                item["cantidad_fugas_te"]
            ])
    arcpy.AddMessage(f"Tabla generada: {tabla_salida}")
    
    # Es una tabla temporal en scratchGDB. No se necesita un parametro de salida ya que no se va a guardar ni compartir, solo se devuelve la ruta para que Experience Builder la consuma directamente desde el scratchGDB. Si se quisiera guardar o compartir, se podría agregar un parámetro de salida y copiar la tabla allí si lo requieren.
    # Devolver salida
    # arcpy.SetParameterAsText(7, tabla_salida)   # Parámetro de salida
    #                                             # Se asume un parámetro 7 para devolver la tabla creada
                                                
#--------------------------------------------------------------------------------------------------#
if __name__ == "__main__":
    main()
