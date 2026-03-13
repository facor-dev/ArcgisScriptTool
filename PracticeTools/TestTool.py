"""Script tool para ArcGIS Pro: copiar solo algunos campos seleccionados.

Este script toma como entrada una capa (feature layer) de la que se espera que el usuario
haya seleccionado registros (por ejemplo, con una herramienta de selección en Experience Builder).
Crea una tabla de salida que solo contiene los campos:
 - escala
 - ID_PLANCHETA

El script se puede publicar como un servicio de geoprocesamiento y consumirlo desde Experience Builder.
"""

import arcpy
import os


def main():
    arcpy.env.overwriteOutput = True

    # Parámetros del script tool
    in_param = arcpy.GetParameter(0)

    # Validar que sea un FeatureSet
    # if not isinstance(in_param, arcpy.FeatureSet):
    #     arcpy.AddError("El parámetro de entrada debe ser un FeatureSet (selección de features).")
    #     raise arcpy.ExecuteError("Tipo de parámetro incorrecto.")

    in_layer = in_param

    required_fields = ["escala", "ID_PLANCHETA"]

    # Validar que la capa (layer) exista y tenga los campos esperados.
    existing_fields = {f.name.lower(): f.name for f in arcpy.ListFields(in_layer)}
    missing = [f for f in required_fields if f.lower() not in existing_fields]
    if missing:
        arcpy.AddError(
            "Los siguientes campos no se encuentran en la capa de entrada: {}".format(
                ", ".join(missing)
            )
        )
        raise arcpy.ExecuteError("Faltan campos obligatorios.")

    # Usamos FieldMappings para conservar solo los campos indicados.
    field_mappings = arcpy.FieldMappings()
    for fld in required_fields:
        actual_name = existing_fields[fld.lower()]
        fld_map = arcpy.FieldMap()
        fld_map.addInputField(in_layer, actual_name)
        field_mappings.addFieldMap(fld_map)

    arcpy.AddMessage(f"Creando tabla con los campos: {', '.join(required_fields)}")

    # Determinar ruta de salida: usar scratchGDB con nombre único
    out_workspace = arcpy.env.scratchGDB
    out_name = "Planchetas_Seleccionadas"

    # arcpy.CreateUniqueName es la función correcta para generar un nombre único en un workspace.
    out_path_full = arcpy.CreateUniqueName(out_name, out_workspace)
    out_workspace, out_name = os.path.split(out_path_full)

    # Contar registros seleccionados
    sel_count = int(arcpy.GetCount_management(in_layer).getOutput(0))
    if sel_count == 0:
        arcpy.AddError("No hay registros seleccionados en la capa de entrada.")
        raise arcpy.ExecuteError("No hay selección.")

    arcpy.conversion.TableToTable(in_layer, out_workspace, out_name, field_mapping=field_mappings)

    out_path = os.path.join(out_workspace, out_name)
    arcpy.AddMessage(f"Tabla de salida creada: {out_path}")

    # Crear un RecordSet para devolver los datos en el servicio
    recordset = arcpy.RecordSet(out_path)
    arcpy.SetParameter(1, recordset)


if __name__ == "__main__":
    main()
