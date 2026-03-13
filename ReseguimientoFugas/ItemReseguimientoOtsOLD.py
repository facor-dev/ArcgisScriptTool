import arcpy

# ---------------------------------------------------------
# 1. PARAMETROS
# ---------------------------------------------------------

ots_input = arcpy.GetParameter(0)   # FeatureSet de OTs seleccionadas

# ---------------------------------------------------------
# 2. CAPA FUGAS
# ---------------------------------------------------------
# Esta capa debe existir en el proyecto de ArcGIS Pro
# agregado desde el Feature Service antes de publicar

fugas_layer = "Fugas"

# ---------------------------------------------------------
# 3. CAPA TEMPORAL DE OTs
# ---------------------------------------------------------

ots_layer = "ots_layer"

arcpy.management.MakeFeatureLayer(
    ots_input,
    ots_layer
)

# ---------------------------------------------------------
# 3.1. VALIDACION DE OTs SELECCIONADAS
# ---------------------------------------------------------

count = int(arcpy.management.GetCount(ots_layer)[0])

if count == 0:
    arcpy.AddError("No hay reseguimientos seleccionados.")
    raise Exception("Sin registros de entrada")

# ---------------------------------------------------------
# 4. DICCIONARIO ACUMULADOR
# ---------------------------------------------------------

resultado = {}
ids_reseguimiento = set()

# ---------------------------------------------------------
# 5. RECORRER OTs
# ---------------------------------------------------------

with arcpy.da.SearchCursor(
    ots_layer,
    ["ID", "ID_PLANCHETA", "LONGITUD"]
) as cursor:

    for row in cursor:

        id_reseg = row[0]
        plancheta = row[1]
        longitud = row[2]

        ids_reseguimiento.add(id_reseg)

        if plancheta not in resultado:

            resultado[plancheta] = {
                "distancia": 0,
                "fugas": 0,
                "espera": 0
            }

        resultado[plancheta]["distancia"] += longitud

# ---------------------------------------------------------
# 6. JOIN ENTRE FUGAS Y OTs
# ---------------------------------------------------------

fugas_join = "fugas_join"

arcpy.management.MakeFeatureLayer(
    fugas_layer,
    fugas_join
)

arcpy.management.AddJoin(
    fugas_join,
    "ID_RESEGUIMIENTO",
    ots_layer,
    "ID",
    "KEEP_COMMON"
)

# ---------------------------------------------------------
# 6.1. ADAPTAR NOMBRES DE CAMPOS DINAMICOS 
# ---------------------------------------------------------

fields = arcpy.ListFields(fugas_join)

campo_plancheta = None
campo_espera = None

for f in fields:

    nombre = f.name.upper()
    arcpy.AddMessage(f"Campo detectado: {f.name}")

    if nombre.endswith("ID_PLANCHETA"):
        campo_plancheta = f.name

    if nombre.endswith("TIEMPO_ESPERA"):
        campo_espera = f.name


# ---------------------------------------------------------
# 6.1. VALIDAR CAMPOS DETECTADOS EN EL JOIN 
# ---------------------------------------------------------

#COMENTADO TEMPORALMENTE HASTA QUE SE DEFINA EL CAMPO DE TIEMPO DE ESPERA EN LA CAPA DE FUGAS
if not campo_plancheta: # or not campo_espera:
    arcpy.AddError("No se pudieron identificar los campos necesarios en el Join.")
    raise Exception("Campos no encontrados")


# ---------------------------------------------------------
# 7. RECORRER FUGAS
# ---------------------------------------------------------

# with arcpy.da.SearchCursor(
#     fugas_join,
#     ["OTs_Relevadas.ID_PLANCHETA", "Fugas.TIEMPO_ESPERA"]
# ) as cursor:

#     for row in cursor:

#         plancheta = row[0]
#         tiempo_espera = row[1]

#         if plancheta in resultado:

#             resultado[plancheta]["fugas"] += 1

#             if tiempo_espera:
#                 resultado[plancheta]["espera"] += 1

with arcpy.da.SearchCursor(
    fugas_join,
    [campo_plancheta]#, campo_espera]
) as cursor:

    for row in cursor:

        plancheta = row[0]
        #tiempo_espera = row[1]

        if plancheta in resultado:

            resultado[plancheta]["fugas"] += 1

            # if tiempo_espera:
            #     resultado[plancheta]["espera"] += 1

# ---------------------------------------------------------
# 8. CREAR TABLA DE SALIDA
# ---------------------------------------------------------

tabla_salida = arcpy.management.CreateTable(
    "in_memory",
    "resultado_certificado"
)

# ---------------------------------------------------------
# 9. CREAR CAMPOS
# ---------------------------------------------------------

arcpy.management.AddField(tabla_salida, "ID_PLANCHETA", "TEXT")
arcpy.management.AddField(tabla_salida, "DISTANCIA_TOTAL", "DOUBLE")
arcpy.management.AddField(tabla_salida, "TOTAL_FUGAS", "LONG")
arcpy.management.AddField(tabla_salida, "TOTAL_TIEMPO_ESPERA", "LONG")

# ---------------------------------------------------------
# 10. INSERTAR RESULTADOS
# ---------------------------------------------------------

with arcpy.da.InsertCursor(
    tabla_salida,
    [
        "ID_PLANCHETA",
        "DISTANCIA_TOTAL",
        "TOTAL_FUGAS",
        "TOTAL_TIEMPO_ESPERA"
    ]
) as cursor:

    for plancheta, valores in resultado.items():

        cursor.insertRow([
            plancheta,
            valores["distancia"],
            valores["fugas"],
#            valores["espera"]
        ])

# ---------------------------------------------------------
# 11. SALIDA
# ---------------------------------------------------------

arcpy.SetParameter(1, tabla_salida)
