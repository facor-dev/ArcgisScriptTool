# -*- coding: utf-8 -*-
import arcpy
import os
from datetime import datetime

NOMBRE_CAPA_OTS = "ots_lyr_tmp"
NOMBRE_CAPA_FUGAS = "fugas_lyr_tmp"
NOMBRE_CAPA_REP = "rep_lyr_tmp"


def add_msg(txt):
    arcpy.AddMessage(str(txt))


def add_warn(txt):
    arcpy.AddWarning(str(txt))


def add_err(txt):
    arcpy.AddError(str(txt))


def chunks(lista, n):
    for i in range(0, len(lista), n):
        yield lista[i:i + n]


def escape_sql_text(valor):
    return str(valor).replace("'", "''")


def sql_in_text(campo, valores):
    vals = []
    for v in valores:
        if v is None:
            continue
        s = str(v).strip()
        if s == "":
            continue
        vals.append("'" + escape_sql_text(s) + "'")

    if not vals:
        return "1=0"

    return f"{campo} IN ({','.join(vals)})"


def sql_fecha_inclusive(campo, fecha_inicio, fecha_fin):
    fi = fecha_inicio.strftime("%Y-%m-%d %H:%M:%S")
    ff = fecha_fin.strftime("%Y-%m-%d %H:%M:%S")
    return f"{campo} >= TIMESTAMP '{fi}' AND {campo} <= TIMESTAMP '{ff}'"


def get_selected_planchetas(planchetas_lyr):
    ids = []
    info = {}

    with arcpy.da.SearchCursor(planchetas_lyr, ["ID_PLANCHETA", "ESCALA"]) as cur:
        for row in cur:
            id_plancheta = row[0]
            escala = row[1]
            if id_plancheta is None:
                continue

            id_txt = str(id_plancheta)
            ids.append(id_txt)
            info[id_txt] = {
                "ID_PLANCHETA": id_txt,
                "ESCALA": escala
            }

    return ids, info


def seleccionar_ots(ots_fc, ids_plancheta, tam_bloque=200):
    arcpy.management.MakeFeatureLayer(ots_fc, NOMBRE_CAPA_OTS)
    arcpy.management.SelectLayerByAttribute(NOMBRE_CAPA_OTS, "CLEAR_SELECTION")

    primera = True
    for bloque in chunks(ids_plancheta, tam_bloque):
        where = sql_in_text("ID_PLANCHETA", bloque)
        tipo = "NEW_SELECTION" if primera else "ADD_TO_SELECTION"
        arcpy.management.SelectLayerByAttribute(NOMBRE_CAPA_OTS, tipo, where)
        primera = False

    ots_info = {}
    with arcpy.da.SearchCursor(NOMBRE_CAPA_OTS, ["ID", "ID_PLANCHETA"]) as cur:
        for row in cur:
            id_ot = row[0]
            id_plancheta = row[1]
            if id_ot is None:
                continue

            ots_info[str(id_ot)] = {
                "ID": str(id_ot),
                "ID_PLANCHETA": str(id_plancheta) if id_plancheta is not None else None
            }

    return ots_info


def seleccionar_fugas(fugas_fc, ids_ot, fecha_inicio, fecha_fin, tam_bloque=200):
    arcpy.management.MakeFeatureLayer(fugas_fc, NOMBRE_CAPA_FUGAS)
    arcpy.management.SelectLayerByAttribute(NOMBRE_CAPA_FUGAS, "CLEAR_SELECTION")

    filtro_estado = "ESTADO = 'VEREDA REPARADA'"
    filtro_fecha = sql_fecha_inclusive("FECHA_REP_VER", fecha_inicio, fecha_fin)

    primera = True
    for bloque in chunks(ids_ot, tam_bloque):
        filtro_ids = sql_in_text("ID_RESEGUIMIENTO", bloque)
        where = f"{filtro_ids} AND {filtro_estado} AND {filtro_fecha}"
        tipo = "NEW_SELECTION" if primera else "ADD_TO_SELECTION"
        arcpy.management.SelectLayerByAttribute(NOMBRE_CAPA_FUGAS, tipo, where)
        primera = False

    fugas_info = {}
    campos = [
        "GLOBALID",
        "ID_RESEGUIMIENTO",
        "PROVINCIA_FUGA",
        "LOCALIDAD_FUGA",
        "USUARIO_ASIGNADO_FUGA",
        "TIPO",
        "ORIGEN",
        "FECHA_REP_VER"
    ]

    with arcpy.da.SearchCursor(NOMBRE_CAPA_FUGAS, campos) as cur:
        for row in cur:
            globalid = row[0]
            if globalid is None:
                continue

            globalid_txt = str(globalid)
            fugas_info[globalid_txt] = {
                "GLOBALID": globalid_txt,
                "ID_RESEGUIMIENTO": str(row[1]) if row[1] is not None else None,
                "PROVINCIA_FUGA": row[2],
                "LOCALIDAD_FUGA": row[3],
                "USUARIO_ASIGNADO_FUGA": row[4],
                "TIPO": row[5],
                "ORIGEN": row[6],
                "FECHA_REP_VER": row[7]
            }

    return fugas_info


def seleccionar_reparaciones(reparaciones_fc, globalids_fuga, nombre_contratista, tam_bloque=200):
    arcpy.management.MakeFeatureLayer(reparaciones_fc, NOMBRE_CAPA_REP)
    arcpy.management.SelectLayerByAttribute(NOMBRE_CAPA_REP, "CLEAR_SELECTION")

    filtro_empresa = f"EMPRESA = '{escape_sql_text(nombre_contratista)}'"

    primera = True
    for bloque in chunks(globalids_fuga, tam_bloque):
        filtro_ids = sql_in_text("REL_REL_GLOBALID", bloque)
        where = f"{filtro_ids} AND {filtro_empresa}"
        tipo = "NEW_SELECTION" if primera else "ADD_TO_SELECTION"
        arcpy.management.SelectLayerByAttribute(NOMBRE_CAPA_REP, tipo, where)
        primera = False

    return NOMBRE_CAPA_REP


def crear_tabla_salida(tabla_salida):
    workspace = os.path.dirname(tabla_salida)
    nombre = os.path.basename(tabla_salida)

    if arcpy.Exists(tabla_salida):
        arcpy.management.Delete(tabla_salida)

    arcpy.management.CreateTable(workspace, nombre)

    # Campos propios del proceso
    campos_nuevos = [
        ("REP_OBJECTID_SRC", "LONG"),
        ("REP_GLOBALID", "TEXT", 50),
        ("REP_REL_GLOBALID", "TEXT", 50),
        ("REP_REL_REL_GLOBALID", "TEXT", 50),
        ("REP_ID", "TEXT", 100),
        ("REP_EMPRESA", "TEXT", 255),
        ("REP_TAREAS_REALIZADAS", "TEXT", 4000),

        ("FUGA_PROVINCIA_FUGA", "TEXT", 255),
        ("FUGA_LOCALIDAD_FUGA", "TEXT", 255),
        ("FUGA_USUARIO_ASIGNADO_FUGA", "TEXT", 255),
        ("FUGA_TIPO", "TEXT", 100),
        ("FUGA_ORIGEN", "TEXT", 100),
        ("FUGA_FECHA_REP_VER", "DATE"),

        ("OT_ID", "TEXT", 100),

        ("PLANCHETA_ID_PLANCHETA", "TEXT", 100),
        ("PLANCHETA_ESCALA", "TEXT", 100),
    ]

    for campo in campos_nuevos:
        if len(campo) == 2:
            arcpy.management.AddField(tabla_salida, campo[0], campo[1])
        else:
            arcpy.management.AddField(tabla_salida, campo[0], campo[1], field_length=campo[2])

    return tabla_salida


def volcar_resultados(rep_lyr, tabla_salida, fugas_info, ots_info, planchetas_info):
    campos_rep_lectura = [
        "OBJECTID",
        "GLOBALID",
        "REL_GLOBALID",
        "REL_REL_GLOBALID",
        "ID",
        "EMPRESA",
        "TAREAS_REALIZADAS"
    ]

    campos_insert = [
        "REP_OBJECTID_SRC",
        "REP_GLOBALID",
        "REP_REL_GLOBALID",
        "REP_REL_REL_GLOBALID",
        "REP_ID",
        "REP_EMPRESA",
        "REP_TAREAS_REALIZADAS",

        "FUGA_PROVINCIA_FUGA",
        "FUGA_LOCALIDAD_FUGA",
        "FUGA_USUARIO_ASIGNADO_FUGA",
        "FUGA_TIPO",
        "FUGA_ORIGEN",
        "FUGA_FECHA_REP_VER",

        "OT_ID",

        "PLANCHETA_ID_PLANCHETA",
        "PLANCHETA_ESCALA",
    ]

    insertados = 0

    with arcpy.da.InsertCursor(tabla_salida, campos_insert) as icur:
        with arcpy.da.SearchCursor(rep_lyr, campos_rep_lectura) as cur:
            for row in cur:
                rep_objectid = row[0]
                rep_globalid = str(row[1]) if row[1] is not None else None
                rep_rel_globalid = str(row[2]) if row[2] is not None else None
                rep_rel_rel_globalid = str(row[3]) if row[3] is not None else None
                rep_id = row[4]
                rep_empresa = row[5]
                rep_tareas = row[6]

                fuga = fugas_info.get(rep_rel_rel_globalid)
                if not fuga:
                    continue

                ot_id = fuga["ID_RESEGUIMIENTO"]
                ot = ots_info.get(ot_id)
                if not ot:
                    continue

                id_plancheta = ot["ID_PLANCHETA"]
                plancheta = planchetas_info.get(id_plancheta)
                if not plancheta:
                    continue

                icur.insertRow([
                    rep_objectid,
                    rep_globalid,
                    rep_rel_globalid,
                    rep_rel_rel_globalid,
                    rep_id,
                    rep_empresa,
                    rep_tareas,

                    fuga["PROVINCIA_FUGA"],
                    fuga["LOCALIDAD_FUGA"],
                    fuga["USUARIO_ASIGNADO_FUGA"],
                    fuga["TIPO"],
                    fuga["ORIGEN"],
                    fuga["FECHA_REP_VER"],

                    ot_id,

                    plancheta["ID_PLANCHETA"],
                    plancheta["ESCALA"],
                ])
                insertados += 1

    return insertados


def ejecutar_etapa_seleccion(planchetas_lyr, ots_fc, fugas_fc, reparaciones_fc,
                             fecha_inicio, fecha_fin, nombre_contratista, tabla_salida):
    add_msg("Obteniendo planchetas seleccionadas...")
    ids_plancheta, planchetas_info = get_selected_planchetas(planchetas_lyr)

    if not ids_plancheta:
        raise Exception("No hay planchetas seleccionadas.")

    add_msg(f"Planchetas seleccionadas: {len(ids_plancheta)}")

    add_msg("Seleccionando OTs Relevadas...")
    ots_info = seleccionar_ots(ots_fc, ids_plancheta)
    if not ots_info:
        add_warn("No se encontraron OTs Relevadas.")
        crear_tabla_salida(tabla_salida)
        return tabla_salida

    add_msg(f"OTs encontradas: {len(ots_info)}")

    add_msg("Seleccionando Fugas...")
    fugas_info = seleccionar_fugas(fugas_fc, list(ots_info.keys()), fecha_inicio, fecha_fin)
    if not fugas_info:
        add_warn("No se encontraron Fugas.")
        crear_tabla_salida(tabla_salida)
        return tabla_salida

    add_msg(f"Fugas encontradas: {len(fugas_info)}")

    add_msg("Seleccionando Reparaciones de Fugas...")
    rep_lyr = seleccionar_reparaciones(reparaciones_fc, list(fugas_info.keys()), nombre_contratista)

    cantidad_rep = int(arcpy.management.GetCount(rep_lyr)[0])
    add_msg(f"Reparaciones seleccionadas: {cantidad_rep}")

    add_msg("Creando tabla de salida...")
    crear_tabla_salida(tabla_salida)

    add_msg("Volcando resultados...")
    insertados = volcar_resultados(rep_lyr, tabla_salida, fugas_info, ots_info, planchetas_info)
    add_msg(f"Registros volcados: {insertados}")

    return tabla_salida

def main():
    planchetas_lyr = arcpy.GetParameter(0)      # capa de planchetas seleccionadas
    ots_fc = arcpy.GetParameterAsText(1)
    fugas_fc = arcpy.GetParameterAsText(2)
    reparaciones_fc = arcpy.GetParameterAsText(3)
    fecha_inicio = arcpy.GetParameter(4)
    fecha_fin = arcpy.GetParameter(5)
    nombre_contratista = arcpy.GetParameterAsText(6)
    tabla_salida = arcpy.GetParameterAsText(7)

    resultado = ejecutar_etapa_seleccion(
        planchetas_lyr,
        ots_fc,
        fugas_fc,
        reparaciones_fc,
        fecha_inicio,
        fecha_fin,
        nombre_contratista,
        tabla_salida
    )

    arcpy.SetParameterAsText(7, resultado)


if __name__ == "__main__":
    main()